"""Streaming pipeline orchestrator — chains stages and manages processing flow."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from app.features.event_streaming.engine.event_bus import EventBus, EventBusEvent
from app.features.event_streaming.engine.stages import (
    DeduplicationStage,
    EnrichmentStage,
    NormalizationStage,
    PipelineContext,
    PipelineStage,
    ValidationStage,
)
from app.features.event_streaming.models.event_type import ProcessingStatus

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_MS = 100


@dataclass(slots=True)
class PipelineStats:
    """Aggregated pipeline processing statistics."""

    total_processed: int = 0
    total_succeeded: int = 0
    total_failed: int = 0
    total_dead_lettered: int = 0
    avg_latency_ms: float = 0.0
    _latency_sum: float = 0.0

    def record(self, latency_ms: float, success: bool) -> None:
        self.total_processed += 1
        self._latency_sum += latency_ms
        self.avg_latency_ms = self._latency_sum / self.total_processed
        if success:
            self.total_succeeded += 1
        else:
            self.total_failed += 1


class StreamingPipeline:
    """Orchestrates event processing through a chain of stages.

    Events flow through validation -> deduplication -> normalization -> enrichment.
    Failed events are retried iteratively up to max_retries times before dead-lettering.
    Successfully processed events are published to the event bus for consumers.
    """

    def __init__(
        self,
        event_bus: EventBus,
        stages: list[PipelineStage] | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._event_bus = event_bus
        self._stages = stages or [
            ValidationStage(),
            DeduplicationStage(),
            NormalizationStage(),
            EnrichmentStage(),
        ]
        self._max_retries = max_retries
        self._stats = PipelineStats()

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """Process a single event through all pipeline stages with iterative retry."""
        ctx.start_time_ms = time.monotonic() * 1000

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                ctx.status = ProcessingStatus.RECEIVED
                logger.info(
                    "Retrying event %s (attempt %d/%d)",
                    ctx.event_id, attempt, self._max_retries,
                )

            stage_failed = False
            for stage in self._stages:
                try:
                    ctx = await stage.process(ctx)
                except Exception as exc:
                    logger.exception("Stage '%s' failed for event %s", stage.name, ctx.event_id)
                    ctx.errors.append(f"Stage '{stage.name}' exception: {exc}")
                    ctx.status = ProcessingStatus.FAILED
                    stage_failed = True
                    break

                if ctx.status == ProcessingStatus.FAILED:
                    logger.warning(
                        "Event %s rejected at stage '%s': %s",
                        ctx.event_id, stage.name, ctx.errors,
                    )
                    stage_failed = True
                    break

            if not stage_failed:
                ctx.status = ProcessingStatus.PROCESSED
                await self._publish_to_bus(ctx)
                break

            if attempt == self._max_retries:
                ctx.status = ProcessingStatus.DEAD_LETTERED
                self._stats.total_dead_lettered += 1
                logger.warning(
                    "Event %s dead-lettered after %d retries. Errors: %s",
                    ctx.event_id, self._max_retries, ctx.errors,
                )

        latency_ms = (time.monotonic() * 1000) - ctx.start_time_ms
        self._stats.record(latency_ms, ctx.status == ProcessingStatus.PROCESSED)
        return ctx

    async def process_batch(self, contexts: list[PipelineContext]) -> list[PipelineContext]:
        """Process multiple events through the pipeline."""
        results: list[PipelineContext] = []
        for ctx in contexts:
            result = await self.process(ctx)
            results.append(result)
        return results

    async def _publish_to_bus(self, ctx: PipelineContext) -> None:
        """Publish successfully processed event to the event bus."""
        bus_event = EventBusEvent(
            event_id=ctx.event_id,
            category=ctx.category,
            event_type=ctx.event_type,
            payload=ctx.payload,
            venue_id=ctx.venue_id,
            entity_id=ctx.entity_id,
            zone_id=ctx.zone_id,
            priority=ctx.priority,
            severity=ctx.severity,
            captured_at=ctx.captured_at,
            producer=ctx.producer,
        )
        delivered = await self._event_bus.publish(bus_event)
        ctx.metadata["bus_delivered_to"] = delivered
        logger.debug("Event %s published, delivered to %d subscribers", ctx.event_id, delivered)

    @property
    def stats(self) -> PipelineStats:
        return self._stats

    @staticmethod
    def context_from_event(event: EventBusEvent) -> PipelineContext:
        """Create a PipelineContext from a bus event."""
        return PipelineContext(
            event_id=event.event_id,
            event_type=event.event_type,
            category=event.category,
            payload=event.payload,
            venue_id=event.venue_id,
            entity_id=event.entity_id,
            zone_id=event.zone_id,
            priority=event.priority,
            severity=event.severity,
            captured_at=event.captured_at,
            producer=event.producer,
            metadata={"original_fields": list(event.payload.keys())},
        )
