"""
nyaya_shared — Shared library for the Nyaya justice transparency platform.

Exports all public models, taxonomy constants, Kafka schema definitions,
and privacy utilities used across services.
"""
from __future__ import annotations

from nyaya_shared.kafka_schemas import (
    CONSUMER_GROUP_AI_EXTRACTOR,
    CONSUMER_GROUP_ENTITY_RESOLVER,
    CONSUMER_GROUP_PERSISTENCE_WORKER,
    CONSUMER_GROUP_PRIVACY_ENGINE,
    CONSUMER_GROUP_TIMELINE_ENGINE,
    TOPIC_EXTRACTED_EVENTS,
    TOPIC_LOW_CONFIDENCE,
    TOPIC_RAW_ARTICLES,
    TOPIC_RESOLVED_EVENTS,
    TOPIC_SANITIZED_ARTICLES,
    TOPIC_TIMELINE_UPDATES,
)
from nyaya_shared.models import (
    ExtractedCase,
    ExtractedEvent,
    RawArticle,
    RedactionEntry,
    SanitizedArticle,
    Timeline,
    TimelineGap,
    TimelineStage,
)
from nyaya_shared.privacy_utils import hash_token, victim_pseudonym
from nyaya_shared.state_codes import STATE_CODES
from nyaya_shared.taxonomy import (
    BENCHMARKS,
    EVENT_CATEGORY_MAP,
    STAGE_DEFINITIONS,
    VALID_EVENT_TYPES,
)

__all__ = [
    # Models
    "RawArticle",
    "RedactionEntry",
    "SanitizedArticle",
    "ExtractedEvent",
    "ExtractedCase",
    "TimelineStage",
    "TimelineGap",
    "Timeline",
    # Taxonomy
    "VALID_EVENT_TYPES",
    "EVENT_CATEGORY_MAP",
    "STAGE_DEFINITIONS",
    "BENCHMARKS",
    # Kafka schemas
    "TOPIC_RAW_ARTICLES",
    "TOPIC_SANITIZED_ARTICLES",
    "TOPIC_EXTRACTED_EVENTS",
    "TOPIC_RESOLVED_EVENTS",
    "TOPIC_LOW_CONFIDENCE",
    "TOPIC_TIMELINE_UPDATES",
    "CONSUMER_GROUP_PRIVACY_ENGINE",
    "CONSUMER_GROUP_AI_EXTRACTOR",
    "CONSUMER_GROUP_ENTITY_RESOLVER",
    "CONSUMER_GROUP_PERSISTENCE_WORKER",
    "CONSUMER_GROUP_TIMELINE_ENGINE",
    # Privacy utilities
    "victim_pseudonym",
    "hash_token",
    # State codes
    "STATE_CODES",
]
