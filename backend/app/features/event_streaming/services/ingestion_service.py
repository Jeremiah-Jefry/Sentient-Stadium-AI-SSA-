"""Event ingestion service — validates and persists incoming events."""

from __future__ import annotations

import hashlib
import uuid

from app.features.event_streaming.dto.event_requests import (
    BatchIngestRequest,
    IngestEventRequest,
)
from app.features.event_streaming.dto.event_responses import BatchIngestResponse
from app.features.event_streaming.engine.event_bus import EventBus
from app.features.event_streaming.engine.pipeline import PipelineContext, StreamingPipeline
from app.features.event_streaming.models.event import StoredEvent
from app.features.event_streaming.models.event_type import ProcessingStatus
from app.features.event_streaming.repositories.event_store_repository import EventStoreRepository
from app.shared.result import Failure, Result, Success


class IngestionService:
    """Handles event ingestion: validation, persistence, dedup, and pipeline dispatch.

    Every incoming event is validated, checked for duplicates, persisted to the
    event store, and dispatched to the streaming pipeline for processing.
    """

    def __init__(
        self,
        event_store: EventStoreRepository,
        pipeline: StreamingPipeline,
        event_bus: EventBus,
    ) -> None:
        self._event_store = event_store
        self._pipeline = pipeline
        self._event_bus = event_bus
        self._total_ingested = 0
        self._total_rejected = 0

    async def ingest(self, req: IngestEventRequest) -> Result[StoredEvent]:
        """Ingest a single event into the platform."""
        dup_check = await self._event_store.exists(req.event_id)
        if isinstance(dup_check, Success) and dup_check.value:
            self._total_rejected += 1
            return Failure(
                error_code="EVENT_DUPLICATE",
                message=f"Event '{req.event_id}' already exists",
            )

        entity_uuid = uuid.UUID(req.entity_id) if req.entity_id else None
        venue_uuid = uuid.UUID(req.venue_id) if req.venue_id else None
        zone_uuid = uuid.UUID(req.zone_id) if req.zone_id else None

        stored_event = StoredEvent(
            event_id=req.event_id,
            correlation_id=req.correlation_id,
            trace_id=req.trace_id,
            parent_event_id=req.parent_event_id,
            event_type=req.event_type,
            category=req.category,
            priority=req.priority,
            severity=req.severity,
            source=req.source,
            producer=req.producer,
            version=req.version,
            entity_id=entity_uuid,
            venue_id=venue_uuid,
            zone_id=zone_uuid,
            payload=req.payload,
            metadata_json=req.metadata_json,
            captured_at=req.captured_at,
            processing_status=ProcessingStatus.RECEIVED,
            retry_count=0,
            max_retries=3,
            ttl_seconds=req.ttl_seconds,
            checksum=self._compute_checksum(req.payload),
        )

        append_result = await self._event_store.append(stored_event)
        if not isinstance(append_result, Success):
            self._total_rejected += 1
            return Failure(error_code="STORE_FAILED", message="Failed to persist event")

        ctx = PipelineContext(
            event_id=req.event_id,
            event_type=req.event_type,
            category=req.category.value,
            payload=req.payload,
            venue_id=req.venue_id,
            entity_id=req.entity_id,
            zone_id=req.zone_id,
            priority=req.priority.value,
            severity=req.severity.value,
            producer=req.producer,
            captured_at=req.captured_at,
            metadata={"original_fields": list(req.payload.keys())},
        )

        await self._pipeline.process(ctx)
        self._total_ingested += 1
        return Success(stored_event)

    async def ingest_batch(self, req: BatchIngestRequest) -> Result[BatchIngestResponse]:
        """Ingest multiple events atomically."""
        accepted = 0
        rejected = 0
        event_ids: list[str] = []
        errors: list[dict] = []

        for event_req in req.events:
            result = await self.ingest(event_req)
            if isinstance(result, Success):
                accepted += 1
                event_ids.append(event_req.event_id)
            else:
                rejected += 1
                errors.append({
                    "event_id": event_req.event_id,
                    "error_code": result.error_code,
                    "message": result.message,
                })

        return Success(BatchIngestResponse(
            accepted=accepted,
            rejected=rejected,
            event_ids=event_ids,
            errors=errors,
        ))

    @staticmethod
    def _compute_checksum(payload: dict) -> str:
        """Compute SHA-256 checksum of the payload for integrity verification."""
        import json
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    @property
    def stats(self) -> dict:
        return {
            "total_ingested": self._total_ingested,
            "total_rejected": self._total_rejected,
        }
