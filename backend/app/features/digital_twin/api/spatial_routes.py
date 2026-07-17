"""Spatial API routes - nearby search, pathfinding, edge management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.features.digital_twin.api.deps import get_spatial_service
from app.features.digital_twin.api.route_utils import unwrap_or_raise
from app.features.digital_twin.dto.spatial_requests import (
    CreateEdgeRequest,
    NearbySearchRequest,
    PathfindingRequest,
    SpatialBoundsRequest,
)
from app.features.digital_twin.dto.spatial_responses import (
    EdgeResponse,
    NearbySearchResponse,
    PathfindingResponse,
)
from app.features.digital_twin.services.spatial_service import SpatialService

router = APIRouter(prefix="/spatial", tags=["Spatial Queries"])


@router.post(
    "/nearby", response_model=NearbySearchResponse,
    summary="Find entities near a geographic point",
)
async def nearby_search(
    body: NearbySearchRequest,
    spatial_service: Annotated[SpatialService, Depends(get_spatial_service)],
) -> NearbySearchResponse:
    result = await spatial_service.nearby_search(body)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.get(
    "/nearby", response_model=NearbySearchResponse,
    summary="Find entities near a point via GET query params",
)
async def nearby_search_get(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    radius_meters: float = Query(500.0, gt=0, le=10000),
    entity_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    spatial_service: Annotated[SpatialService, Depends(get_spatial_service)],
) -> NearbySearchResponse:
    from app.features.digital_twin.models.entity_type import EntityType

    req = NearbySearchRequest(
        latitude=latitude, longitude=longitude,
        radius_meters=radius_meters,
        entity_type=EntityType(entity_type) if entity_type else None,
        limit=limit,
    )
    result = await spatial_service.nearby_search(req)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.post(
    "/pathfinding", response_model=PathfindingResponse,
    summary="Find shortest path between two entities",
)
async def find_path(
    body: PathfindingRequest,
    spatial_service: Annotated[SpatialService, Depends(get_spatial_service)],
) -> PathfindingResponse:
    result = await spatial_service.find_path(body)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.post(
    "/bounds",
    summary="Find entities within a bounding box",
)
async def bounds_search(
    body: SpatialBoundsRequest,
    spatial_service: Annotated[SpatialService, Depends(get_spatial_service)],
) -> list[dict]:
    result = await spatial_service.bounds_search(body)
    return [item.model_dump() for item in unwrap_or_raise(result)]


@router.post(
    "/edges", response_model=EdgeResponse, status_code=201,
    summary="Create a graph edge between two entities",
)
async def create_edge(
    body: CreateEdgeRequest,
    spatial_service: Annotated[SpatialService, Depends(get_spatial_service)],
) -> EdgeResponse:
    result = await spatial_service.create_edge(body)
    return unwrap_or_raise(result)  # type: ignore[return-value]


@router.get(
    "/edges/{venue_id}", response_model=list[EdgeResponse],
    summary="Get all edges for a venue",
)
async def get_edges(
    venue_id: str,
    spatial_service: Annotated[SpatialService, Depends(get_spatial_service)],
) -> list[EdgeResponse]:
    result = await spatial_service.get_edges_for_venue(venue_id)
    return unwrap_or_raise(result)  # type: ignore[return-value]
