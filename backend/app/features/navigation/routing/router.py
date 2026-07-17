"""Main navigation router — orchestrates all routing subsystems.

Entry point for all route computation requests. Delegates to:
- Pathfinding algorithms
- Dynamic weight engine
- Routing profiles
- Accessibility engine
- Emergency router
- Volunteer router
- Route quality engine
- Route simulator
- Route explainer
- Route replanner
"""

from __future__ import annotations

import time
import uuid

from app.features.navigation.accessibility.engine import AccessibilityEngine
from app.features.navigation.emergency.router import EmergencyRouter
from app.features.navigation.explainability.explainer import RouteExplainer
from app.features.navigation.graph.dynamic_weights import DynamicWeightEngine
from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import (
    PathResult,
)
from app.features.navigation.models.enums import (
    EmergencyType,
    ReplanTrigger,
    RouteType,
    RoutingProfile,
    SpatialQueryType,
)
from app.features.navigation.pathfinding.algorithm import (
    AlgorithmRegistry,
)
from app.features.navigation.routing.quality import RouteQualityEngine
from app.features.navigation.routing.replanner import (
    ReplanResult,
    RouteReplanner,
)
from app.features.navigation.routing.spatial_queries import SpatialQueryEngine
from app.features.navigation.simulation.simulator import RouteSimulator
from app.features.navigation.volunteer.assignment import (
    AssignmentResult,
    VolunteerRouter,
    VolunteerState,
    VolunteerTask,
)


class NavigationRouter:
    """Main routing service — computes optimal routes across all profiles."""

    def __init__(
        self,
        graph: NavigationGraph,
        weight_engine: DynamicWeightEngine,
        registry: AlgorithmRegistry | None = None,
    ) -> None:
        self._graph = graph
        self._weight_engine = weight_engine
        self._registry = registry or AlgorithmRegistry()
        self._quality = RouteQualityEngine(graph)
        self._explainer = RouteExplainer(graph)
        self._simulator = RouteSimulator(graph)
        self._replanner = RouteReplanner(graph, self._registry)
        self._spatial = SpatialQueryEngine(graph)
        self._accessibility = AccessibilityEngine(graph)
        self._emergency = EmergencyRouter(graph, self._registry)
        self._volunteer = VolunteerRouter(graph, self._registry)

    def compute_route(
        self,
        origin: uuid.UUID,
        destination: uuid.UUID,
        profile: RoutingProfile = RoutingProfile.SPECTATOR,
        route_type: RouteType = RouteType.FASTEST,
        zone_id: str | None = None,
        alternatives_count: int = 3,
    ) -> dict:
        """Compute optimal route with quality metrics and explanation."""
        t_start = time.monotonic()
        weight_ctx = self._weight_engine.build_context(zone_id)

        algo = self._registry.select(
            self._graph.node_count, alternatives_count,
        )
        result = algo.find_path(
            self._graph, origin, destination, weight_ctx,
        )

        alternatives: list[PathResult] = []
        if alternatives_count > 1:
            try:
                k_results = self._graph.find_k_shortest(
                    origin, destination, alternatives_count, weight_ctx,
                )
                alternatives = [r for r in k_results if r.path != result.path]
            except Exception:
                pass

        simulated = self._simulator.simulate(result, weight_ctx)
        metrics = self._quality.assess(result, profile, weight_ctx)
        explanation = self._explainer.explain(result, metrics, profile, alternatives)

        is_valid, violations = self._accessibility.validate_route(result, profile)

        elapsed = (time.monotonic() - t_start) * 1000

        return {
            "route": result,
            "metrics": metrics,
            "explanation": explanation,
            "simulation": simulated,
            "alternatives": alternatives[:3],
            "accessibility_valid": is_valid,
            "accessibility_violations": violations,
            "computation_ms": elapsed,
            "profile": profile.value,
            "route_type": route_type.value,
        }

    def compute_emergency_route(
        self,
        start: uuid.UUID,
        emergency_type: EmergencyType,
        destination_id: uuid.UUID | None = None,
        zone_id: str | None = None,
    ) -> dict:
        """Compute emergency-specific route."""
        weight_ctx = self._weight_engine.build_context(zone_id)
        result = self._emergency.compute_emergency_route(
            start, emergency_type, weight_ctx, destination_id,
        )
        metrics = self._quality.assess(result, RoutingProfile.ADMINISTRATOR, weight_ctx)
        explanation = self._explainer.explain(result, metrics, RoutingProfile.ADMINISTRATOR)

        return {
            "route": result,
            "metrics": metrics,
            "explanation": explanation,
            "emergency_type": emergency_type.value,
        }

    def find_nearest(
        self,
        from_id: uuid.UUID,
        query_type: SpatialQueryType,
        zone_id: str | None = None,
    ) -> dict | None:
        """Find nearest entity of specified type."""
        weight_ctx = self._weight_engine.build_context(zone_id)
        result = self._spatial.find_nearest(from_id, query_type, weight_ctx)
        if result is None:
            return None
        node, dist = result
        return {
            "node_id": str(node.node_id),
            "name": node.name,
            "entity_type": node.entity_type,
            "distance": dist,
            "lat": node.lat,
            "lon": node.lon,
        }

    def compute_volunteer_assignments(
        self,
        volunteers: list[VolunteerState],
        tasks: list[VolunteerTask],
        zone_id: str | None = None,
    ) -> list[AssignmentResult]:
        """Optimize volunteer task assignments."""
        weight_ctx = self._weight_engine.build_context(zone_id)
        return self._volunteer.compute_batch_assignments(
            volunteers, tasks, weight_ctx,
        )

    def handle_replan_trigger(
        self,
        trigger: ReplanTrigger,
        zone_id: str | None = None,
    ) -> list[ReplanResult]:
        """Process a replanning trigger across all active routes."""
        weight_ctx = self._weight_engine.build_context(zone_id)
        return self._replanner.handle_trigger(trigger, zone_id, weight_ctx)

    def register_active_route(
        self,
        route_id: str,
        user_id: str,
        profile: RoutingProfile,
        origin: uuid.UUID,
        destination: uuid.UUID,
        route: PathResult,
    ) -> None:
        """Track an active route for replanning."""
        self._replanner.register_route(
            route_id, user_id, profile, origin, destination, route,
        )

    @property
    def graph(self) -> NavigationGraph:
        return self._graph

    @property
    def weight_engine(self) -> DynamicWeightEngine:
        return self._weight_engine

    @property
    def replanner(self) -> RouteReplanner:
        return self._replanner

    @property
    def spatial(self) -> SpatialQueryEngine:
        return self._spatial
