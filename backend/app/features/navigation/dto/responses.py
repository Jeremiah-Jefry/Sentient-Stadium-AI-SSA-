"""Navigation response DTOs — Pydantic schemas for API output."""

from __future__ import annotations

from pydantic import BaseModel


class RouteStepResponse(BaseModel):
    """A single step in a computed route."""

    node_id: str
    name: str
    entity_type: str
    lat: float
    lon: float
    floor: int = 0
    edge_type: str = ""
    distance_meters: float = 0.0


class RouteResponse(BaseModel):
    """Complete route with quality metrics and explanation."""

    route_id: str
    origin_id: str
    destination_id: str
    steps: list[RouteStepResponse]
    total_distance_meters: float
    total_time_seconds: float
    safety_score: float
    accessibility_score: float
    crowd_exposure: float
    confidence: float
    grade: str
    profile: str
    route_type: str
    computation_ms: float
    algorithm_used: str


class RouteExplanationResponse(BaseModel):
    """Structured explanation for a route decision."""

    summary: str
    why_selected: str
    why_rejected_alternatives: list[str]
    risk_factors: list[str]
    expected_bottlenecks: list[str]
    predicted_delays: list[str]
    accessibility_notes: list[str]
    tradeoffs: list[str]


class RouteDetailResponse(BaseModel):
    """Full route response with explanation, alternatives, and simulation."""

    route: RouteResponse
    explanation: RouteExplanationResponse
    alternatives: list[RouteResponse]
    simulation_success_probability: float
    simulation_expected_delay: float
    accessibility_valid: bool
    accessibility_violations: list[str]


class EmergencyRouteResponse(BaseModel):
    """Emergency route response with scenario-specific metadata."""

    route: RouteResponse
    explanation: RouteExplanationResponse
    emergency_type: str


class NearestEntityResponse(BaseModel):
    """Result of a nearest-entity spatial query."""

    node_id: str
    name: str
    entity_type: str
    distance: float
    lat: float
    lon: float


class VolunteerAssignmentResponse(BaseModel):
    """Volunteer-task assignment result."""

    volunteer_id: str
    task_id: str
    travel_time_seconds: float
    total_distance_meters: float
    utility_score: float
    reasoning: str


class ReplanResponse(BaseModel):
    """Result of a replanning trigger."""

    route_id: str
    rerouted: bool
    trigger: str
    reason: str


class NavigationStatsResponse(BaseModel):
    """Navigation engine statistics."""

    graph_nodes: int
    graph_edges: int
    graph_version: int
    active_routes: int
    total_replans: int
    weight_engine_snapshot: dict
