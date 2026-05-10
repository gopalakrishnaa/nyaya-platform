"""Privacy utility functions: hashing, pseudonymisation."""

from __future__ import annotations

import hashlib
import hmac


def hash_token(value: str, salt: str = "") -> str:
    """Return a stable hex digest of *value* (optionally salted).

    The result is safe to log — it does not reveal the original text.
    """
    key = salt.encode("utf-8") if salt else b""
    if key:
        digest = hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()
    else:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest


def victim_pseudonym(case_id: str, counter: int = 0) -> str:
    """Return a deterministic pseudonym for a victim in the given case.

    The pseudonym is derived from the case_id so multiple redactions of the
    same name within one article produce the same token, while revealing
    nothing about the underlying identity.
    """
    seed = f"{case_id}:victim:{counter}"
    token = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8].upper()
    return f"VICTIM-{token}"
