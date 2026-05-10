"""Tests for persistence_worker.opensearch_client.SearchService."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from persistence_worker.opensearch_client import SearchService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(mock_os_client: MagicMock) -> SearchService:
    """Return a SearchService whose internal OpenSearch client is replaced."""
    with patch("persistence_worker.opensearch_client.OpenSearch", return_value=mock_os_client):
        svc = SearchService(
            url="http://localhost:9200",
            username="",
            password="",
            index="nyaya-cases",
        )
    return svc


# ---------------------------------------------------------------------------
# search() — query text
# ---------------------------------------------------------------------------

class TestSearchWithQuery:
    def test_query_builds_multi_match_request(self) -> None:
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        svc = _make_service(mock_client)
        svc.search(query="rape")

        assert mock_client.search.called
        call_kwargs = mock_client.search.call_args
        # Accept positional or keyword argument for body
        body = (
            call_kwargs.kwargs.get("body")
            or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
        )
        assert body is not None, "Expected 'body' argument in opensearch.search() call"

        must_clauses = body["query"]["bool"]["must"]
        multi_match_clauses = [c for c in must_clauses if "multi_match" in c]
        assert len(multi_match_clauses) == 1, "Expected exactly one multi_match clause"
        assert multi_match_clauses[0]["multi_match"]["query"] == "rape"

    def test_query_uses_multi_match_not_bare_match(self) -> None:
        """Ensures we emit multi_match (cross-field) rather than a plain match."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        svc = _make_service(mock_client)
        svc.search(query="rape")

        body = mock_client.search.call_args.kwargs.get("body") or mock_client.search.call_args.args[1]
        must_clauses = body["query"]["bool"]["must"]
        bare_match_clauses = [c for c in must_clauses if "match" in c and "multi_match" not in c]
        assert bare_match_clauses == [], "Should not use bare 'match' clause for text queries"


# ---------------------------------------------------------------------------
# search() — suppression filter always present
# ---------------------------------------------------------------------------

class TestSearchSuppressionFilter:
    def test_always_adds_is_suppressed_false_filter(self) -> None:
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        svc = _make_service(mock_client)
        svc.search()  # no query, no filters

        body = mock_client.search.call_args.kwargs.get("body") or mock_client.search.call_args.args[1]
        filter_clauses = body["query"]["bool"]["filter"]
        suppression_filter = {"term": {"is_suppressed": False}}
        assert suppression_filter in filter_clauses, (
            f"Expected {suppression_filter} in filter clauses, got: {filter_clauses}"
        )

    def test_suppression_filter_present_even_with_other_filters(self) -> None:
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        svc = _make_service(mock_client)
        svc.search(query="murder", filters={"state": "Maharashtra"})

        body = mock_client.search.call_args.kwargs.get("body") or mock_client.search.call_args.args[1]
        filter_clauses = body["query"]["bool"]["filter"]
        assert {"term": {"is_suppressed": False}} in filter_clauses


# ---------------------------------------------------------------------------
# search() — state filter
# ---------------------------------------------------------------------------

class TestSearchWithStateFilter:
    def test_state_filter_adds_term_clause(self) -> None:
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        svc = _make_service(mock_client)
        svc.search(filters={"state": "Maharashtra"})

        body = mock_client.search.call_args.kwargs.get("body") or mock_client.search.call_args.args[1]
        filter_clauses = body["query"]["bool"]["filter"]
        state_filter = {"term": {"state": "Maharashtra"}}
        assert state_filter in filter_clauses, (
            f"Expected state term filter in {filter_clauses}"
        )

    def test_state_filter_does_not_replace_suppression_filter(self) -> None:
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        svc = _make_service(mock_client)
        svc.search(filters={"state": "Maharashtra"})

        body = mock_client.search.call_args.kwargs.get("body") or mock_client.search.call_args.args[1]
        filter_clauses = body["query"]["bool"]["filter"]
        # Both filters must be present
        assert {"term": {"is_suppressed": False}} in filter_clauses
        assert {"term": {"state": "Maharashtra"}} in filter_clauses


# ---------------------------------------------------------------------------
# index_case()
# ---------------------------------------------------------------------------

class TestIndexCase:
    def test_calls_opensearch_index_with_correct_index_name(self) -> None:
        mock_client = MagicMock()
        svc = _make_service(mock_client)

        case_doc = {
            "id": "case-001",
            "case_ref": "MH/2024/001",
            "crime_category": "RAPE",
            "is_suppressed": False,
        }
        svc.index_case(case_doc)

        assert mock_client.index.called, "opensearch.index() was not called"
        call_kwargs = mock_client.index.call_args.kwargs
        assert call_kwargs.get("index") == "nyaya-cases", (
            f"Expected index='nyaya-cases', got index='{call_kwargs.get('index')}'"
        )

    def test_index_case_uses_document_id(self) -> None:
        mock_client = MagicMock()
        svc = _make_service(mock_client)

        case_doc = {"id": "case-xyz", "case_ref": "DL/2024/007"}
        svc.index_case(case_doc)

        call_kwargs = mock_client.index.call_args.kwargs
        assert call_kwargs.get("id") == "case-xyz"

    def test_index_case_passes_full_document_as_body(self) -> None:
        mock_client = MagicMock()
        svc = _make_service(mock_client)

        case_doc = {"id": "case-abc", "case_ref": "KA/2024/010", "state": "Karnataka"}
        svc.index_case(case_doc)

        call_kwargs = mock_client.index.call_args.kwargs
        assert call_kwargs.get("body") == case_doc


# ---------------------------------------------------------------------------
# delete_case()
# ---------------------------------------------------------------------------

class TestDeleteCase:
    def test_calls_opensearch_delete_with_case_id(self) -> None:
        mock_client = MagicMock()
        svc = _make_service(mock_client)

        svc.delete_case("case-to-delete-999")

        assert mock_client.delete.called, "opensearch.delete() was not called"
        call_kwargs = mock_client.delete.call_args.kwargs
        assert call_kwargs.get("id") == "case-to-delete-999", (
            f"Expected id='case-to-delete-999', got id='{call_kwargs.get('id')}'"
        )

    def test_delete_case_targets_correct_index(self) -> None:
        mock_client = MagicMock()
        svc = _make_service(mock_client)

        svc.delete_case("case-42")

        call_kwargs = mock_client.delete.call_args.kwargs
        assert call_kwargs.get("index") == "nyaya-cases"

    def test_delete_case_ignores_404(self) -> None:
        """delete() should be called with ignore=[404] so missing docs don't raise."""
        mock_client = MagicMock()
        svc = _make_service(mock_client)

        svc.delete_case("nonexistent-case")

        call_kwargs = mock_client.delete.call_args.kwargs
        assert 404 in (call_kwargs.get("ignore") or []), (
            "Expected ignore=[404] in delete() call to handle missing documents gracefully"
        )
