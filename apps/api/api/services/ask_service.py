from __future__ import annotations

from typing import Any

import anthropic
import structlog

from ..config import settings
from .search_service import SearchService

logger = structlog.get_logger()

REFUSAL_ANSWER = (
    "I could not find documented cases that answer this question. "
    "Try rephrasing, or browse cases directly via search."
)

SYSTEM_PROMPT = """You answer questions about crimes against women in India's \
legal system, using ONLY the documented case timelines provided below.

Rules:
1. Base every claim on the provided cases. Cite each claim with the case \
reference in square brackets, e.g. [MH-2024-001234].
2. If the provided cases do not answer the question, say so plainly. Do not \
guess or use outside knowledge.
3. Never name or speculate about victims or accused. Use only the pseudonyms \
present in the data.
4. Do not offer opinions on guilt, innocence, or the merits of pending cases. \
Report documented events and statutory deadlines only.
5. Be concise. Plain language, no legal jargon without explanation."""


class AskService:
    def __init__(self, search: SearchService | None = None) -> None:
        self._search = search or SearchService()
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def ask(self, question: str) -> dict[str, Any]:
        results = self._search.search(
            query=question,
            from_=0,
            size=settings.ask_max_cases,
            include_aggs=False,
        )
        hits = results.get("hits", {}).get("hits", [])
        if not hits:
            return {"answer": REFUSAL_ANSWER, "citations": [], "grounded": False}

        case_refs, context = self._build_context(hits)

        response = await self._client.messages.create(
            model=settings.ask_model,
            max_tokens=1024,
            temperature=0.0,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Documented cases:\n\n{context}\n\nQuestion: {question}",
                }
            ],
        )
        answer = response.content[0].text

        citations = [ref for ref in case_refs if f"[{ref}]" in answer]
        if not citations:
            logger.warning("ask_uncited_answer", question=question)
            return {"answer": REFUSAL_ANSWER, "citations": [], "grounded": False}

        return {"answer": answer, "citations": citations, "grounded": True}

    @staticmethod
    def _build_context(hits: list[dict[str, Any]]) -> tuple[list[str], str]:
        case_refs: list[str] = []
        blocks: list[str] = []
        for hit in hits:
            src = hit.get("_source", {})
            ref = src.get("case_ref")
            if not ref:
                continue
            case_refs.append(ref)
            events = src.get("events_summary", [])
            event_lines = "\n".join(
                f"  - {e.get('event_date', 'date unknown')}: {e.get('summary', '')}"
                for e in events
            )
            blocks.append(
                f"[{ref}] {src.get('crime_category', '')} | "
                f"{src.get('state', '')} | status: {src.get('status', '')}\n"
                f"{event_lines}"
            )
        return case_refs, "\n\n".join(blocks)
