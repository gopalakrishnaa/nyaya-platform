"""Tests for POST /v1/ask (AskService grounding and citation enforcement)."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.ask_service import REFUSAL_ANSWER, AskService


def _search_results(hits: list[dict[str, Any]]) -> dict[str, Any]:
    return {"hits": {"hits": hits}}


def _hit(case_ref: str) -> dict[str, Any]:
    return {
        "_source": {
            "case_ref": case_ref,
            "crime_category": "RAPE",
            "state": "Maharashtra",
            "status": "TRIAL",
            "events_summary": [
                {"event_date": "2024-01-05", "summary": "FIR registered"},
                {"event_date": "2024-04-20", "summary": "Chargesheet filed"},
            ],
        }
    }


def _claude_response(text: str) -> MagicMock:
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def _make_service(hits: list[dict[str, Any]], answer: str | None = None) -> AskService:
    search = MagicMock()
    search.search.return_value = _search_results(hits)
    with patch("api.services.ask_service.anthropic.AsyncAnthropic"):
        svc = AskService(search=search)
    if answer is not None:
        svc._client.messages.create = AsyncMock(return_value=_claude_response(answer))
    return svc


class TestAskService:
    @pytest.mark.asyncio
    async def test_no_hits_refuses_without_llm_call(self) -> None:
        svc = _make_service(hits=[])
        result = await svc.ask("how long do POCSO cases take in Bihar?")
        assert result["grounded"] is False
        assert result["answer"] == REFUSAL_ANSWER
        assert result["citations"] == []

    @pytest.mark.asyncio
    async def test_cited_answer_is_grounded(self) -> None:
        svc = _make_service(
            hits=[_hit("MH-2024-001234")],
            answer="The chargesheet was filed in 105 days [MH-2024-001234].",
        )
        result = await svc.ask("how long until chargesheet in Maharashtra?")
        assert result["grounded"] is True
        assert result["citations"] == ["MH-2024-001234"]

    @pytest.mark.asyncio
    async def test_uncited_answer_is_refused(self) -> None:
        svc = _make_service(
            hits=[_hit("MH-2024-001234")],
            answer="Cases generally take several months.",
        )
        result = await svc.ask("how long until chargesheet in Maharashtra?")
        assert result["grounded"] is False
        assert result["answer"] == REFUSAL_ANSWER

    @pytest.mark.asyncio
    async def test_only_actually_cited_refs_returned(self) -> None:
        svc = _make_service(
            hits=[_hit("MH-2024-001234"), _hit("UP-2024-005678")],
            answer="One case shows a 105-day delay [MH-2024-001234].",
        )
        result = await svc.ask("chargesheet delays?")
        assert result["citations"] == ["MH-2024-001234"]

    def test_build_context_skips_hits_without_case_ref(self) -> None:
        refs, context = AskService._build_context(
            [_hit("MH-2024-001234"), {"_source": {"state": "Bihar"}}]
        )
        assert refs == ["MH-2024-001234"]
        assert "Bihar" not in context
