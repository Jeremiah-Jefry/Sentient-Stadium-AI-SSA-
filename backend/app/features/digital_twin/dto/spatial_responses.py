"""Spatial and graph query response DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NearbyEntityResponse(BaseModel):
    """Entity with computed distance from the query point."""

    id: str
    name: str
    entity_type: str
    operational_status: str
    current_health: str
    coordinates_lat: float
    coordinates_lon: float
    distance_meters: float


class NearbySearchResponse(BaseModel):
    """Results of a nearby spatial search."""

    entities: list[NearbyEntityResponse]
    query_lat: float
    query_lon: float
    radius_meters: float
    count: int


class PathStepResponse(BaseModel):
    """Single step in a computed path."""

    entity_id: str
    entity_name: str
    entity_type: str
    coordinates_lat: float
    coordinates_lon: float
    edge_type: str
    distance_meters: float


class PathfindingResponse(BaseModel):
    """Complete path between two entities."""

    from_entity_id: str
    to_entity_id: str
    steps: list[PathStepResponse]
    total_distance_meters: float
    total_steps: int
    accessibility_compliant: bool


class EdgeResponse(BaseModel):
    """Graph edge representation."""

    id: str
    from_entity_id: str
    to_entity_id: str
    edge_type: str
    weight: float
    is_bidirectional: bool
    accessibility_level: str
    venue_id: str


class GraphStatsResponse(BaseModel):
    """Graph connectivity statistics for monitoring."""

    total_nodes: int
    total_edges: int
    connected_components: int
    average_degree: float
    max_degree: int
    isolated_nodes: int
