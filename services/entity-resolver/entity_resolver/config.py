"""Configuration for the entity-resolver service."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Kafka
    kafka_brokers: str = "localhost:9092"
    topic_extracted_events: str = "nyaya.extracted_events"
    topic_resolved_events: str = "nyaya.resolved_events"
    consumer_group: str = "entity-resolver"

    # Database
    database_url: str = "postgresql+asyncpg://nyaya:nyaya@localhost:5432/nyaya"

    # AI / Embeddings
    anthropic_api_key: str = ""
    dedup_model: str = "claude-haiku-4-5-20251001"
    embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )

    # Threshold configuration
    auto_merge_threshold: float = 0.92
    llm_verify_upper: float = 0.92
    llm_verify_lower: float = 0.78
    moderation_lower: float = 0.70

    # Privacy
    privacy_salt: str = ""


settings = Settings()
