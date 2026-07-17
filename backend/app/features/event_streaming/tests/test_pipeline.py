"""Tests for the streaming pipeline and its stages."""

from __future__ import annotations

import pytest

from app.features.event_streaming.engine.event_bus import EventBus, EventBusEvent
from app.features.event_streaming.engine.pipeline import (
    PipelineContext,
    StreamingPipeline,
)
from app.features.event_streaming.engine.stages import (
    DeduplicationStage,
    EnrichmentStage,
    NormalizationStage,
    ValidationStage,
)
from app.features.event_streaming.models.event_type import ProcessingStatus


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def pipeline(bus: EventBus) -> StreamingPipeline:
    return StreamingPipeline(event_bus=bus, max_retries=0)


def _valid_context(**overrides: object) -> PipelineContext:
    defaults = {
        "event_id": "evt-001",
        "event_type": "crowd_density_update",
        "category": "crowd",
        "payload": {"crowd_density": 5000, "source": "test"},
        "venue_id": "venue-1",
        "captured_at": "2026-07-15T20:00:00Z",
        "producer": "test",
        "metadata": {"original_fields": list({"crowd_density", "source"})},
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)  # type: ignore[arg-type]


class TestValidationStage:
    @pytest.mark.asyncio
    async def test_valid_event_passes(self) -> None:
        stage = ValidationStage()
        ctx = _valid_context()
        result = await stage.process(ctx)
        assert result.status == ProcessingStatus.RECEIVED

    @pytest.mark.asyncio
    async def test_missing_event_id_fails(self) -> None:
        stage = ValidationStage()
        ctx = _valid_context(event_id="")
        result = await stage.process(ctx)
        assert result.status == ProcessingStatus.FAILED


class TestDeduplicationStage:
    @pytest.mark.asyncio
    async def test_first_event_passes(self) -> None:
        stage = DeduplicationStage()
        ctx = _valid_context()
        result = await stage.process(ctx)
        assert result.status == ProcessingStatus.DEDUPLICATING

    @pytest.mark.asyncio
    async def test_duplicate_event_rejected(self) -> None:
        stage = DeduplicationStage()
        ctx1 = _valid_context()
        await stage.process(ctx1)
        ctx2 = _valid_context()
        result = await stage.process(ctx2)
        assert result.status == ProcessingStatus.FAILED
        assert "Duplicate" in result.errors[0]


class TestNormalizationStage:
    @pytest.mark.asyncio
    async def test_strips_whitespace(self) -> None:
        stage = NormalizationStage()
        ctx = _valid_context(category="  Crowd  ")
        result = await stage.process(ctx)
        assert result.category == "crowd"

    @pytest.mark.asyncio
    async def test_computes_checksum(self) -> None:
        stage = NormalizationStage()
        ctx = _valid_context()
        result = await stage.process(ctx)
        assert "checksum" in result.metadata


class TestEnrichmentStage:
    @pytest.mark.asyncio
    async def test_adds_metadata(self) -> None:
        stage = EnrichmentStage()
        ctx = _valid_context()
        result = await stage.process(ctx)
        assert result.metadata.get("enrichment_complete") is True
        assert result.metadata.get("pipeline_version") == "1.0"


class TestStreamingPipeline:
    @pytest.mark.asyncio
    async def test_process_valid_event(self, pipeline: StreamingPipeline) -> None:
        ctx = _valid_context()
        result = await pipeline.process(ctx)
        assert result.status == ProcessingStatus.PROCESSED

    @pytest.mark.asyncio
    async def test_process_invalid_event(self, pipeline: StreamingPipeline) -> None:
        ctx = _valid_context(event_id="")
        result = await pipeline.process(ctx)
        assert result.status == ProcessingStatus.FAILED

    @pytest.mark.asyncio
    async def test_process_batch(self, pipeline: StreamingPipeline) -> None:
        contexts = [_valid_context(event_id=f"evt-{i}") for i in range(3)]
        results = await pipeline.process_batch(contexts)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_stats_tracking(self, pipeline: StreamingPipeline) -> None:
        ctx = _valid_context()
        await pipeline.process(ctx)
        assert pipeline.stats.total_processed == 1
        assert pipeline.stats.total_succeeded == 1

    @pytest.mark.asyncio
    async def test_context_from_event(self) -> None:
        event = EventBusEvent(
            event_id="e1", category="crowd", event_type="test",
            payload={}, venue_id="v1", producer="test",
        )
        ctx = StreamingPipeline.context_from_event(event)
        assert ctx.event_id == "e1"
        assert ctx.venue_id == "v1"
