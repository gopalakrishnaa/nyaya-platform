"""Kafka topic names and consumer group IDs shared across services."""

# ── Topics ──────────────────────────────────────────────────────────────────
TOPIC_RAW_ARTICLES = "nyaya.raw_articles"
TOPIC_SANITIZED_ARTICLES = "nyaya.sanitized_articles"
TOPIC_EXTRACTED_EVENTS = "nyaya.extracted_events"
TOPIC_LOW_CONFIDENCE = "nyaya.low_confidence"
TOPIC_EXTRACTION_JOBS = "nyaya.extraction_jobs"
TOPIC_RESOLVED_EVENTS = "nyaya.resolved_events"

# ── Consumer Groups ──────────────────────────────────────────────────────────
CONSUMER_GROUP_PRIVACY_ENGINE = "privacy-engine"
CONSUMER_GROUP_AI_EXTRACTOR = "ai-extractor"
CONSUMER_GROUP_PERSISTENCE_WORKER = "persistence-worker"
CONSUMER_GROUP_TIMELINE_ENGINE = "timeline-engine"
CONSUMER_GROUP_ENTITY_RESOLVER = "entity-resolver"
