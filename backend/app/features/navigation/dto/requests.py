"""Navigation request DTOs — Pydantic schemas for API input."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    """Request to compute a route between two locations."""

    origin_id: str = Field(..., description="Origin entity UUID")
    destination_id: str = Field(..., description="Destination entity UUID")
    profile: str = Field(default="spectator", description="Routing profile")
    route_type: str = Field(default="fastest", description="Route optimization type")
    zone_id: str | None = Field(default=None, description="Context zone ID")
    alternatives_count: int = Field(default=3, ge=1, le=10)


class EmergencyRouteRequest(BaseModel):
    """Request to compute an emergency route."""

    start_id: str = Field(..., description="Starting entity UUID")
    emergency_type: str = Field(..., description="Emergency scenario type")
    destination_id: str | None = Field(default=None, description="Target entity UUID")
    zone_id: str | None = Field(default=None, description="Context zone ID")


class SpatialQueryRequest(BaseModel):
    """Request for a spatial proximity query."""

    from_id: str = Field(..., description="Origin entity UUID")
    query_type: str = Field(..., description="Type of spatial query")
    zone_id: str | None = Field(default=None, description="Context zone ID")


class VolunteerAssignmentRequest(BaseModel):
    """Request for volunteer task assignment optimization."""

    volunteer_ids: list[str] = Field(..., min_length=1)
    task_ids: list[str] = Field(..., min_length=1)
    zone_id: str | None = Field(default=None)


class BatchRouteRequest(BaseModel):
    """Request for batch route computation."""

    routes: list[RouteRequest] = Field(..., min_length=1, max_length=50)


class ReplanRequest(BaseModel):
    """Request to trigger replanning for a zone."""

    trigger: str = Field(..., description="Replan trigger type")
    zone_id: str | None = Field(default=None)


class RouteFeedbackRequest(BaseModel):
    """User feedback on a computed route."""

    route_id: str = Field(...)
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)
    deviated: bool = Field(default=False)
    actual_duration_seconds: float | None = Field(default=None)
