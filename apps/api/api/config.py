from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://nyaya:nyaya@localhost:5432/nyaya"
    redis_url: str = "redis://localhost:6379"
    opensearch_url: str = "http://localhost:9200"
    opensearch_username: str = ""
    opensearch_password: str = ""
    opensearch_index: str = "cases_v1"

    jwt_private_key_path: str = "/secrets/jwt_private.pem"
    jwt_public_key_path: str = "/secrets/jwt_public.pem"
    jwt_algorithm: str = "RS256"
    jwt_expire_minutes: int = 60

    api_rate_limit_public: int = 100  # per minute
    api_rate_limit_api_key: int = 1000  # per minute

    cors_origins: list[str] = ["http://localhost:3000"]

    otel_exporter_otlp_endpoint: str = ""
    log_level: str = "INFO"
    environment: Literal["development", "staging", "production"] = "development"

    privacy_salt: str = "default-dev-salt-change-in-production"


settings = Settings()  # type: ignore[call-arg]
