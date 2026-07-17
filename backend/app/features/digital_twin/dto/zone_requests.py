"""Zone request DTOs for hierarchy management."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.features.digital_twin.models.entity_state import ZoneType

MAX_NAME_LENGTH = 200


class CreateZoneRequest(BaseModel):
    """Request to create a new zone in the hierarchy."""

    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    description: str | None = Field(None, max_length=2000)
    zone_type: ZoneType = ZoneType.ZONE
    venue_id: str = Field(..., description="UUID of the parent venue")
    parent_zone_id: str | None = Field(None, description="UUID of the parent zone")
    bounds_lat_min: float | None = Field(None, ge=-90.0, le=90.0)
    bounds_lat_max: float | None = Field(None, ge=-90.0, le=90.0)
    bounds_lon_min: float | None = Field(None, ge=-180.0, le=180.0)
    bounds_lon_max: float | None = Field(None, ge=-180.0, le=180.0)
    metadata_json: dict | None = None


class UpdateZoneRequest(BaseModel):
    """Request to update a zone. All fields optional for partial updates."""

    name: str | None = Field(None, min_length=1, max_length=MAX_NAME_LENGTH)
    description: str | None = None
    zone_type: ZoneType | None = None
    parent_zone_id: str | None = None
    bounds_lat_min: float | None = Field(None, ge=-90.0, le=90.0)
    bounds_lat_max: float | None = Field(None, ge=-90.0, le=90.0)
    bounds_lon_min: float | None = Field(None, ge=-180.0, le=180.0)
    bounds_lon_max: float | None = Field(None, ge=-180.0, le=180.0)
    metadata_json: dict | None = None


class CreateVenueRequest(BaseModel):
    """Request to create a new venue (stadium)."""

    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    description: str | None = Field(None, max_length=2000)
    address: str | None = Field(None, max_length=500)
    coordinates_lat: float = Field(..., ge=-90.0, le=90.0)
    coordinates_lon: float = Field(..., ge=-180.0, le=180.0)
    timezone: str = Field("UTC", max_length=50)
    metadata_json: dict | None = None
