"""Event API routes — ingestion, query, and batch operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.features.event_streaming.api.deps import (
    get_dead_letter_repo,
    get_event_store_repo,
    get_ingestion_service,
)
from app.features.event_streaming.dto.event_requests import (
    BatchIngestRequest,
    IngestEventRequest,
)
from app.features.event_streaming.dto.event_responses import (
    BatchIngestResponse,
    DeadLetterResponse,
    PaginatedEventResponse,
    StoredEventResponse,
)
from app.features.event_streaming.repositories.dead_letter_repository import DeadLetterRepository
from app.features.event_streaming.repositories.event_store_repository import EventStoreRepository
from app.features.event_streaming.services.ingestion_service import IngestionService
from app.shared.result import Success

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/ingest", response_model=StoredEventResponse, status_code=status.HTTP_201_CREATED)
async def ingest_event(
    req: IngestEventRequest,
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> StoredEventResponse:
    """Ingest a single event into the streaming platform."""
    result = await ingestion.ingest(req)
    if not isinstance(result, Success):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result.message)
    e = result.value
    return StoredEventResponse(
        id=str(e.id), event_id=e.event_id, correlation_id=e.correlation_id,
        trace_id=e.trace_id, parent_event_id=e.parent_event_id,
        event_type=e.event_type, category=e.category, priority=e.priority,
        severity=e.severity, source=e.source, producer=e.producer, version=e.version,
        entity_id=str(e.entity_id) if e.entity_id else None,
        venue_id=str(e.venue_id) if e.venue_id else None,
        zone_id=str(e.zone_id) if e.zone_id else None,
        payload=e.payload, metadata_json=e.metadata_json,
        captured_at=e.captured_at, processing_status=e.processing_status,
        retry_count=e.retry_count, processing_duration_ms=e.processing_duration_ms,
        created_at=str(e.created_at),
    )


@router.post(
    "/ingest/batch",
    response_model=BatchIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_batch(
    req: BatchIngestRequest,
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> BatchIngestResponse:
    """Ingest multiple events atomically."""
    result = await ingestion.ingest_batch(req)
    if not isinstance(result, Success):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result.message)
    return result.value


@router.get("/query", response_model=PaginatedEventResponse)
async def query_events(
    venue_id: str | None = Query(None),
    entity_id: str | None = Query(None),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    event_store: EventStoreRepository = Depends(get_event_store_repo),
) -> PaginatedEventResponse:
    """Query events from the event store with filters."""
    import uuid as _uuid
    venue_uuid = _uuid.UUID(venue_id) if venue_id else None
    entity_uuid = _uuid.UUID(entity_id) if entity_id else None

    result = await event_store.query_events(
        venue_id=venue_uuid,
        entity_id=entity_uuid,
        category=category,
        page=page,
        page_size=page_size,
    )
    if not isinstance(result, Success):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Query failed")

    events, total = result.value
    total_pages = (total + page_size - 1) // page_size

    items = [
        {
            "id": str(e.id), "event_id": e.event_id,
            "event_type": e.event_type, "category": e.category,
            "severity": e.severity, "producer": e.producer,
            "entity_id": str(e.entity_id) if e.entity_id else None,
            "captured_at": e.captured_at,
            "processing_status": e.processing_status,
        }
        for e in events
    ]
    return PaginatedEventResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@router.get("/dead-letter", response_model=list[DeadLetterResponse])
async def get_dead_letters(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    dlq_repo: DeadLetterRepository = Depends(get_dead_letter_repo),
) -> list[DeadLetterResponse]:
    """Fetch unresolved dead letter events."""
    result = await dlq_repo.get_unresolved(page=page, page_size=page_size)
    if not isinstance(result, Success):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Failed to fetch dead letters")
    return [
        DeadLetterResponse(
            id=str(e.id), original_event_id=e.original_event_id,
            original_payload=e.original_payload, error_type=e.error_type,
            error_message=e.error_message, retry_count=e.retry_count,
            is_resolved=e.is_resolved, created_at=str(e.created_at),
        )
        for e in result.value
    ]
