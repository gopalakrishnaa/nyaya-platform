from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    kafka_brokers: str = "localhost:9092"
    kafka_topic_resolved: str = "nyaya.resolved_events"
    kafka_topic_timeline: str = "nyaya.timeline_updates"
    consumer_group: str = "timeline-engine"

    database_url: str = "postgresql+asyncpg://nyaya:nyaya@localhost:5432/nyaya"

    log_level: str = "INFO"
    prometheus_port: int = 8004


settings = Settings()  # type: ignore[call-arg]
