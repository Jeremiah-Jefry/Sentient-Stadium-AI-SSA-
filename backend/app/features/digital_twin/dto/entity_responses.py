"""Entity response DTOs for single entity, lists, and paginated results."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityComponentResponse(BaseModel):
    """A component attached to an entity."""

    component_type: str
    component_data: dict


class EntityResponse(BaseModel):
    """Complete entity representation returned by the API."""

    id: str
    name: str
    description: str | None
    entity_type: str
    operational_status: str
    current_health: str
    current_capacity: int
    max_capacity: int
    coordinates_lat: float
    coordinates_lon: float
    indoor_x: float | None
    indoor_y: float | None
    floor_number: int | None
    building_level: int | None
    accessibility_level: str
    accessibility_metadata: dict | None
    current_state: dict | None
    metadata_json: dict | None
    venue_id: str
    zone_id: str | None
    parent_id: str | None
    components: list[EntityComponentResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str


class EntitySummaryResponse(BaseModel):
    """Lightweight entity representation for lists and search results."""

    id: str
    name: str
    entity_type: str
    operational_status: str
    current_health: str
    current_capacity: int
    max_capacity: int
    coordinates_lat: float
    coordinates_lon: float
    zone_id: str | None


class PaginatedEntityResponse(BaseModel):
    """Paginated list of entities."""

    items: list[EntitySummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EntityTimelineResponse(BaseModel):
    """Entity version history for audit and timeline."""

    versions: list[EntityVersionResponse]
    entity_id: str


class EntityVersionResponse(BaseModel):
    """A single version snapshot of an entity."""

    id: str
    version: int
    state_snapshot: dict
    changed_by: str | None
    change_reason: str | None
    created_at: str


class EntityEventResponse(BaseModel):
    """An event record for entity state change."""

    id: str
    entity_id: str
    event_type: str
    event_data: dict | None
    source: str
    created_at: str


class EntityListResponse(BaseModel):
    """List of entity events."""

    events: list[EntityEventResponse]
    total: int


class BulkUpdateResponse(BaseModel):
    """Response for bulk state update operation."""

    updated_count: int
    failed_ids: list[str] = Field(default_factory=list)
