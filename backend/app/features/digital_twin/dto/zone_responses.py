"""Zone and Venue response DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ZoneResponse(BaseModel):
    """Complete zone representation returned by the API."""

    id: str
    name: str
    description: str | None
    zone_type: str
    level: int
    parent_zone_id: str | None
    venue_id: str
    bounds_lat_min: float | None
    bounds_lat_max: float | None
    bounds_lon_min: float | None
    bounds_lon_max: float | None
    metadata_json: dict | None
    created_at: str
    updated_at: str


class ZoneTreeResponse(BaseModel):
    """Recursive zone tree for hierarchy visualization."""

    id: str
    name: str
    zone_type: str
    level: int
    children: list["ZoneTreeResponse"] = Field(default_factory=list)


class VenueResponse(BaseModel):
    """Complete venue representation."""

    id: str
    name: str
    description: str | None
    address: str | None
    coordinates_lat: float
    coordinates_lon: float
    timezone: str
    metadata_json: dict | None
    created_at: str
    updated_at: str


class VenueListResponse(BaseModel):
    """Paginated list of venues."""

    items: list[VenueResponse]
    total: int


class ZoneEntityCountResponse(BaseModel):
    """Zone with its entity count for capacity planning."""

    zone_id: str
    zone_name: str
    zone_type: str
    entity_count: int
    total_capacity: int
