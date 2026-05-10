from __future__ import annotations

import json
import uuid
from datetime import date

import structlog
from confluent_kafka import Consumer, KafkaError, Producer

from nyaya_shared.kafka_schemas import CONSUMER_GROUP_TIMELINE_ENGINE, TOPIC_RESOLVED_EVENTS

from .builder import TimelineBuilder
from .config import settings

logger = structlog.get_logger()


class TimelinePipeline:
    def __init__(self) -> None:
        self._builder = TimelineBuilder()
        self._consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_brokers,
                "group.id": CONSUMER_GROUP_TIMELINE_ENGINE,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        self._producer = Producer({"bootstrap.servers": settings.kafka_brokers})

    def run(self) -> None:
        self._consumer.subscribe([TOPIC_RESOLVED_EVENTS])
        logger.info("timeline_engine_started")

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
                    case_id_str = payload.get("case_id")
                    if not case_id_str:
                        self._consumer.commit(message=msg)
                        continue

                    case_id = uuid.UUID(case_id_str)
                    events = payload.get("events", [])
                    pocso = payload.get("pocso_applicable", False)

                    # Convert date strings to date objects
                    for event in events:
                        if event.get("event_date") and isinstance(event["event_date"], str):
                            try:
                                event["event_date"] = date.fromisoformat(event["event_date"])
                            except ValueError:
                                event["event_date"] = None

                    timeline = self._builder.build(case_id, events, pocso=pocso)

                    out = {
                        "case_id": str(case_id),
                        "timeline": timeline.model_dump(mode="json"),
                    }
                    self._producer.produce(
                        topic=settings.kafka_topic_timeline,
                        key=str(case_id).encode("utf-8"),
                        value=json.dumps(out).encode("utf-8"),
                    )
                    self._producer.flush()
                    self._consumer.commit(message=msg)

                    logger.info(
                        "timeline_built",
                        case_id=case_id_str,
                        stages=len(timeline.stages),
                        gaps=len(timeline.gaps),
                    )

                except Exception as exc:
                    logger.error("pipeline_error", error=str(exc), offset=msg.offset())

        finally:
            self._consumer.close()
