"""Event response DTOs for API responses, streaming status, and sensor data."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StoredEventResponse(BaseModel):
    """Complete event representation returned by the API."""

    id: str
    event_id: str
    correlation_id: str | None
    trace_id: str | None
    parent_event_id: str | None
    event_type: str
    category: str
    priority: str
    severity: str
    source: str
    producer: str
    version: int
    entity_id: str | None
    venue_id: str | None
    zone_id: str | None
    payload: dict
    metadata_json: dict | None
    captured_at: str
    processing_status: str
    retry_count: int
    processing_duration_ms: float | None
    created_at: str


class EventSummaryResponse(BaseModel):
    """Lightweight event representation for lists."""

    id: str
    event_id: str
    event_type: str
    category: str
    severity: str
    producer: str
    entity_id: str | None
    captured_at: str
    processing_status: str


class PaginatedEventResponse(BaseModel):
    """Paginated list of events."""

    items: list[EventSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BatchIngestResponse(BaseModel):
    """Response for batch event ingestion."""

    accepted: int
    rejected: int
    event_ids: list[str] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)


class StreamStatusResponse(BaseModel):
    """Current status of the event streaming platform."""

    total_events_stored: int
    events_per_second: float
    avg_processing_latency_ms: float
    active_consumers: int
    dead_letter_count: int
    pipeline_healthy: bool
    uptime_seconds: float


class SensorResponse(BaseModel):
    """Complete sensor representation returned by the API."""

    id: str
    name: str
    description: str | None
    sensor_type: str
    venue_id: str
    entity_id: str | None
    zone_id: str | None
    coordinates_lat: float
    coordinates_lon: float
    indoor_x: float | None
    indoor_y: float | None
    floor_number: int | None
    is_active: bool
    is_calibrated: bool
    last_calibration_at: str | None
    reading_interval_ms: int
    accuracy: float | None
    range_meters: float | None
    firmware_version: str | None
    metadata_json: dict | None
    created_at: str
    updated_at: str


class SensorHealthResponse(BaseModel):
    """Aggregated sensor health for a venue."""

    total_sensors: int
    active_sensors: int
    inactive_sensors: int
    calibrated_sensors: int
    by_type: dict[str, dict[str, int]]


class DeadLetterResponse(BaseModel):
    """Dead letter event representation."""

    id: str
    original_event_id: str
    original_payload: dict
    error_type: str
    error_message: str
    retry_count: int
    is_resolved: bool
    created_at: str


class AggregationResponse(BaseModel):
    """Windowed aggregation result."""

    id: str
    venue_id: str
    zone_id: str | None
    window_type: str
    window_start: str
    window_end: str
    event_count: int
    events_by_category: dict
    events_by_severity: dict
    peak_crowd_density: float | None
    avg_response_time_ms: float | None
    anomalies_detected: int
    alerts_triggered: int


class SnapshotResponse(BaseModel):
    """Event snapshot representation."""

    id: str
    venue_id: str
    captured_at: str
    interval_type: str
    total_events: int
    events_by_category: dict
    events_by_severity: dict
    active_sensors: int
    failed_sensors: int
    state_summary: dict
