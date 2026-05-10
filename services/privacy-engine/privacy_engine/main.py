from __future__ import annotations

import logging

import structlog
from prometheus_client import start_http_server

from .config import settings
from .pipeline import PrivacyPipeline


def main() -> None:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
    )
    log = structlog.get_logger()
    log.info("starting_prometheus", port=settings.prometheus_port)
    start_http_server(settings.prometheus_port)

    pipeline = PrivacyPipeline()
    try:
        pipeline.run()
    except KeyboardInterrupt:
        log.info("shutdown_requested")
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
