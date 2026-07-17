"""Event processing service — manages pipeline lifecycle and consumer orchestration."""

from __future__ import annotations

import logging
import time

from app.features.event_streaming.engine.event_bus import EventBus, EventBusEvent
from app.features.event_streaming.engine.pipeline import PipelineContext, StreamingPipeline
from app.features.event_streaming.models.consumer_offset import ConsumerOffset
from app.features.event_streaming.models.dead_letter import DeadLetterEvent
from app.features.event_streaming.models.event_type import ConsumerStatus
from app.features.event_streaming.repositories.consumer_offset_repository import (
    ConsumerOffsetRepository,
)
from app.features.event_streaming.repositories.dead_letter_repository import DeadLetterRepository
from app.shared.result import Result, Success

logger = logging.getLogger(__name__)


class ProcessingService:
    """Orchestrates event processing: pipeline management, consumer health, and DLQ handling.

    Monitors consumer health, tracks processing offsets, and manages dead letter events.
    """

    def __init__(
        self,
        pipeline: StreamingPipeline,
        event_bus: EventBus,
        consumer_offset_repo: ConsumerOffsetRepository,
        dead_letter_repo: DeadLetterRepository,
    ) -> None:
        self._pipeline = pipeline
        self._event_bus = event_bus
        self._consumer_offset_repo = consumer_offset_repo
        self._dead_letter_repo = dead_letter_repo
        self._start_time = time.monotonic()

    async def process_event(self, ctx: PipelineContext) -> PipelineContext:
        """Process a single event through the pipeline."""
        return await self._pipeline.process(ctx)

    async def process_batch(self, contexts: list[PipelineContext]) -> list[PipelineContext]:
        """Process a batch of events through the pipeline."""
        return await self._pipeline.process_batch(contexts)

    async def update_consumer_offset(
        self,
        consumer_id: str,
        event_id: str,
        processing_ms: float,
        success: bool,
    ) -> Result[ConsumerOffset]:
        """Update a consumer's processing offset after handling an event."""
        existing = await self._consumer_offset_repo.get_by_consumer_id(consumer_id)

        if isinstance(existing, Success) and existing.value is not None:
            offset = existing.value
            offset.last_processed_event_id = event_id
            offset.last_processed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            offset.events_processed += 1 if success else 0
            offset.events_failed += 0 if success else 1

            total = offset.events_processed + offset.events_failed
            if total > 0:
                offset.avg_processing_ms = (
                    (offset.avg_processing_ms * (total - 1) + processing_ms) / total
                )
        else:
            offset = ConsumerOffset(
                consumer_id=consumer_id,
                last_processed_event_id=event_id,
                last_processed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                events_processed=1 if success else 0,
                events_failed=0 if success else 1,
                avg_processing_ms=processing_ms,
                status=ConsumerStatus.HEALTHY,
            )

        await self._consumer_offset_repo.upsert(offset)
        return Success(offset)

    async def send_to_dead_letter(
        self,
        event: EventBusEvent,
        error_type: str,
        error_message: str,
        retry_count: int,
    ) -> Result[DeadLetterEvent]:
        """Move a failed event to the dead letter queue."""
        dlq_event = DeadLetterEvent(
            original_event_id=event.event_id,
            original_payload=event.payload,
            error_type=error_type,
            error_message=error_message,
            retry_count=retry_count,
            last_retry_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        return await self._dead_letter_repo.append(dlq_event)

    async def get_stream_status(self) -> dict:
        """Get current streaming platform status."""
        pipeline_stats = self._pipeline.stats
        bus_stats = self._event_bus.stats
        dlq_count = await self._dead_letter_repo.count_unresolved()

        return {
            "pipeline_stats": {
                "total_processed": pipeline_stats.total_processed,
                "total_succeeded": pipeline_stats.total_succeeded,
                "total_failed": pipeline_stats.total_failed,
                "total_dead_lettered": pipeline_stats.total_dead_lettered,
                "avg_latency_ms": round(pipeline_stats.avg_latency_ms, 2),
            },
            "bus_stats": bus_stats,
            "dead_letter_count": dlq_count.value if isinstance(dlq_count, Success) else 0,
            "uptime_seconds": round(time.monotonic() - self._start_time, 1),
        }

    @property
    def pipeline(self) -> StreamingPipeline:
        return self._pipeline

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus
