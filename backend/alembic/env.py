"""Alembic environment configuration for async SQLAlchemy migrations."""

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Add the backend directory to sys.path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.shared.models.base import Base  # noqa: E402
from app.features.auth.models import *  # noqa: F401, E402 - Import all models for Alembic discovery

# Digital Twin models
from app.features.digital_twin.models.entity import *  # noqa: F401, E402
from app.features.digital_twin.models.entity_type import *  # noqa: F401, E402
from app.features.digital_twin.models.entity_state import *  # noqa: F401, E402
from app.features.digital_twin.models.entity_component import *  # noqa: F401, E402
from app.features.digital_twin.models.entity_event import *  # noqa: F401, E402
from app.features.digital_twin.models.entity_version import *  # noqa: F401, E402
from app.features.digital_twin.models.venue import *  # noqa: F401, E402
from app.features.digital_twin.models.zone import *  # noqa: F401, E402
from app.features.digital_twin.models.edge import *  # noqa: F401, E402

# Event Streaming models
from app.features.event_streaming.models.event import *  # noqa: F401, E402
from app.features.event_streaming.models.event_type import *  # noqa: F401, E402
from app.features.event_streaming.models.sensor import *  # noqa: F401, E402
from app.features.event_streaming.models.aggregation import *  # noqa: F401, E402
from app.features.event_streaming.models.consumer_offset import *  # noqa: F401, E402
from app.features.event_streaming.models.dead_letter import *  # noqa: F401, E402
from app.features.event_streaming.models.event_snapshot import *  # noqa: F401, E402

# AI Intelligence models
from app.features.ai_intelligence.models.prediction import *  # noqa: F401, E402
from app.features.ai_intelligence.models.risk_history import *  # noqa: F401, E402
from app.features.ai_intelligence.models.confidence_record import *  # noqa: F401, E402
from app.features.ai_intelligence.models.decision import *  # noqa: F401, E402
from app.features.ai_intelligence.models.intervention import *  # noqa: F401, E402
from app.features.ai_intelligence.models.historical_outcome import *  # noqa: F401, E402
from app.features.ai_intelligence.models.model_metadata import *  # noqa: F401, E402

# Navigation models
from app.features.navigation.models.database import *  # noqa: F401, E402

# Orchestration models
from app.features.orchestration.models.database import *  # noqa: F401, E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from environment if available
db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode - generates SQL without connecting."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with an existing connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    from sqlalchemy.ext.asyncio import create_async_engine

    url = config.get_main_option("sqlalchemy.url")
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode - connects to the database."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
