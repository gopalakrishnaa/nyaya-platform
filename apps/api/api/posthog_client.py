from __future__ import annotations

import atexit

from posthog import Posthog

from .config import settings

posthog_client: Posthog | None = None


def init_posthog() -> None:
    global posthog_client
    if settings.posthog_disabled or not settings.posthog_project_token:
        return
    posthog_client = Posthog(
        api_key=settings.posthog_project_token,
        host=settings.posthog_host,
        enable_exception_autocapture=True,
    )
    atexit.register(posthog_client.shutdown)


def shutdown_posthog() -> None:
    if posthog_client is not None:
        posthog_client.shutdown()
