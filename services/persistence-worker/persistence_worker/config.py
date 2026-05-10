from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    kafka_brokers: str = "localhost:9092"
    kafka_topic_resolved: str = "nyaya.resolved_events"
    kafka_topic_timeline: str = "nyaya.timeline_updates"
    consumer_group: str = "persistence-worker"

    database_url: str = "postgresql+asyncpg://nyaya:nyaya@localhost:5432/nyaya"

    opensearch_url: str = "http://localhost:9200"
    opensearch_username: str = ""
    opensearch_password: str = ""
    opensearch_index: str = "cases_v1"

    log_level: str = "INFO"
    prometheus_port: int = 8005


settings = Settings()  # type: ignore[call-arg]
