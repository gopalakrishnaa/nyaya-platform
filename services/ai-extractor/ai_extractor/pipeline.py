from __future__ import annotations

import json
import uuid

import structlog
from confluent_kafka import Consumer, KafkaError, Producer

from nyaya_shared.models import SanitizedArticle
from nyaya_shared.kafka_schemas import (
    CONSUMER_GROUP_AI_EXTRACTOR,
    TOPIC_EXTRACTED_EVENTS,
    TOPIC_LOW_CONFIDENCE,
    TOPIC_SANITIZED_ARTICLES,
)

from .confidence_scorer import ConfidenceScorer
from .config import settings
from .extractor import ExtractionError, LLMExtractor

logger = structlog.get_logger()


class AiExtractorPipeline:
    def __init__(self) -> None:
        self._extractor = LLMExtractor()
        self._scorer = ConfidenceScorer()

        self._consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_brokers,
                "group.id": CONSUMER_GROUP_AI_EXTRACTOR,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        self._producer = Producer(
            {
                "bootstrap.servers": settings.kafka_brokers,
                "enable.idempotence": True,
            }
        )

    def run(self) -> None:
        self._consumer.subscribe([TOPIC_SANITIZED_ARTICLES])
        logger.info("ai_extractor_started")

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
                    sanitized = SanitizedArticle(**payload)

                    if sanitized.is_suppressed:
                        self._consumer.commit(message=msg)
                        continue

                    source_code = payload.get("source_code", "UNKNOWN")
                    trust_score = float(payload.get("source_trust_score", 0.70))
                    language_code = payload.get("language_code", "en")
                    published_at = payload.get("published_at")
                    job_id = uuid.uuid4()

                    try:
                        extracted, job_meta = self._extractor.extract(
                            sanitized=sanitized,
                            source_code=source_code,
                            trust_score=trust_score,
                            language_code=language_code,
                            published_at=published_at,
                            job_id=job_id,
                        )
                    except ExtractionError as exc:
                        logger.warning(
                            "extraction_error",
                            error=str(exc),
                            article_id=str(sanitized.id),
                        )
                        # Route to low-confidence so it's archived, not silently lost.
                        self._producer.produce(
                            topic=TOPIC_LOW_CONFIDENCE,
                            key=str(sanitized.id).encode("utf-8"),
                            value=json.dumps({
                                "sanitized_article_id": str(sanitized.id),
                                "error": str(exc),
                                "source_code": source_code,
                            }).encode("utf-8"),
                        )
                        self._producer.flush(timeout=2.0)
                        self._consumer.commit(message=msg)
                        continue

                    confidence = self._scorer.score(extracted, trust_score)

                    out: dict = extracted.model_dump(mode="json")
                    out["sanitized_article_id"] = str(sanitized.id)
                    out["job_meta"] = job_meta
                    out["computed_confidence"] = confidence
                    out["auto_approved"] = (
                        confidence >= settings.auto_approve_confidence
                        or (
                            confidence >= settings.auto_approve_tier1_confidence
                            and trust_score >= settings.auto_approve_tier1_trust
                        )
                    )

                    # Route by confidence
                    if confidence >= settings.human_review_threshold:
                        target_topic = TOPIC_EXTRACTED_EVENTS
                    else:
                        target_topic = TOPIC_LOW_CONFIDENCE

                    self._producer.produce(
                        topic=target_topic,
                        key=str(sanitized.id).encode("utf-8"),
                        value=json.dumps(out).encode("utf-8"),
                    )
                    self._producer.flush()
                    self._consumer.commit(message=msg)

                    logger.info(
                        "extraction_complete",
                        article_id=str(sanitized.id),
                        confidence=confidence,
                        auto_approved=out["auto_approved"],
                        topic=target_topic,
                    )

                except Exception as exc:
                    logger.error(
                        "pipeline_error",
                        error=str(exc),
                        offset=msg.offset(),
                    )
                    # Always commit — malformed payload will loop forever otherwise.
                    try:
                        self._producer.produce(
                            topic=TOPIC_LOW_CONFIDENCE,
                            key=b"unknown",
                            value=json.dumps({"error": str(exc), "offset": msg.offset()}).encode(),
                        )
                        self._producer.flush(timeout=2.0)
                    except Exception:
                        pass
                    self._consumer.commit(message=msg)

        finally:
            self._consumer.close()
