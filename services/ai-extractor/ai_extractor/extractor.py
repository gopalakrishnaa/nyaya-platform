from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any

import anthropic
import structlog
from pydantic import ValidationError

from nyaya_shared.models import ExtractedCase, SanitizedArticle
from nyaya_shared.taxonomy import VALID_EVENT_TYPES, EVENT_CATEGORY_MAP

from .config import settings
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = structlog.get_logger()

# Guards: first word >1 char, second word >2 chars — filters "New Delhi", "A Kumar", etc.
# Still imperfect (catches "Ram Singh") but blocks obvious place/org false positives.
NAME_PATTERN = re.compile(r"\b([A-Z][a-z]{2,15} [A-Z][a-z]{3,15})\b")


class ExtractionError(Exception):
    pass


class LLMExtractor:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def extract(
        self,
        sanitized: SanitizedArticle,
        source_code: str,
        trust_score: float,
        language_code: str,
        published_at: str | None,
        job_id: uuid.UUID,
    ) -> tuple[ExtractedCase, dict[str, Any]]:
        article_text = sanitized.body_sanitized[:8000]

        user_prompt = USER_PROMPT_TEMPLATE.format(
            source_code=source_code,
            trust_score=trust_score,
            language_code=language_code,
            published_at=published_at or "unknown",
            article_text=article_text,
        )

        model = settings.primary_model
        response: anthropic.types.Message

        start_time = time.monotonic()
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=settings.extraction_max_tokens,
                temperature=settings.extraction_temperature,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.BadRequestError as exc:
            # Content filter (HTTP 400). Same content will block haiku too — no retry.
            raise ExtractionError(f"Content filter: {exc}") from exc
        except anthropic.APIError as exc:
            logger.warning("primary_model_failed", error=str(exc), job_id=str(job_id))
            model = settings.fallback_model
            start_time = time.monotonic()  # reset — measure actual call latency
            try:
                response = self._client.messages.create(
                    model=model,
                    max_tokens=settings.extraction_max_tokens,
                    temperature=settings.extraction_temperature,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                )
            except anthropic.BadRequestError as exc2:
                raise ExtractionError(f"Content filter on fallback: {exc2}") from exc2
            except anthropic.APIError as exc3:
                raise ExtractionError(f"Fallback model failed: {exc3}") from exc3

        latency_ms = int((time.monotonic() - start_time) * 1000)
        raw_text = response.content[0].text.strip()

        job_meta: dict[str, Any] = {
            "job_id": str(job_id),
            "model_name": model,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            "latency_ms": latency_ms,
            "raw_output": raw_text[:500],  # cap to avoid bloating Kafka messages
        }

        extracted = self._parse_and_validate(raw_text, job_id)
        return extracted, job_meta

    def _parse_and_validate(self, raw_text: str, job_id: uuid.UUID) -> ExtractedCase:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"Invalid JSON from LLM: {exc}") from exc

        # Validate and fix event_types
        for event in data.get("events", []):
            if event.get("event_type") not in VALID_EVENT_TYPES:
                logger.warning(
                    "invalid_event_type",
                    event_type=event.get("event_type"),
                    job_id=str(job_id),
                )
                event["event_type"] = "MEDIA_REPORT"
            # Auto-fill event_category from map
            etype = event.get("event_type", "MEDIA_REPORT")
            event["event_category"] = EVENT_CATEGORY_MAP.get(etype, "ADMINISTRATIVE")
            # PII guard: check summary for name-like strings
            summary = event.get("summary", "")
            if summary and NAME_PATTERN.search(summary):
                logger.warning("pii_in_summary", job_id=str(job_id))
                event["summary"] = NAME_PATTERN.sub("[NAME_REDACTED]", summary)

        try:
            return ExtractedCase(**data)
        except ValidationError as exc:
            raise ExtractionError(f"Pydantic validation failed: {exc}") from exc
