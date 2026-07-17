"""Spatial queries — nearest entity, nearby density, incidents, hazards.

Provides high-level spatial query API over the navigation graph for:
- Nearest exit, AED, medical room, volunteer, restroom, etc.
- Nearby crowd density aggregation
- Nearby incidents and hazards
- Nearby accessible routes
"""

from __future__ import annotations

import uuid

from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import NavNode, WeightContext
from app.features.navigation.models.enums import SpatialQueryType

ENTITY_TYPE_MAP: dict[SpatialQueryType, set[str]] = {
    SpatialQueryType.NEAREST_EXIT: {"exit", "emergency_exit"},
    SpatialQueryType.NEAREST_AED: {"aed"},
    SpatialQueryType.NEAREST_MEDICAL_ROOM: {"medical_room", "first_aid_post"},
    SpatialQueryType.NEAREST_VOLUNTEER: {"volunteer_position"},
    SpatialQueryType.NEAREST_RESTROOM: {"restroom"},
    SpatialQueryType.NEAREST_WHEELCHAIR_STATION: {"wheelchair_station"},
    SpatialQueryType.NEAREST_INFORMATION_DESK: {"information_desk"},
    SpatialQueryType.NEAREST_SECURITY_OFFICER: {"security_checkpoint"},
}


class SpatialQueryEngine:
    """Executes spatial queries against the navigation graph."""

    def __init__(self, graph: NavigationGraph) -> None:
        self._graph = graph

    def find_nearest(
        self,
        from_id: uuid.UUID,
        query_type: SpatialQueryType,
        ctx: WeightContext | None = None,
    ) -> tuple[NavNode, float] | None:
        """Find nearest entity of the specified type."""
        target_types = ENTITY_TYPE_MAP.get(query_type)
        if target_types is None:
            return None
        return self._graph.find_nearest(from_id, target_types, ctx)

    def find_nearest_with_accessibility(
        self,
        from_id: uuid.UUID,
        query_type: SpatialQueryType,
        ctx: WeightContext | None = None,
    ) -> tuple[NavNode, float] | None:
        """Find nearest accessible entity."""
        target_types = ENTITY_TYPE_MAP.get(query_type)
        if target_types is None:
            return None
        result = self._graph.find_nearest(from_id, target_types, ctx)
        if result is None:
            return None
        node, dist = result
        if node.accessibility_level == "none":
            return None
        return node, dist

    def find_nearby_density(
        self,
        center_id: uuid.UUID,
        radius: float = 200.0,
        ctx: WeightContext | None = None,
    ) -> list[tuple[NavNode, float, float]]:
        """Find nearby nodes with crowd density information."""
        results = self._graph.find_within_radius(
            center_id, radius, ctx=ctx,
        )
        return [
            (node, dist, node.current_capacity / max(node.max_capacity, 1))
            for node, dist in results
            if node.max_capacity > 0
        ]

    def find_nearby_incidents(
        self,
        center_id: uuid.UUID,
        incident_node_ids: set[uuid.UUID],
        radius: float = 500.0,
        ctx: WeightContext | None = None,
    ) -> list[tuple[NavNode, float]]:
        """Find incidents within cost radius."""
        results = self._graph.find_within_radius(
            center_id, radius, ctx=ctx,
        )
        return [
            (node, dist)
            for node, dist in results
            if node.node_id in incident_node_ids
        ]

    def find_nearby_hazards(
        self,
        center_id: uuid.UUID,
        hazard_node_ids: set[uuid.UUID],
        radius: float = 300.0,
        ctx: WeightContext | None = None,
    ) -> list[tuple[NavNode, float]]:
        """Find hazards within cost radius."""
        results = self._graph.find_within_radius(
            center_id, radius, ctx=ctx,
        )
        return [
            (node, dist)
            for node, dist in results
            if node.node_id in hazard_node_ids
        ]

    def count_nearby(
        self,
        center_id: uuid.UUID,
        target_types: set[str],
        radius: float = 100.0,
        ctx: WeightContext | None = None,
    ) -> int:
        """Count entities of given types within radius."""
        results = self._graph.find_within_radius(
            center_id, radius, target_types, ctx,
        )
        return len(results)
