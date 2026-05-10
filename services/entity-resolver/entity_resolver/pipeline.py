"""Kafka pipeline for the entity-resolver service."""

from __future__ import annotations

import json
import signal
import time
import uuid
from typing import Any

import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
from prometheus_client import Counter, Histogram

from .config import settings
from .resolver import EntityResolver

logger = structlog.get_logger()

# ── Prometheus metrics ────────────────────────────────────────────────────────
CASES_RESOLVED_TOTAL = Counter(
    "entity_resolver_cases_resolved_total",
    "Total cases resolved",
    ["method"],
)
RESOLUTION_DURATION = Histogram(
    "entity_resolver_resolution_duration_seconds",
    "Time taken to resolve a case",
)
KAFKA_ERRORS_TOTAL = Counter(
    "entity_resolver_kafka_errors_total",
    "Total Kafka errors",
)


class EntityResolverPipeline:
    """Consumes extracted_events, resolves each case, produces to resolved_events."""

    def __init__(self, resolver: EntityResolver) -> None:
        self._resolver = resolver
        self._running = False

        self._consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_brokers,
                "group.id": settings.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        self._producer = Producer(
            {
                "bootstrap.servers": settings.kafka_brokers,
                "acks": "all",
                "retries": 5,
                "retry.backoff.ms": 200,
            }
        )

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        self._consumer.subscribe([settings.topic_extracted_events])
        logger.info(
            "entity_resolver_pipeline_started",
            topic=settings.topic_extracted_events,
        )

        def _shutdown(signum: int, frame: Any) -> None:
            logger.info("shutdown_signal_received")
            self._running = False

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)

        self._run_loop()

    def _run_loop(self) -> None:
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._async_loop())
        finally:
            loop.close()
            self._consumer.close()
            self._producer.flush()
            logger.info("entity_resolver_pipeline_stopped")

    async def _async_loop(self) -> None:
        while self._running:
            msg = self._consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                KAFKA_ERRORS_TOTAL.inc()
                logger.error("kafka_consumer_error", error=str(msg.error()))
                continue

            try:
                await self._process_message(msg)
                self._consumer.commit(message=msg, asynchronous=False)
            except Exception as exc:
                logger.exception("message_processing_failed", error=str(exc))
                KAFKA_ERRORS_TOTAL.inc()

    # ── message handling ──────────────────────────────────────────────────────

    async def _process_message(self, msg: Any) -> None:
        payload: dict = json.loads(msg.value().decode("utf-8"))

        from nyaya_shared.models import ExtractedCase

        extracted = ExtractedCase.model_validate(payload)
        sanitized_article_id = uuid.UUID(
            payload.get("sanitized_article_id", str(uuid.uuid4()))
        )

        start = time.monotonic()
        result = await self._resolver.resolve(extracted, sanitized_article_id)
        duration = time.monotonic() - start

        RESOLUTION_DURATION.observe(duration)
        CASES_RESOLVED_TOTAL.labels(method=result.resolution_method).inc()

        # Build outbound payload — merge original fields + resolution metadata
        out_payload = {
            **payload,
            "case_id": str(result.case_id),
            "resolution_method": result.resolution_method,
            "resolution_confidence": result.confidence,
            "is_new_case": result.is_new,
        }

        self._producer.produce(
            topic=settings.topic_resolved_events,
            key=str(result.case_id).encode("utf-8"),
            value=json.dumps(out_payload).encode("utf-8"),
            on_delivery=self._on_delivery,
        )
        self._producer.poll(0)

        logger.info(
            "case_resolved",
            case_id=str(result.case_id),
            method=result.resolution_method,
            confidence=result.confidence,
            duration_ms=round(duration * 1000, 1),
        )

    @staticmethod
    def _on_delivery(err: Any, msg: Any) -> None:
        if err:
            logger.error("kafka_produce_error", error=str(err))
            KAFKA_ERRORS_TOTAL.inc()
