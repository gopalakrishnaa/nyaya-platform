"""PrivacyPipeline — consumes raw articles and emits sanitized articles."""

from __future__ import annotations

import json

import structlog
from confluent_kafka import Consumer, KafkaError, Producer

from nyaya_shared.kafka_schemas import (
    CONSUMER_GROUP_PRIVACY_ENGINE,
    TOPIC_RAW_ARTICLES,
    TOPIC_SANITIZED_ARTICLES,
)
from nyaya_shared.models import RawArticle, RedactionEntry, SanitizedArticle

from .config import settings
from .redactors import (
    AddressMasker,
    ImageClassifier,
    MinorDetector,
    NameRedactor,
    PhoneEmailRedactor,
)

logger = structlog.get_logger()


class PrivacyPipeline:
    """End-to-end privacy pipeline: minor check → name redact → address mask → contact redact."""

    def __init__(self) -> None:
        self.minor_detector = MinorDetector(settings.minor_suppression_threshold)
        self.name_redactor = NameRedactor(spacy_model=settings.spacy_model_en)
        self.address_masker = AddressMasker()
        self.phone_email_redactor = PhoneEmailRedactor()
        self.image_classifier = ImageClassifier()

        self._consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_brokers,
                "group.id": CONSUMER_GROUP_PRIVACY_ENGINE,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,  # manual commit only after successful emit
            }
        )
        self._producer = Producer(
            {
                "bootstrap.servers": settings.kafka_brokers,
                "enable.idempotence": True,
            }
        )

    def process(self, raw: RawArticle, temp_case_id: str) -> SanitizedArticle:
        """Process a raw article through the full privacy pipeline.

        Steps:
        1. Minor detection (highest priority — suppresses entire article)
        2. Name redaction (victim → pseudonym, accused → hash)
        3. Address masking
        4. Phone/email redaction
        """
        redaction_log: list[RedactionEntry] = []

        combined_text = f"{raw.title or ''}\n{raw.body_text}"

        # ── Step 1: Minor detection ───────────────────────────────────────────
        minor_result = self.minor_detector.detect(combined_text)

        if minor_result.should_suppress:
            logger.info(
                "article_suppressed_minor",
                article_id=str(raw.id),
                minor_confidence=minor_result.confidence,
            )
            return SanitizedArticle(
                raw_article_id=raw.id,
                title_sanitized="[SUPPRESSED — Minor Involved]",
                body_sanitized=(
                    "[This article has been suppressed as it involves a minor victim "
                    "per POCSO Act protections.]"
                ),
                redaction_level="SUPPRESSED",
                is_suppressed=True,
                suppression_reason="MINOR_VICTIM_DETECTED",
                is_minor_involved=True,
                minor_confidence=minor_result.confidence,
                redaction_log=[],
            )

        # Check for images — flag separately (does not block processing)
        if self.image_classifier.has_images(raw.model_dump()):
            logger.warning(
                "article_has_images_flagged",
                article_id=str(raw.id),
                action="HOLD_FOR_MANUAL_REVIEW",
            )

        title = raw.title or ""
        body = raw.body_text
        lang = raw.language_code or "en"

        # ── Step 2: Name redaction ────────────────────────────────────────────
        title, title_name_log = self.name_redactor.redact(title, temp_case_id, lang)
        body, body_name_log = self.name_redactor.redact(body, temp_case_id, lang)
        redaction_log.extend(title_name_log)
        redaction_log.extend(body_name_log)

        # ── Step 3: Address masking ───────────────────────────────────────────
        title, title_addr_log = self.address_masker.mask(title)
        body, body_addr_log = self.address_masker.mask(body)
        redaction_log.extend(title_addr_log)
        redaction_log.extend(body_addr_log)

        # ── Step 4: Phone/email redaction ─────────────────────────────────────
        title, title_contact_log = self.phone_email_redactor.redact(title)
        body, body_contact_log = self.phone_email_redactor.redact(body)
        redaction_log.extend(title_contact_log)
        redaction_log.extend(body_contact_log)

        level = (
            "FULL"
            if len(redaction_log) > 5
            else ("PARTIAL" if redaction_log else "NONE")
        )

        logger.info(
            "article_sanitized",
            article_id=str(raw.id),
            redaction_count=len(redaction_log),
            level=level,
        )

        return SanitizedArticle(
            raw_article_id=raw.id,
            title_sanitized=title if title else None,
            body_sanitized=body,
            redaction_level=level,
            redaction_log=redaction_log,
            is_suppressed=False,
            is_minor_involved=minor_result.is_minor_involved,
            minor_confidence=minor_result.confidence if minor_result.is_minor_involved else None,
        )

    def run(self) -> None:
        """Main loop: consume raw articles, sanitize, produce to sanitized topic."""
        self._consumer.subscribe([TOPIC_RAW_ARTICLES])
        logger.info("privacy_engine_started", brokers=settings.kafka_brokers)

        try:
            while True:
                msg = self._consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error("kafka_consumer_error", error=str(msg.error()))
                    continue

                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                    raw = RawArticle(**payload)

                    # Use sha256_hash as stable case_id for name pseudonymisation
                    temp_case_id = raw.sha256_hash

                    sanitized = self.process(raw, temp_case_id)

                    # Produce BEFORE committing offset (at-least-once guarantee)
                    out_payload = sanitized.model_dump_json().encode("utf-8")
                    self._producer.produce(
                        topic=TOPIC_SANITIZED_ARTICLES,
                        key=str(raw.id).encode("utf-8"),
                        value=out_payload,
                    )
                    self._producer.flush()

                    # Only commit offset after successful produce
                    self._consumer.commit(message=msg)

                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "pipeline_processing_error",
                        error=str(exc),
                        msg_offset=msg.offset(),
                        exc_info=True,
                    )

        finally:
            self._consumer.close()

    def close(self) -> None:
        """Gracefully shut down consumer and flush producer."""
        self._consumer.close()
        self._producer.flush()
