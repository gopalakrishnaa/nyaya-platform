from __future__ import annotations

from typing import Any

import structlog
from opensearchpy import OpenSearch

logger = structlog.get_logger()

CASES_INDEX_MAPPING: dict[str, Any] = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "autocomplete_analyzer": {
                    "tokenizer": "autocomplete_tokenizer",
                    "filter": ["lowercase"],
                },
                "autocomplete_search": {
                    "tokenizer": "lowercase",
                },
            },
            "tokenizer": {
                "autocomplete_tokenizer": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20,
                    "token_chars": ["letter", "digit"],
                },
            },
        },
    },
    "mappings": {
        "properties": {
            "case_ref": {
                "type": "text",
                "analyzer": "autocomplete_analyzer",
                "search_analyzer": "autocomplete_search",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "crime_category": {"type": "keyword"},
            "status": {"type": "keyword"},
            "state": {"type": "keyword"},
            "district": {"type": "keyword"},
            "ipc_sections": {"type": "integer"},
            "pocso_applicable": {"type": "boolean"},
            "fast_track_court": {"type": "boolean"},
            "conviction_achieved": {"type": "boolean"},
            "is_suppressed": {"type": "boolean"},
            "victim_age_group": {"type": "keyword"},
            "incident_year": {"type": "integer"},
            "event_count": {"type": "integer"},
            "last_event_at": {"type": "date"},
            "overall_confidence": {"type": "float"},
            "full_text": {
                "type": "text",
                "analyzer": "standard",
            },
            "events_summary": {
                "type": "nested",
                "properties": {
                    "event_type": {"type": "keyword"},
                    "event_category": {"type": "keyword"},
                    "event_date": {"type": "date"},
                    "summary": {"type": "text"},
                },
            },
        }
    },
}


class SearchService:
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        index: str,
    ) -> None:
        self._client = OpenSearch(
            hosts=[url],
            http_auth=(username, password) if username else None,
            use_ssl=url.startswith("https"),
            verify_certs=False,
            ssl_show_warn=False,
        )
        self._index = index

    def ensure_index(self) -> None:
        if not self._client.indices.exists(index=self._index):
            self._client.indices.create(index=self._index, body=CASES_INDEX_MAPPING)
            logger.info("opensearch_index_created", index=self._index)

    def index_case(self, case_doc: dict[str, Any]) -> None:
        self._client.index(
            index=self._index,
            id=case_doc["id"],
            body=case_doc,
            refresh=False,
        )

    def delete_case(self, case_id: str) -> None:
        self._client.delete(index=self._index, id=case_id, ignore=[404])

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
                        "fields": [
                            "case_ref^3",
                            "full_text",
                            "events_summary.summary",
                        ],
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
            "highlight": {
                "fields": {
                    "full_text": {},
                }
            },
        }

        if include_aggs:
            body["aggs"] = {
                "by_status": {"terms": {"field": "status", "size": 20}},
                "by_category": {"terms": {"field": "crime_category", "size": 20}},
                "by_state": {"terms": {"field": "state", "size": 40}},
                "by_year": {"terms": {"field": "incident_year", "size": 10}},
                "by_age_group": {"terms": {"field": "victim_age_group", "size": 10}},
                "pocso_count": {"filter": {"term": {"pocso_applicable": True}}},
                "fast_track_count": {"filter": {"term": {"fast_track_court": True}}},
                "conviction_count": {"filter": {"term": {"conviction_achieved": True}}},
            }

        return self._client.search(index=self._index, body=body)  # type: ignore[no-any-return]
