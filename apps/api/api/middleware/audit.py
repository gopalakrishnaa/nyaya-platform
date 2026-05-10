from __future__ import annotations

import json

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response: Response = await call_next(request)

        if request.method in MUTATING_METHODS and response.status_code < 400:
            try:
                request_id = getattr(request.state, "request_id", None)
                actor_id = None
                actor_email = None

                # Extract actor from state if auth middleware ran
                user = getattr(request.state, "user", None)
                if user:
                    actor_id = user.get("sub")
                    actor_email = user.get("email")

                logger.info(
                    "audit_event",
                    actor_id=actor_id,
                    actor_email=actor_email,
                    action=f"{request.method} {request.url.path}",
                    ip_address=request.headers.get("X-Forwarded-For", ""),
                    request_id=request_id,
                    status_code=response.status_code,
                )
            except Exception:
                pass

        return response
