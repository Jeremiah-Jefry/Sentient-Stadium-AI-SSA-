"""Navigation route endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.features.navigation.api.deps import get_navigation_router
from app.features.navigation.dto.requests import (
    EmergencyRouteRequest,
    RouteRequest,
    SpatialQueryRequest,
)
from app.features.navigation.models.enums import (
    EmergencyType,
    RouteType,
    RoutingProfile,
    SpatialQueryType,
)
from app.features.navigation.routing.router import NavigationRouter

router = APIRouter(prefix="/routes", tags=["Navigation Routes"])


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    """Parse and validate a UUID string, raising ValueError on failure."""
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid {field_name}: must be a valid UUID",
        ) from exc


@router.post("/compute")
async def compute_route(
    request: RouteRequest,
    nav: NavigationRouter = Depends(get_navigation_router),
) -> dict:
    origin = _parse_uuid(request.origin_id, "origin_id")
    dest = _parse_uuid(request.destination_id, "destination_id")
    result = nav.compute_route(
        origin=origin,
        destination=dest,
        profile=RoutingProfile(request.profile),
        route_type=RouteType(request.route_type),
        zone_id=request.zone_id,
        alternatives_count=request.alternatives_count,
    )
    return {
        "route_id": (
            str(result["route"].path[0])
            if result["route"].path else ""
        ),
        "steps": [
            {
                "node_id": str(nid),
                "edge_type": (
                    result["route"].edges[i]
                    if i < len(result["route"].edges) else ""
                ),
            }
            for i, nid in enumerate(result["route"].path)
        ],
        "total_distance_meters": (
            result["route"].total_distance_meters
        ),
        "total_time_seconds": (
            result["route"].total_time_seconds
        ),
        "grade": result["metrics"].grade,
        "safety_score": result["metrics"].safety_score,
        "accessibility_score": result["metrics"].accessibility_score,
        "computation_ms": result["computation_ms"],
        "profile": result["profile"],
        "route_type": result["route_type"],
        "alternatives_count": len(result["alternatives"]),
        "simulation_success_probability": (
            result["simulation"].success_probability
        ),
        "explanation": result["explanation"].summary,
    }


@router.post("/emergency")
async def compute_emergency_route(
    request: EmergencyRouteRequest,
    nav: NavigationRouter = Depends(get_navigation_router),
) -> dict:
    start = _parse_uuid(request.start_id, "start_id")
    dest = (
        _parse_uuid(request.destination_id, "destination_id")
        if request.destination_id else None
    )
    result = nav.compute_emergency_route(
        start=start,
        emergency_type=EmergencyType(request.emergency_type),
        destination_id=dest,
        zone_id=request.zone_id,
    )
    return {
        "route_id": (
            str(result["route"].path[0])
            if result["route"].path else ""
        ),
        "emergency_type": result["emergency_type"],
        "total_time_seconds": (
            result["route"].total_time_seconds
        ),
        "total_distance_meters": (
            result["route"].total_distance_meters
        ),
        "grade": result["metrics"].grade,
        "explanation": result["explanation"].summary,
    }


@router.post("/spatial")
async def spatial_query(
    request: SpatialQueryRequest,
    nav: NavigationRouter = Depends(get_navigation_router),
) -> dict:
    from_id = _parse_uuid(request.from_id, "from_id")
    result = nav.find_nearest(
        from_id=from_id,
        query_type=SpatialQueryType(request.query_type),
        zone_id=request.zone_id,
    )
    if result is None:
        return {"found": False}
    return {"found": True, **result}


@router.get("/stats")
async def navigation_stats(
    nav: NavigationRouter = Depends(get_navigation_router),
) -> dict:
    return {
        "graph_nodes": nav.graph.node_count,
        "graph_edges": nav.graph.edge_count,
        "graph_version": nav.graph.version,
        "active_routes": nav.replanner.active_count,
        "weight_engine": nav.weight_engine.snapshot(),
    }
