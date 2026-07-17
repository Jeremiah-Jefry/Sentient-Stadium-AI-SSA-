"""Event request DTOs for ingestion, queries, replay, and sensor management."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.features.event_streaming.models.event_type import (
    EventCategory,
    EventPriority,
    EventSeverity,
    SensorType,
)

MAX_PAYLOAD_SIZE_BYTES = 65536


class IngestEventRequest(BaseModel):
    """Request to ingest a single event into the streaming platform."""

    event_id: str = Field(..., min_length=1, max_length=64)
    event_type: str = Field(..., min_length=1, max_length=100)
    category: EventCategory
    priority: EventPriority = EventPriority.NORMAL
    severity: EventSeverity = EventSeverity.INFO
    source: str = Field(..., min_length=1, max_length=200)
    producer: str = Field(..., min_length=1, max_length=100)
    version: int = Field(1, ge=1, le=100)
    entity_id: str | None = None
    venue_id: str | None = None
    zone_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    parent_event_id: str | None = None
    payload: dict = Field(..., min_length=1)
    metadata_json: dict | None = None
    captured_at: str = Field(..., description="ISO 8601 timestamp")
    ttl_seconds: int | None = Field(None, ge=1, le=86400)


class BatchIngestRequest(BaseModel):
    """Request to ingest multiple events atomically."""

    events: list[IngestEventRequest] = Field(..., min_length=1, max_length=1000)


class QueryEventsRequest(BaseModel):
    """Request to query events from the event store."""

    venue_id: str | None = None
    entity_id: str | None = None
    category: EventCategory | None = None
    event_type: str | None = Field(None, max_length=100)
    severity_min: EventSeverity | None = None
    since: str | None = Field(None, description="ISO 8601 start timestamp")
    until: str | None = Field(None, description="ISO 8601 end timestamp")
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)


class ReplayRequest(BaseModel):
    """Request to replay historical events through the processing pipeline."""

    venue_id: str | None = None
    entity_id: str | None = None
    category: EventCategory | None = None
    from_timestamp: str = Field(..., description="ISO 8601 start of replay window")
    to_timestamp: str = Field(..., description="ISO 8601 end of replay window")
    speed_multiplier: float = Field(1.0, ge=0.1, le=100.0)
    target_consumers: list[str] = Field(default_factory=list)


class RegisterSensorRequest(BaseModel):
    """Request to register a new sensor in the registry."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    sensor_type: SensorType
    venue_id: str
    entity_id: str | None = None
    zone_id: str | None = None
    coordinates_lat: float = Field(..., ge=-90.0, le=90.0)
    coordinates_lon: float = Field(..., ge=-180.0, le=180.0)
    indoor_x: float | None = Field(None, ge=0)
    indoor_y: float | None = Field(None, ge=0)
    floor_number: int | None = Field(None, ge=0)
    reading_interval_ms: int = Field(1000, ge=100, le=60000)
    accuracy: float | None = Field(None, gt=0, le=1.0)
    range_meters: float | None = Field(None, gt=0)
    firmware_version: str | None = Field(None, max_length=50)
    metadata_json: dict | None = None


class UpdateSensorRequest(BaseModel):
    """Request to update sensor metadata. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    is_active: bool | None = None
    is_calibrated: bool | None = None
    reading_interval_ms: int | None = Field(None, ge=100, le=60000)
    accuracy: float | None = Field(None, gt=0, le=1.0)
    range_meters: float | None = Field(None, gt=0)
    firmware_version: str | None = Field(None, max_length=50)
    metadata_json: dict | None = None
