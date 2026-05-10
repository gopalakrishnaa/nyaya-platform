from __future__ import annotations

from typing import Any

from opensearchpy import OpenSearch

from ..config import settings


class SearchService:
    def __init__(self) -> None:
        self._client = OpenSearch(
            hosts=[settings.opensearch_url],
            http_auth=(
                (settings.opensearch_username, settings.opensearch_password)
                if settings.opensearch_username
                else None
            ),
            use_ssl=settings.opensearch_url.startswith("https"),
            verify_certs=False,
            ssl_show_warn=False,
        )
        self._index = settings.opensearch_index

    def search(
        self,
        query: str | None = None,
        filters: dict[str, Any] | None = None,
        from_: int = 0,
        size: int = 20,
        include_aggs: bool = True,
    ) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        filter_clauses: list[dict[str, Any]] = [
            {"term": {"is_suppressed": False}}
        ]

        if query:
            must.append(
                {
                    "multi_match": {
                        "query": query,
                        "fields": ["case_ref^3", "full_text", "events_summary.summary"],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                }
            )

        if filters:
            for field, value in filters.items():
                if value is not None:
                    if isinstance(value, list):
                        filter_clauses.append({"terms": {field: value}})
                    else:
                        filter_clauses.append({"term": {field: value}})

        body: dict[str, Any] = {
            "from": from_,
            "size": size,
            "query": {
                "bool": {
                    "must": must if must else [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            "highlight": {"fields": {"full_text": {}}},
        }

        if include_aggs:
            body["aggs"] = {
                "by_status": {"terms": {"field": "status", "size": 20}},
                "by_category": {"terms": {"field": "crime_category", "size": 20}},
                "by_state": {"terms": {"field": "state", "size": 40}},
                "by_year": {"terms": {"field": "incident_year", "size": 10}},
                "pocso_count": {"filter": {"term": {"pocso_applicable": True}}},
                "fast_track_count": {"filter": {"term": {"fast_track_court": True}}},
                "conviction_count": {"filter": {"term": {"conviction_achieved": True}}},
            }

        try:
            return self._client.search(index=self._index, body=body)  # type: ignore[no-any-return]
        except Exception:
            return {"hits": {"hits": [], "total": {"value": 0}}, "aggregations": {}}
