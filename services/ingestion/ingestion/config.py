"""Settings for the ingestion service, loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Kafka ─────────────────────────────────────────────────────────────────
    kafka_brokers: str = "localhost:9092"
    kafka_topic_raw_articles: str = "nyaya.raw_articles"
    # Producer linger and batch settings for throughput
    kafka_linger_ms: int = 50
    kafka_batch_size: int = 65536

    # ── MinIO / S3 ────────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_raw: str = "nyaya-raw"
    minio_use_ssl: bool = False

    # ── Database (for eCourts tracked cases) ─────────────────────────────────
    database_url: str = "postgresql://nyaya:nyaya@localhost:5432/nyaya"

    # ── eCourts API ───────────────────────────────────────────────────────────
    ecourts_api_base_url: str = "https://apis.ecourts.gov.in/api/v1"
    ecourts_api_key: str = ""

    # ── NCRB ─────────────────────────────────────────────────────────────────
    ncrb_report_index_url: str = "https://ncrb.gov.in/crime-in-india-table-addtional-table-and-chapter"

    # ── MinIO RTI bucket (uploaded PDFs) ─────────────────────────────────────
    minio_bucket_rti: str = "nyaya-rti-uploads"

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── Prometheus metrics port ───────────────────────────────────────────────
    prometheus_port: int = 8002


settings = Settings()  # type: ignore[call-arg]
