from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..middleware.rate_limit import rate_limit
from ..posthog_client import posthog_client
from ..services.ask_service import AskService

router = APIRouter(prefix="/v1/ask", tags=["ask"])


class AskRequest(BaseModel):
    question: str = Field(min_length=10, max_length=500)


@router.post("")
async def ask(request: Request, body: AskRequest) -> dict[str, Any]:
    await rate_limit(request, settings.api_rate_limit_ask)
    svc = AskService()
    result = await svc.ask(body.question)
    result["disclaimer"] = (
        "AI-generated from documented case timelines. Verify via the cited cases."
    )
    if posthog_client is not None:
        posthog_client.capture(
            "anonymous",
            "ask_question_submitted",
            {
                "question_length": len(body.question),
                "grounded": result.get("grounded", False),
                "citation_count": len(result.get("citations", [])),
            },
        )
    return result
