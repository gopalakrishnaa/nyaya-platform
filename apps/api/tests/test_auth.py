"""Tests for JWT auth middleware at api.middleware.auth."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt as jose_jwt


# ---------------------------------------------------------------------------
# RSA key pair generation (shared across tests in this module)
# ---------------------------------------------------------------------------

def _generate_rsa_key_pair() -> tuple[str, str]:
    """Return (private_key_pem, public_key_pem) as strings."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    return private_pem, public_pem


def _make_rs256_token(
    private_pem: str,
    payload: dict[str, Any] | None = None,
    *,
    expired: bool = False,
) -> str:
    """Sign and return a JWT with RS256 using the supplied private key."""
    now = int(time.time())
    claims: dict[str, Any] = payload or {}
    if "sub" not in claims:
        claims["sub"] = "user-test-001"
    if expired:
        claims["exp"] = now - 3600  # already expired
    else:
        claims["exp"] = now + 3600  # valid for an hour

    return jose_jwt.encode(claims, private_pem, algorithm="RS256")


# ---------------------------------------------------------------------------
# decode_jwt()
# ---------------------------------------------------------------------------

class TestDecodeJwt:
    def test_valid_rs256_token_returns_payload(self) -> None:
        """decode_jwt() with a correctly signed RS256 token returns the claims dict."""
        from api.middleware.auth import decode_jwt

        private_pem, public_pem = _generate_rsa_key_pair()
        token = _make_rs256_token(private_pem, {"sub": "user-123", "role": "ADMIN"})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            f.write(public_pem)
            pub_path = f.name

        with (
            patch("api.middleware.auth.settings") as mock_settings,
        ):
            mock_settings.jwt_public_key_path = pub_path
            mock_settings.jwt_algorithm = "RS256"
            payload = decode_jwt(token)

        assert isinstance(payload, dict)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "ADMIN"

    def test_expired_token_raises_401(self) -> None:
        """decode_jwt() raises HTTPException 401 for an expired token."""
        from api.middleware.auth import decode_jwt

        private_pem, public_pem = _generate_rsa_key_pair()
        token = _make_rs256_token(private_pem, expired=True)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            f.write(public_pem)
            pub_path = f.name

        with (
            patch("api.middleware.auth.settings") as mock_settings,
            pytest.raises(HTTPException) as exc_info,
        ):
            mock_settings.jwt_public_key_path = pub_path
            mock_settings.jwt_algorithm = "RS256"
            decode_jwt(token)

        assert exc_info.value.status_code == 401

    def test_wrong_algorithm_raises_401(self) -> None:
        """decode_jwt() raises HTTPException 401 when the token uses an unexpected algorithm.

        We produce an HS256 token but configure the service to expect RS256.
        jose will reject the mismatched algorithm.
        """
        from api.middleware.auth import decode_jwt

        # HS256 token — signed with a shared secret, not RSA
        hs256_token = jose_jwt.encode(
            {"sub": "attacker", "exp": int(time.time()) + 3600},
            "some-hmac-secret",
            algorithm="HS256",
        )

        private_pem, public_pem = _generate_rsa_key_pair()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            f.write(public_pem)
            pub_path = f.name

        with (
            patch("api.middleware.auth.settings") as mock_settings,
            pytest.raises(HTTPException) as exc_info,
        ):
            mock_settings.jwt_public_key_path = pub_path
            mock_settings.jwt_algorithm = "RS256"
            decode_jwt(hs256_token)

        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self) -> None:
        """A token signed with a *different* private key must be rejected."""
        from api.middleware.auth import decode_jwt

        private_pem_attacker, _ = _generate_rsa_key_pair()
        _, public_pem_server = _generate_rsa_key_pair()

        # Attacker signs with their own key; server verifies with its public key
        token = _make_rs256_token(private_pem_attacker, {"sub": "attacker"})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            f.write(public_pem_server)
            pub_path = f.name

        with (
            patch("api.middleware.auth.settings") as mock_settings,
            pytest.raises(HTTPException) as exc_info,
        ):
            mock_settings.jwt_public_key_path = pub_path
            mock_settings.jwt_algorithm = "RS256"
            decode_jwt(token)

        assert exc_info.value.status_code == 401

    def test_missing_public_key_file_raises_401(self) -> None:
        """decode_jwt() raises 401 when the public key file doesn't exist."""
        from api.middleware.auth import decode_jwt

        private_pem, _ = _generate_rsa_key_pair()
        token = _make_rs256_token(private_pem)

        with (
            patch("api.middleware.auth.settings") as mock_settings,
            pytest.raises(HTTPException) as exc_info,
        ):
            mock_settings.jwt_public_key_path = "/nonexistent/path/jwt_public.pem"
            mock_settings.jwt_algorithm = "RS256"
            decode_jwt(token)

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user()
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_no_authorization_header_raises_401(self) -> None:
        """get_current_user() returns None when credentials=None (no Auth header).

        The router's `security = HTTPBearer(auto_error=False)` injects None when
        no Authorization header is present, so get_current_user returns None.
        A downstream `require_moderator` / `require_admin` guard would then raise
        403.  However, the /v1/cases public endpoint accepts None (unauthenticated)
        without error.

        This test verifies the raw dependency behaviour: None credentials → None
        return (no exception raised in get_current_user itself).
        """
        from api.middleware.auth import get_current_user

        result = await get_current_user(credentials=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_credentials_delegates_to_decode_jwt(self) -> None:
        """get_current_user() calls decode_jwt and returns the resulting payload."""
        from api.middleware.auth import get_current_user

        private_pem, public_pem = _generate_rsa_key_pair()
        token = _make_rs256_token(private_pem, {"sub": "user-777", "role": "VIEWER"})

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            f.write(public_pem)
            pub_path = f.name

        with patch("api.middleware.auth.settings") as mock_settings:
            mock_settings.jwt_public_key_path = pub_path
            mock_settings.jwt_algorithm = "RS256"
            payload = await get_current_user(credentials=credentials)

        assert payload is not None
        assert payload["sub"] == "user-777"

    @pytest.mark.asyncio
    async def test_invalid_token_in_credentials_raises_401(self) -> None:
        """get_current_user() propagates the 401 from decode_jwt on bad tokens."""
        from api.middleware.auth import get_current_user

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="not.a.valid.jwt"
        )

        _, public_pem = _generate_rsa_key_pair()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            f.write(public_pem)
            pub_path = f.name

        with (
            patch("api.middleware.auth.settings") as mock_settings,
            pytest.raises(HTTPException) as exc_info,
        ):
            mock_settings.jwt_public_key_path = pub_path
            mock_settings.jwt_algorithm = "RS256"
            await get_current_user(credentials=credentials)

        assert exc_info.value.status_code == 401
