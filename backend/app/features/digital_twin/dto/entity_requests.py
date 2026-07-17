"""Entity request DTOs for create, update, search, and bulk operations."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.features.digital_twin.models.entity_state import (
    AccessibilityLevel,
    EntityHealth,
    OperationalStatus,
)
from app.features.digital_twin.models.entity_type import EntityType

MAX_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000


class CreateEntityRequest(BaseModel):
    """Request to create a new entity in the digital twin."""

    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    description: str | None = Field(None, max_length=MAX_DESCRIPTION_LENGTH)
    entity_type: EntityType
    venue_id: str = Field(..., description="UUID of the parent venue")
    zone_id: str | None = Field(None, description="UUID of the containing zone")
    parent_id: str | None = Field(None, description="UUID of the parent entity")
    coordinates_lat: float = Field(..., ge=-90.0, le=90.0)
    coordinates_lon: float = Field(..., ge=-180.0, le=180.0)
    indoor_x: float | None = Field(None, ge=0)
    indoor_y: float | None = Field(None, ge=0)
    floor_number: int | None = Field(None, ge=0)
    building_level: int | None = Field(None, ge=0)
    current_capacity: int = Field(0, ge=0)
    max_capacity: int = Field(0, ge=0)
    accessibility_level: AccessibilityLevel = AccessibilityLevel.FULL
    accessibility_metadata: dict | None = None
    metadata_json: dict | None = None


class UpdateEntityRequest(BaseModel):
    """Request to update an existing entity. All fields optional for partial updates."""

    name: str | None = Field(None, min_length=1, max_length=MAX_NAME_LENGTH)
    description: str | None = Field(None, max_length=MAX_DESCRIPTION_LENGTH)
    zone_id: str | None = None
    parent_id: str | None = None
    coordinates_lat: float | None = Field(None, ge=-90.0, le=90.0)
    coordinates_lon: float | None = Field(None, ge=-180.0, le=180.0)
    indoor_x: float | None = None
    indoor_y: float | None = None
    floor_number: int | None = None
    building_level: int | None = None
    operational_status: OperationalStatus | None = None
    current_health: EntityHealth | None = None
    current_capacity: int | None = Field(None, ge=0)
    max_capacity: int | None = Field(None, ge=0)
    accessibility_level: AccessibilityLevel | None = None
    accessibility_metadata: dict | None = None
    current_state: dict | None = None
    metadata_json: dict | None = None


class UpdateEntityStateRequest(BaseModel):
    """Request to update only the real-time state of an entity."""

    operational_status: OperationalStatus | None = None
    current_health: EntityHealth | None = None
    current_capacity: int | None = Field(None, ge=0)
    current_state: dict | None = None


class BulkUpdateStateRequest(BaseModel):
    """Request to update state for multiple entities at once."""

    entity_ids: list[str] = Field(..., min_length=1, max_length=100)
    operational_status: OperationalStatus | None = None
    current_health: EntityHealth | None = None
    current_capacity: int | None = Field(None, ge=0)
    current_state: dict | None = None


class SearchEntityRequest(BaseModel):
    """Request to search entities with filters."""

    entity_type: EntityType | None = None
    operational_status: OperationalStatus | None = None
    current_health: EntityHealth | None = None
    accessibility_level: AccessibilityLevel | None = None
    zone_id: str | None = None
    venue_id: str | None = None
    search: str | None = Field(None, max_length=200)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
