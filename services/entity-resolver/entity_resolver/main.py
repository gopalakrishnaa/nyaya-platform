"""Entry point for the entity-resolver service."""

from __future__ import annotations

import logging
import os

import structlog
from prometheus_client import start_http_server
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import settings
from .pipeline import EntityResolverPipeline
from .resolver import EntityResolver


def _configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )


def main() -> None:
    _configure_logging()
    logger = structlog.get_logger()

    # Optional Prometheus metrics server
    metrics_port = int(os.environ.get("METRICS_PORT", "9100"))
    start_http_server(metrics_port)
    logger.info("metrics_server_started", port=metrics_port)

    # Database session factory
    engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=10)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    resolver = EntityResolver(db_session_factory=session_factory)
    pipeline = EntityResolverPipeline(resolver=resolver)

    logger.info("entity_resolver_starting")
    pipeline.start()


if __name__ == "__main__":
    main()
