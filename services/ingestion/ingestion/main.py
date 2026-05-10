from __future__ import annotations

import logging
import os

import boto3
import structlog
from confluent_kafka import Producer

from .adapters.ani_adapter import ANIAdapter
from .adapters.ananda_bazar_adapter import AnandaBazarAdapter
from .adapters.dainik_bhaskar_adapter import DainikBhaskarAdapter
from .adapters.ecourts_adapter import ECourtsAdapter
from .adapters.mathrubhumi_adapter import MathrubhumiAdapter
from .adapters.ncrb_adapter import NCRBAdapter
from .adapters.pti_adapter import PTIAdapter
from .adapters.rti_adapter import RTIAdapter
from .config import settings
from .scheduler import create_scheduler

logger = structlog.get_logger()


def configure_logging() -> None:
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


def main() -> None:
    configure_logging()

    producer = Producer(
        {
            "bootstrap.servers": settings.kafka_brokers,
            "enable.idempotence": True,
        }
    )

    s3 = boto3.client(
        "s3",
        endpoint_url=f"http{'s' if settings.minio_use_ssl else ''}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    )
    bucket = settings.minio_bucket_raw

    adapter_kwargs = {"producer": producer, "s3_client": s3, "bucket": bucket}

    adapters = {
        "ani": ANIAdapter(**adapter_kwargs),
        "pti": PTIAdapter(**adapter_kwargs),
        "ncrb": NCRBAdapter(**adapter_kwargs),
        "ecourts": ECourtsAdapter(**adapter_kwargs),
        "rti": RTIAdapter(**adapter_kwargs),
        "dainik_bhaskar": DainikBhaskarAdapter(**adapter_kwargs),
        "mathrubhumi": MathrubhumiAdapter(**adapter_kwargs),
        "ananda_bazar": AnandaBazarAdapter(**adapter_kwargs),
    }

    scheduler = create_scheduler(adapters)
    logger.info("ingestion_scheduler_starting", adapters=list(adapters.keys()))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("ingestion_scheduler_stopped")
        scheduler.shutdown()
        for adapter in adapters.values():
            adapter.close()
        producer.flush()


if __name__ == "__main__":
    main()
