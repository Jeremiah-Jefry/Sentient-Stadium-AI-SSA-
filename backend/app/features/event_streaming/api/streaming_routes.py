"""Streaming API routes — status, replay, and synthetic data generation."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.features.event_streaming.api.deps import (
    get_event_bus,
    get_processing_service,
    get_replay_service,
)
from app.features.event_streaming.dto.event_requests import ReplayRequest
from app.features.event_streaming.dto.event_responses import StreamStatusResponse
from app.features.event_streaming.services.processing_service import ProcessingService
from app.features.event_streaming.services.replay_service import ReplayService
from app.shared.result import Success

router = APIRouter(prefix="/streaming", tags=["Streaming"])


@router.get("/status", response_model=StreamStatusResponse)
async def get_stream_status(
    processing: ProcessingService = Depends(get_processing_service),
) -> StreamStatusResponse:
    """Get current event streaming platform status."""
    status_data = await processing.get_stream_status()
    return StreamStatusResponse(
        total_events_stored=status_data["pipeline_stats"]["total_processed"],
        events_per_second=0.0,
        avg_processing_latency_ms=status_data["pipeline_stats"]["avg_latency_ms"],
        active_consumers=status_data["bus_stats"]["active_subscribers"],
        dead_letter_count=status_data["dead_letter_count"],
        pipeline_healthy=status_data["pipeline_stats"]["total_failed"] == 0,
        uptime_seconds=status_data["uptime_seconds"],
    )


@router.post("/replay")
async def start_replay(
    req: ReplayRequest,
    replay_service: ReplayService = Depends(get_replay_service),
) -> dict:
    """Start replaying historical events through the pipeline."""
    result = await replay_service.replay(req)
    if not isinstance(result, Success):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result.message)
    return result.value


@router.post("/replay/{replay_id}/cancel")
async def cancel_replay(
    replay_id: str,
    replay_service: ReplayService = Depends(get_replay_service),
) -> dict:
    """Cancel an active replay."""
    success = replay_service.cancel_replay(replay_id)
    return {"replay_id": replay_id, "cancelled": success}


@router.get("/bus/stats")
async def get_bus_stats(
    event_bus: object = Depends(get_event_bus),
) -> dict:
    """Get event bus statistics."""
    return event_bus.stats


@router.get("/health")
async def streaming_health() -> dict:
    """Health check for the streaming platform."""
    return {"status": "healthy", "module": "event_streaming"}
