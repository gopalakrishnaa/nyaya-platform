"""
Alembic environment configuration for the Nyaya platform.

Supports both offline (SQL generation) and online (live DB) migration modes.
Uses asyncpg driver for async PostgreSQL connections.
"""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to the .ini file values
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Override sqlalchemy.url from environment variable if present.
# This is the recommended approach for CI/CD and container deployments.
# ---------------------------------------------------------------------------
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Ensure we use the asyncpg driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    config.set_main_option("sqlalchemy.url", database_url)

# ---------------------------------------------------------------------------
# MetaData for autogenerate support.
# Import all SQLAlchemy models here so Alembic can detect schema changes.
# ---------------------------------------------------------------------------
# When the ORM layer is added under services/, import the Base metadata here:
#   from nyaya_api.db.models import Base
#   target_metadata = Base.metadata
#
# For now we use None — migrations are driven by explicit SQL in revision files.
target_metadata = None


# ---------------------------------------------------------------------------
# Helper: strip asyncpg for sync connections used in offline mode
# ---------------------------------------------------------------------------
def _make_sync_url(url: str) -> str:
    """Replace asyncpg driver with psycopg2 for synchronous offline mode."""
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


# ---------------------------------------------------------------------------
# OFFLINE MODE — generates SQL script without connecting to the DB
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url", "")
    # Offline mode needs a synchronous driver
    sync_url = _make_sync_url(url)

    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# ONLINE MODE — connects to the DB and runs migrations
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Include schema in migration commands
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    In 'online' mode, create an async engine and run migrations
    inside a coroutine so that asyncio-aware connection pools are used.
    """
    configuration = config.get_section(config.config_ini_section, {})

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using asyncio event loop."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
