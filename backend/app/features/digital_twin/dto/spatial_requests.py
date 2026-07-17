"""Spatial query request DTOs for nearby search and pathfinding."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.features.digital_twin.models.entity_state import AccessibilityLevel
from app.features.digital_twin.models.entity_type import EntityType


class NearbySearchRequest(BaseModel):
    """Request to find entities near a geographic point."""

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_meters: float = Field(500.0, gt=0, le=10000)
    entity_type: EntityType | None = None
    limit: int = Field(20, ge=1, le=100)


class PathfindingRequest(BaseModel):
    """Request to find the shortest path between two entities."""

    from_entity_id: str
    to_entity_id: str
    accessibility_level: AccessibilityLevel | None = Field(
        None, description="Filter path by accessibility (full, partial, none)",
    )
    edge_type: str | None = Field(
        None, description="Filter by edge type (walking, wheelchair, emergency)",
    )


class CreateEdgeRequest(BaseModel):
    """Request to create a graph edge between two entities."""

    from_entity_id: str
    to_entity_id: str
    edge_type: str = "walking"
    weight: float = Field(1.0, gt=0)
    is_bidirectional: bool = True
    accessibility_level: str = "full"
    venue_id: str
    metadata_json: dict | None = None


class BulkCreateEdgeRequest(BaseModel):
    """Request to create multiple edges at once."""

    edges: list[CreateEdgeRequest] = Field(..., min_length=1, max_length=500)


class SpatialBoundsRequest(BaseModel):
    """Request to find entities within a bounding box."""

    lat_min: float = Field(..., ge=-90.0, le=90.0)
    lat_max: float = Field(..., ge=-90.0, le=90.0)
    lon_min: float = Field(..., ge=-180.0, le=180.0)
    lon_max: float = Field(..., ge=-180.0, le=180.0)
    entity_type: EntityType | None = None
    limit: int = Field(100, ge=1, le=1000)
