"""Tests for FIR number exact matching in entity_resolver.resolver.EntityResolver.

EntityResolver.resolve(extracted, sanitized_article_id) is async.
It takes a db_session_factory (async context manager factory).

Priority order for resolution:
  1. FIR exact match  (fir_number + fir_police_station)
  2. Court case exact match
  3. Embedding similarity
  4. New case creation

These tests focus on step 1 (FIR match) by:
  - Mocking the DB session factory so no real DB is touched.
  - Patching heavy dependencies (sentence_transformers, anthropic) to
    avoid network/model loading.

Run with: pytest -p asyncio_mode=auto  or configure asyncio_mode in pyproject.toml.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from entity_resolver.resolver import EntityResolver, ResolutionResult
except ModuleNotFoundError:  # pragma: no cover
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from entity_resolver.resolver import EntityResolver, ResolutionResult

try:
    from nyaya_shared.models import ExtractedCase, ExtractedEvent
except ModuleNotFoundError:  # pragma: no cover
    import sys, os
    sys.path.insert(
        0,
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared-python"),
    )
    from nyaya_shared.models import ExtractedCase, ExtractedEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXISTING_CASE_ID = uuid.uuid4()
ARTICLE_ID = uuid.uuid4()


def _make_case(
    fir_number: str | None = "123/2023",
    fir_police_station: str | None = "Banjara Hills PS",
    **kwargs,
) -> ExtractedCase:
    defaults = dict(
        crime_category="RAPE",
        state="Telangana",
        district="Hyderabad",
        fir_number=fir_number,
        fir_police_station=fir_police_station,
        ipc_sections=[376],
    )
    defaults.update(kwargs)
    return ExtractedCase(**defaults)


def _make_session_factory(fetchone_return=None) -> MagicMock:
    """Build a mock async session factory.

    The factory is called as:
        async with self._db() as session:
            result = await session.execute(...)
            row = result.fetchone()

    fetchone_return: what result.fetchone() returns.
      - tuple/list → FIR/court match found
      - None       → no match
    """
    mock_result = MagicMock()
    mock_result.fetchone.return_value = fetchone_return
    mock_result.fetchall.return_value = []   # no embedding candidates
    mock_result.scalar.return_value = 1       # seq for new case creation

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    # Support `async with factory() as session`
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_session
    mock_ctx.__aexit__.return_value = False

    mock_factory = MagicMock(return_value=mock_ctx)
    return mock_factory


def _make_resolver(fetchone_return=None) -> EntityResolver:
    """Return an EntityResolver with all heavy deps patched."""
    factory = _make_session_factory(fetchone_return=fetchone_return)
    with (
        patch("entity_resolver.resolver.anthropic.Anthropic"),
        patch("entity_resolver.resolver.SentenceTransformer"),
    ):
        resolver = EntityResolver(db_session_factory=factory)
    return resolver


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFirExactMatch:
    """Two events with same fir_number + fir_police_station → existing case returned."""

    @pytest.mark.asyncio
    async def test_fir_match_returns_existing_case_id(self):
        resolver = _make_resolver(fetchone_return=(EXISTING_CASE_ID,))

        with (
            patch("entity_resolver.resolver.anthropic.Anthropic"),
            patch("entity_resolver.resolver.SentenceTransformer"),
        ):
            case = _make_case(fir_number="123/2023", fir_police_station="Banjara Hills PS")
            result = await resolver.resolve(case, ARTICLE_ID)

        assert result.case_id == EXISTING_CASE_ID

    @pytest.mark.asyncio
    async def test_fir_match_resolution_method_is_fir_exact(self):
        resolver = _make_resolver(fetchone_return=(EXISTING_CASE_ID,))

        with (
            patch("entity_resolver.resolver.anthropic.Anthropic"),
            patch("entity_resolver.resolver.SentenceTransformer"),
        ):
            case = _make_case(fir_number="123/2023", fir_police_station="Banjara Hills PS")
            result = await resolver.resolve(case, ARTICLE_ID)

        assert result.resolution_method == "FIR_EXACT"

    @pytest.mark.asyncio
    async def test_fir_match_confidence_is_one(self):
        resolver = _make_resolver(fetchone_return=(EXISTING_CASE_ID,))

        with (
            patch("entity_resolver.resolver.anthropic.Anthropic"),
            patch("entity_resolver.resolver.SentenceTransformer"),
        ):
            case = _make_case()
            result = await resolver.resolve(case, ARTICLE_ID)

        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_fir_match_is_not_new_case(self):
        resolver = _make_resolver(fetchone_return=(EXISTING_CASE_ID,))

        with (
            patch("entity_resolver.resolver.anthropic.Anthropic"),
            patch("entity_resolver.resolver.SentenceTransformer"),
        ):
            case = _make_case()
            result = await resolver.resolve(case, ARTICLE_ID)

        assert result.is_new is False


class TestFirNotInDb:
    """fir_number present but DB returns no match → falls through to new-case creation."""

    @pytest.mark.asyncio
    async def test_fir_miss_creates_new_case(self):
        resolver = _make_resolver(fetchone_return=None)

        with (
            patch("entity_resolver.resolver.anthropic.Anthropic"),
            patch("entity_resolver.resolver.SentenceTransformer"),
            patch("entity_resolver.resolver.victim_pseudonym", return_value="VICTIM-test"),
        ):
            case = _make_case(fir_number="999/2023", fir_police_station="Unknown PS")
            result = await resolver.resolve(case, ARTICLE_ID)

        assert result.resolution_method == "NEW_CASE"
        assert result.is_new is True

    @pytest.mark.asyncio
    async def test_fir_miss_returns_resolution_result(self):
        resolver = _make_resolver(fetchone_return=None)

        with (
            patch("entity_resolver.resolver.anthropic.Anthropic"),
            patch("entity_resolver.resolver.SentenceTransformer"),
            patch("entity_resolver.resolver.victim_pseudonym", return_value="VICTIM-test"),
        ):
            case = _make_case(fir_number="999/2023", fir_police_station="Unknown PS")
            result = await resolver.resolve(case, ARTICLE_ID)

        assert isinstance(result, ResolutionResult)
        assert isinstance(result.case_id, uuid.UUID)


class TestFirNumberNone:
    """fir_number=None → FIR match step skipped entirely.

    The resolver checks `if extracted.fir_number and extracted.fir_police_station`
    so with fir_number=None, it should not execute the FIR query at all.
    """

    @pytest.mark.asyncio
    async def test_none_fir_skips_fir_query(self):
        factory = _make_session_factory(fetchone_return=None)
        resolver_under_test: EntityResolver

        with (
            patch("entity_resolver.resolver.anthropic.Anthropic"),
            patch("entity_resolver.resolver.SentenceTransformer"),
        ):
            resolver_under_test = EntityResolver(db_session_factory=factory)

        # Track what SQL queries are executed
        executed_sql: list[str] = []

        # Intercept session.execute calls to check which queries fire
        async def _recording_execute(sql, *args, **kwargs):
            executed_sql.append(str(sql))
            result = MagicMock()
            result.fetchone.return_value = None
            result.fetchall.return_value = []
            result.scalar.return_value = 1
            return result

        mock_session = AsyncMock()
        mock_session.execute.side_effect = _recording_execute

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = False
        factory.return_value = mock_ctx

        with (
            patch("entity_resolver.resolver.anthropic.Anthropic"),
            patch("entity_resolver.resolver.SentenceTransformer"),
            patch("entity_resolver.resolver.victim_pseudonym", return_value="VICTIM-test"),
        ):
            case = _make_case(fir_number=None, fir_police_station=None)
            result = await resolver_under_test.resolve(case, ARTICLE_ID)

        # No SQL mentioning FIR match should have been executed
        fir_queries = [q for q in executed_sql if "fir_number" in q.lower()]
        assert fir_queries == [], (
            f"FIR match query should be skipped when fir_number=None, but got: {fir_queries}"
        )

    @pytest.mark.asyncio
    async def test_none_fir_still_returns_result(self):
        resolver = _make_resolver(fetchone_return=None)

        with (
            patch("entity_resolver.resolver.anthropic.Anthropic"),
            patch("entity_resolver.resolver.SentenceTransformer"),
            patch("entity_resolver.resolver.victim_pseudonym", return_value="VICTIM-test"),
        ):
            case = _make_case(fir_number=None, fir_police_station=None)
            result = await resolver.resolve(case, ARTICLE_ID)

        assert isinstance(result, ResolutionResult)

    @pytest.mark.asyncio
    async def test_none_fir_not_fir_exact_method(self):
        """When FIR number is absent, resolution should never be FIR_EXACT."""
        resolver = _make_resolver(fetchone_return=None)

        with (
            patch("entity_resolver.resolver.anthropic.Anthropic"),
            patch("entity_resolver.resolver.SentenceTransformer"),
            patch("entity_resolver.resolver.victim_pseudonym", return_value="VICTIM-test"),
        ):
            case = _make_case(fir_number=None, fir_police_station=None)
            result = await resolver.resolve(case, ARTICLE_ID)

        assert result.resolution_method != "FIR_EXACT"
