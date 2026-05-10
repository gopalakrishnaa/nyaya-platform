from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db

security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_REQUIRED_CLAIMS = {"sub", "role", "exp"}


@lru_cache(maxsize=1)
def _load_public_key() -> str:
    return Path(settings.jwt_public_key_path).read_text()


def decode_jwt(token: str) -> dict:  # type: ignore[type-arg]
    try:
        public_key = _load_public_key()
        payload = jwt.decode(token, public_key, algorithms=[settings.jwt_algorithm])
    except (JWTError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    missing = _REQUIRED_CLAIMS - payload.keys()
    if missing:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token missing claims: {missing}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload  # type: ignore[return-value]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict | None:  # type: ignore[type-arg]
    if not credentials:
        return None
    return decode_jwt(credentials.credentials)


async def require_moderator(
    user: dict | None = Depends(get_current_user),  # type: ignore[type-arg]
) -> dict:  # type: ignore[type-arg]
    if not user or user.get("role") not in ("MODERATOR", "ADMIN", "SUPERADMIN"):
        raise HTTPException(status_code=403, detail="Moderator role required")
    return user


async def require_admin(
    user: dict | None = Depends(get_current_user),  # type: ignore[type-arg]
) -> dict:  # type: ignore[type-arg]
    if not user or user.get("role") not in ("ADMIN", "SUPERADMIN"):
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


_API_KEY_QUERY = text(
    "SELECT id, email, tier, rate_limit_per_minute FROM api_keys "
    "WHERE key_hash = :key_hash AND is_active = TRUE "
    "AND (expires_at IS NULL OR expires_at > NOW())"
)


async def get_api_key_user(
    api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> dict | None:  # type: ignore[type-arg]
    if not api_key:
        return None
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    result = await db.execute(_API_KEY_QUERY, {"key_hash": key_hash})
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"id": str(row[0]), "email": row[1], "tier": row[2], "rate_limit": row[3]}
