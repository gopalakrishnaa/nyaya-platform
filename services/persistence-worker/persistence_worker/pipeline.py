from __future__ import annotations

import json
from typing import Any

import structlog
from confluent_kafka import Consumer, KafkaError, Producer

from nyaya_shared.kafka_schemas import (
    CONSUMER_GROUP_PERSISTENCE_WORKER,
    TOPIC_RESOLVED_EVENTS,
)

from .config import settings
from .opensearch_client import SearchService

logger = structlog.get_logger()


def _build_case_doc(payload: dict[str, Any]) -> dict[str, Any]:
    """Build OpenSearch document from resolved event payload."""
    incident_date = payload.get("incident_date")
    incident_year = None
    if incident_date:
        try:
            incident_year = int(incident_date[:4])
        except (TypeError, ValueError):
            pass

    events_summary = [
        {
            "event_type": e.get("event_type"),
            "event_category": e.get("event_category"),
            "event_date": e.get("event_date"),
            "summary": e.get("summary", ""),
        }
        for e in payload.get("events", [])
    ]

    # Build searchable full_text (no PII — only structural data)
    full_text_parts = [
        payload.get("case_ref", ""),
        payload.get("crime_category", ""),
        payload.get("state", ""),
        payload.get("district", ""),
    ] + [e.get("summary", "") for e in payload.get("events", [])]

    return {
        "id": payload.get("case_id") or payload.get("id"),
        "case_ref": payload.get("case_ref", ""),
        "crime_category": payload.get("crime_category"),
        "status": payload.get("status", "REPORTED"),
        "state": payload.get("state"),
        "district": payload.get("district"),
        "ipc_sections": payload.get("ipc_sections", []),
        "pocso_applicable": payload.get("pocso_applicable", False),
        "fast_track_court": payload.get("fast_track_court", False),
        "conviction_achieved": payload.get("conviction_achieved", False),
        "is_suppressed": payload.get("is_suppressed", False),
        "victim_age_group": payload.get("victim_age_group"),
        "incident_year": incident_year,
        "event_count": len(payload.get("events", [])),
        "last_event_at": payload.get("last_event_at"),
        "overall_confidence": payload.get("overall_confidence"),
        "full_text": " ".join(p for p in full_text_parts if p),
        "events_summary": events_summary,
    }


class PersistenceWorkerPipeline:
    def __init__(self) -> None:
        self._search = SearchService(
            url=settings.opensearch_url,
            username=settings.opensearch_username,
            password=settings.opensearch_password,
            index=settings.opensearch_index,
        )
        self._consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_brokers,
                "group.id": CONSUMER_GROUP_PERSISTENCE_WORKER,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )

    def run(self) -> None:
        self._search.ensure_index()
        self._consumer.subscribe([TOPIC_RESOLVED_EVENTS])
        logger.info("persistence_worker_started")

        try:
            while True:
                msg = self._consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error("kafka_error", error=str(msg.error()))
                    continue

                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                    case_id = payload.get("case_id") or payload.get("id")

                    if payload.get("is_suppressed"):
                        if case_id:
                            self._search.delete_case(str(case_id))
                            logger.info("case_suppressed_deleted", case_id=str(case_id))
                    else:
                        doc = _build_case_doc(payload)
                        self._search.index_case(doc)
                        logger.info("case_indexed", case_id=str(case_id))

                    self._consumer.commit(message=msg)

                except Exception as exc:
                    logger.error("pipeline_error", error=str(exc), offset=msg.offset())

        finally:
            self._consumer.close()
