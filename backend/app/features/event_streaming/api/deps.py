"""Dependency injection for Event Streaming module."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.event_streaming.cache.cache_manager import CacheManager
from app.features.event_streaming.engine.event_bus import EventBus
from app.features.event_streaming.engine.pipeline import StreamingPipeline
from app.features.event_streaming.fusion.engine import FusionEngine
from app.features.event_streaming.repositories.aggregation_repository import AggregationRepository
from app.features.event_streaming.repositories.consumer_offset_repository import (
    ConsumerOffsetRepository,
)
from app.features.event_streaming.repositories.dead_letter_repository import DeadLetterRepository
from app.features.event_streaming.repositories.event_store_repository import EventStoreRepository
from app.features.event_streaming.repositories.sensor_repository import SensorRepository
from app.features.event_streaming.services.context_engine import ContextEngine
from app.features.event_streaming.services.ingestion_service import IngestionService
from app.features.event_streaming.services.processing_service import ProcessingService
from app.features.event_streaming.services.replay_service import ReplayService
from app.features.event_streaming.services.sensor_fusion_service import SensorFusionService
from app.shared.database import get_db_session

_event_bus = EventBus()
_cache = CacheManager()
_fusion_engine = FusionEngine()


def get_event_bus() -> EventBus:
    return _event_bus


def get_cache_manager() -> CacheManager:
    return _cache


def get_fusion_engine() -> FusionEngine:
    return _fusion_engine


async def get_event_store_repo(
    session: AsyncSession = Depends(get_db_session),
) -> EventStoreRepository:
    return EventStoreRepository(session)


async def get_sensor_repo(
    session: AsyncSession = Depends(get_db_session),
) -> SensorRepository:
    return SensorRepository(session)


async def get_dead_letter_repo(
    session: AsyncSession = Depends(get_db_session),
) -> DeadLetterRepository:
    return DeadLetterRepository(session)


async def get_consumer_offset_repo(
    session: AsyncSession = Depends(get_db_session),
) -> ConsumerOffsetRepository:
    return ConsumerOffsetRepository(session)


async def get_aggregation_repo(
    session: AsyncSession = Depends(get_db_session),
) -> AggregationRepository:
    return AggregationRepository(session)


def get_processing_service(
    event_store: EventStoreRepository,
    dead_letter_repo: DeadLetterRepository,
    consumer_offset_repo: ConsumerOffsetRepository,
) -> ProcessingService:
    return ProcessingService(
        pipeline=StreamingPipeline(event_bus=_event_bus),
        event_bus=_event_bus,
        consumer_offset_repo=consumer_offset_repo,
        dead_letter_repo=dead_letter_repo,
    )


def get_ingestion_service(
    event_store: EventStoreRepository,
    dead_letter_repo: DeadLetterRepository,
    consumer_offset_repo: ConsumerOffsetRepository,
) -> IngestionService:
    pipeline = StreamingPipeline(event_bus=_event_bus)
    return IngestionService(
        event_store=event_store,
        pipeline=pipeline,
        event_bus=_event_bus,
    )


def get_context_engine(
    sensor_repo: SensorRepository,
) -> ContextEngine:
    return ContextEngine(
        sensor_repo=sensor_repo,
        fusion_engine=_fusion_engine,
    )


def get_replay_service(
    event_store: EventStoreRepository,
) -> ReplayService:
    pipeline = StreamingPipeline(event_bus=_event_bus)
    return ReplayService(event_store=event_store, pipeline=pipeline)


def get_sensor_fusion_service(
    sensor_repo: SensorRepository,
) -> SensorFusionService:
    return SensorFusionService(
        fusion_engine=_fusion_engine,
        sensor_repo=sensor_repo,
    )
