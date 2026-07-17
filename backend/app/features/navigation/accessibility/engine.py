"""Accessibility routing engine — ensures all routes comply with constraints.

Supports:
- Wheelchair routing (elevators, ramps, wide corridors, low slope)
- Blind user routing (tactile paths, audio beacons, staff corridors)
- Hearing impaired routing (visual signage, emergency exit proximity)
- Generic accessibility (low crowd, wide paths, accessible facilities)
"""

from __future__ import annotations

import uuid

from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import PathResult, WeightContext
from app.features.navigation.models.enums import RoutingProfile
from app.features.navigation.routing.profile import get_profile_config


class AccessibilityEngine:
    """Validates and enforces accessibility constraints on computed routes.

    Acts as a post-processing filter and pre-computation constraint layer.
    """

    def __init__(self, graph: NavigationGraph) -> None:
        self._graph = graph

    def validate_route(
        self,
        result: PathResult,
        profile: RoutingProfile,
    ) -> tuple[bool, list[str]]:
        """Validate a computed route against accessibility requirements."""
        config = get_profile_config(profile)
        violations: list[str] = []

        if not config.requires_accessibility:
            return True, violations

        for _i, node_id in enumerate(result.path):
            node = self._graph.get_node(node_id)
            if node is None:
                continue
            if config.requires_accessibility and node.accessibility_level == "none":
                violations.append(
                    f"Node {node.name} ({node_id}) has no accessibility",
                )

        for i, edge_type in enumerate(result.edges):
            if config.avoid_stairs and edge_type == "stairs":
                violations.append(f"Step {i}: uses stairs")
            if config.avoid_escalators and edge_type == "escalator":
                violations.append(f"Step {i}: uses escalator")
            if edge_type not in config.allowed_edge_types:
                violations.append(
                    f"Step {i}: edge type '{edge_type}' not in allowed set",
                )

        is_valid = len(violations) == 0
        return is_valid, violations

    def build_accessibility_context(
        self,
        profile: RoutingProfile,
    ) -> WeightContext:
        """Build WeightContext with accessibility constraints baked in."""
        config = get_profile_config(profile)
        ctx = WeightContext()

        if config.requires_accessibility:
            ctx.crowd_density = min(ctx.crowd_density, config.max_crowd_exposure)

        if config.prefer_elevators:
            ctx.escalator_available = False

        return ctx

    def find_accessible_nearest(
        self,
        from_id: uuid.UUID,
        target_types: set[str],
        ctx: WeightContext | None = None,
    ) -> tuple[uuid.UUID, float] | None:
        """Find nearest accessible entity of given types."""
        result = self._graph.find_nearest(from_id, target_types, ctx)
        if result is None:
            return None
        node, dist = result
        if node.accessibility_level == "none":
            return None
        return node.node_id, dist

    def filter_accessible_nodes(
        self,
        node_ids: list[uuid.UUID],
        profile: RoutingProfile,
    ) -> list[uuid.UUID]:
        """Filter node list to only those accessible for the given profile."""
        config = get_profile_config(profile)
        if not config.requires_accessibility:
            return node_ids

        filtered: list[uuid.UUID] = []
        for nid in node_ids:
            node = self._graph.get_node(nid)
            if node and node.accessibility_level != "none":
                filtered.append(nid)
        return filtered
