from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .middleware.audit import AuditMiddleware
from .middleware.request_id import RequestIDMiddleware
from .routers import admin, ask, cases, export, health, moderation, search, stats


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
    )


configure_logging()

app = FastAPI(
    title="Nyaya API",
    description=(
        "Justice transparency platform API — tracking crimes against women "
        "through India's legal system"
    ),
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(health.router)
app.include_router(cases.router)
app.include_router(search.router)
app.include_router(ask.router)
app.include_router(stats.router)
app.include_router(moderation.router)
app.include_router(admin.router)
app.include_router(export.router)
