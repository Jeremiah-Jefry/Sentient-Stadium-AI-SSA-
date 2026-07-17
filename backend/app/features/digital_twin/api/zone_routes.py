"""Zone and Venue API routes - hierarchy management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.features.digital_twin.api.deps import get_zone_service
from app.features.digital_twin.api.route_utils import unwrap_or_raise
from app.features.digital_twin.dto.zone_requests import (
    CreateVenueRequest,
    CreateZoneRequest,
    UpdateZoneRequest,
)
from app.features.digital_twin.dto.zone_responses import (
    VenueListResponse,
    VenueResponse,
    ZoneResponse,
    ZoneTreeResponse,
)
from app.features.digital_twin.services.zone_service import ZoneService

router = APIRouter(prefix="/venues", tags=["Venues & Zones"])


@router.post(
    "/", response_model=VenueResponse, status_code=201,
    summary="Create a new venue (stadium)",
)
async def create_venue(
    body: CreateVenueRequest,
    zone_service: Annotated[ZoneService, Depends(get_zone_service)],
) -> VenueResponse:
    result = await zone_service.create_venue(body)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.get("/", response_model=VenueListResponse, summary="List all venues")
async def list_venues(
    zone_service: Annotated[ZoneService, Depends(get_zone_service)],
) -> VenueListResponse:
    result = await zone_service.list_venues()
    return VenueListResponse(items=unwrap_or_raise(result), total=0)


@router.get(
    "/{venue_id}/zones/tree", response_model=list[ZoneTreeResponse],
    summary="Get full zone hierarchy tree for a venue",
)
async def get_zone_tree(
    venue_id: str,
    zone_service: Annotated[ZoneService, Depends(get_zone_service)],
) -> list[ZoneTreeResponse]:
    result = await zone_service.get_zone_tree(venue_id)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.post(
    "/{venue_id}/zones", response_model=ZoneResponse, status_code=201,
    summary="Create a zone within a venue",
)
async def create_zone(
    venue_id: str,
    body: CreateZoneRequest,
    zone_service: Annotated[ZoneService, Depends(get_zone_service)],
) -> ZoneResponse:
    body.venue_id = venue_id
    result = await zone_service.create_zone(body)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.get(
    "/{venue_id}",
    response_model=VenueResponse,
    summary="Get a venue by ID",
)
async def get_venue(
    venue_id: str,
    zone_service: Annotated[ZoneService, Depends(get_zone_service)],
) -> VenueResponse:
    result = await zone_service.get_venue(venue_id)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.put(
    "/zones/{zone_id}", response_model=ZoneResponse,
    summary="Update a zone",
)
async def update_zone(
    zone_id: str,
    body: UpdateZoneRequest,
    zone_service: Annotated[ZoneService, Depends(get_zone_service)],
) -> ZoneResponse:
    result = await zone_service.update_zone(zone_id, body)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.get(
    "/zones/{zone_id}", response_model=ZoneResponse,
    summary="Get a zone by ID",
)
async def get_zone(
    zone_id: str,
    zone_service: Annotated[ZoneService, Depends(get_zone_service)],
) -> ZoneResponse:
    result = await zone_service.get_zone(zone_id)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.get(
    "/zones/{zone_id}/descendants", response_model=list[ZoneResponse],
    summary="Get all descendant zones",
)
async def get_zone_descendants(
    zone_id: str,
    zone_service: Annotated[ZoneService, Depends(get_zone_service)],
) -> list[ZoneResponse]:
    result = await zone_service.get_descendants(zone_id)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.delete("/zones/{zone_id}", summary="Soft-delete a zone")
async def delete_zone(
    zone_id: str,
    zone_service: Annotated[ZoneService, Depends(get_zone_service)],
) -> dict:
    result = await zone_service.delete_zone(zone_id)
    unwrap_or_raise(result)
    return {"message": "Zone deleted successfully"}
