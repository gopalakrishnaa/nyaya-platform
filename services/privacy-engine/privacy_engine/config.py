from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    kafka_brokers: str = "localhost:9092"
    kafka_topic_raw: str = "nyaya.raw_articles"
    kafka_topic_sanitized: str = "nyaya.sanitized_articles"
    consumer_group: str = "privacy-engine"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_raw: str = "nyaya-raw"
    minio_bucket_sanitized: str = "nyaya-sanitized"
    minio_use_ssl: bool = False

    privacy_salt: str = ""

    # NER model paths
    spacy_model_en: str = "en_core_web_lg"
    ai4bharat_model_path: str = "/models/ai4bharat-ner"

    # Confidence thresholds
    minor_suppression_threshold: float = 0.80

    log_level: str = "INFO"

    prometheus_port: int = 8001


settings = Settings()  # type: ignore[call-arg]
