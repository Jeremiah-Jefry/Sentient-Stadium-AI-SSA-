"""Navigation graph data structures — nodes, edges, weight context, path result."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NavNode:
    """A node in the navigation graph with spatial and semantic metadata."""

    node_id: uuid.UUID
    name: str
    entity_type: str
    lat: float
    lon: float
    floor: int = 0
    zone_id: uuid.UUID | None = None
    accessibility_level: str = "full"
    is_occupied: bool = False
    current_capacity: int = 0
    max_capacity: int = 0


@dataclass(frozen=True, slots=True)
class NavEdge:
    """A weighted directed edge with multi-dimensional cost metadata."""

    from_id: uuid.UUID
    to_id: uuid.UUID
    edge_type: str
    base_weight: float
    accessibility_level: str = "full"
    is_bidirectional: bool = True
    distance_meters: float = 0.0
    floor_change: int = 0


@dataclass(slots=True)
class WeightContext:
    """Dynamic factors that modify edge traversal cost at query time."""

    crowd_density: float = 0.0
    walking_speed_modifier: float = 1.0
    weather_penalty: float = 0.0
    escalator_available: bool = True
    elevator_available: bool = True
    emergency_active: bool = False
    maintenance_active: bool = False
    security_restricted: bool = False
    medical_incident_nearby: bool = False
    cleaning_active: bool = False
    temporarily_closed: bool = False
    risk_score: float = 0.0
    predicted_congestion: float = 0.0
    waiting_time_seconds: float = 0.0
    energy_cost_modifier: float = 1.0


@dataclass(frozen=True, slots=True)
class EdgeCost:
    """Computed multi-dimensional cost for a single edge traversal."""

    time_seconds: float
    distance_meters: float
    safety_score: float
    accessibility_score: float
    crowd_exposure: float
    energy_cost: float
    confidence: float = 1.0


@dataclass(slots=True)
class PathResult:
    """Complete result of a pathfinding computation with quality metrics."""

    path: list[uuid.UUID]
    edges: list[str]
    total_distance_meters: float
    total_time_seconds: float
    total_cost: float
    safety_score: float = 1.0
    accessibility_score: float = 1.0
    crowd_exposure: float = 0.0
    energy_cost: float = 0.0
    confidence: float = 1.0
    algorithm_used: str = ""
    nodes_visited: int = 0
    computation_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class RouteExplanation:
    """Structured explanation of why a route was selected."""

    summary: str
    why_selected: str
    why_rejected_alternatives: list[str]
    risk_factors: list[str]
    expected_bottlenecks: list[str]
    predicted_delays: list[str]
    accessibility_notes: list[str]
    tradeoffs: list[str]


@dataclass(slots=True)
class QualityMetrics:
    """Multi-metric quality assessment for a computed route."""

    travel_time_seconds: float
    walking_distance_meters: float
    safety_score: float
    accessibility_score: float
    crowd_exposure_score: float
    risk_score: float
    energy_cost: float
    route_reliability: float
    confidence: float
    overall_score: float
    grade: str = "A"
