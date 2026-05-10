from __future__ import annotations

# Re-export commonly used dependencies for convenience
from .database import get_db
from .middleware.auth import get_api_key_user, get_current_user, require_admin, require_moderator

__all__ = [
    "get_db",
    "get_current_user",
    "get_api_key_user",
    "require_moderator",
    "require_admin",
]
