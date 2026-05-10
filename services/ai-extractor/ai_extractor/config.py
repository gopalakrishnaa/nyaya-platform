from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    kafka_brokers: str = "localhost:9092"
    kafka_topic_sanitized: str = "nyaya.sanitized_articles"
    kafka_topic_extracted: str = "nyaya.extracted_events"
    kafka_topic_low_confidence: str = "nyaya.low_confidence_extractions"
    consumer_group: str = "ai-extractor"

    anthropic_api_key: str
    primary_model: str = "claude-sonnet-4-6"
    fallback_model: str = "claude-haiku-4-5-20251001"
    extraction_temperature: float = 0.0
    extraction_max_tokens: int = 2048

    # Confidence routing thresholds
    auto_approve_confidence: float = 0.90
    auto_approve_tier1_confidence: float = 0.75
    auto_approve_tier1_trust: float = 0.80
    human_review_threshold: float = 0.60

    log_level: str = "INFO"
    prometheus_port: int = 8002


settings = Settings()  # type: ignore[call-arg]
