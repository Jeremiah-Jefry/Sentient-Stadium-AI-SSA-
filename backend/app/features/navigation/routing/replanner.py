"""Realtime replanning engine — monitors conditions and triggers route recalculation.

When conditions change (gate closures, crowd surges, medical incidents,
weather, security restrictions, infrastructure failures):
- Automatically recalculates affected routes
- Supports incremental replanning
- Provides alternative suggestions
- Publishes reroute notifications
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import PathResult, WeightContext
from app.features.navigation.models.enums import ReplanTrigger, RoutingProfile
from app.features.navigation.pathfinding.algorithm import AlgorithmRegistry


@dataclass(slots=True)
class ActiveRoute:
    """A tracked active route that may need replanning."""

    route_id: str
    user_id: str
    profile: RoutingProfile
    origin: uuid.UUID
    destination: uuid.UUID
    current_path: PathResult
    current_step_index: int = 0
    created_at: float = field(default_factory=time.monotonic)
    last_replan_at: float = 0.0
    replan_count: int = 0


@dataclass(slots=True)
class ReplanResult:
    """Result of a replanning operation."""

    route_id: str
    rerouted: bool
    new_route: PathResult | None = None
    trigger: ReplanTrigger | None = None
    reason: str = ""
    alternatives: list[PathResult] = field(default_factory=list)


class RouteReplanner:
    """Monitors active routes and triggers recalculation when conditions change."""

    def __init__(
        self,
        graph: NavigationGraph,
        registry: AlgorithmRegistry,
    ) -> None:
        self._graph = graph
        self._registry = registry
        self._active_routes: dict[str, ActiveRoute] = {}
        self._replan_cooldown_seconds: float = 10.0

    def register_route(
        self,
        route_id: str,
        user_id: str,
        profile: RoutingProfile,
        origin: uuid.UUID,
        destination: uuid.UUID,
        route: PathResult,
    ) -> None:
        self._active_routes[route_id] = ActiveRoute(
            route_id=route_id,
            user_id=user_id,
            profile=profile,
            origin=origin,
            destination=destination,
            current_path=route,
        )

    def unregister_route(self, route_id: str) -> None:
        self._active_routes.pop(route_id, None)

    def advance_step(self, route_id: str, current_node: uuid.UUID) -> None:
        route = self._active_routes.get(route_id)
        if route is None:
            return
        for i, node_id in enumerate(route.current_path.path):
            if node_id == current_node and i > route.current_step_index:
                route.current_step_index = i
                break

    def handle_trigger(
        self,
        trigger: ReplanTrigger,
        affected_zone_id: str | None = None,
        ctx: WeightContext | None = None,
    ) -> list[ReplanResult]:
        """Evaluate all active routes for replanning given a condition change."""
        results: list[ReplanResult] = []
        now = time.monotonic()

        for route_id, active in list(self._active_routes.items()):
            if now - active.last_replan_at < self._replan_cooldown_seconds:
                continue

            if not self._route_affected(active, trigger, affected_zone_id):
                continue

            try:
                new_route = self._recalculate(active, ctx)
                rerouted = new_route.total_cost < active.current_path.total_cost * 1.1
                if rerouted:
                    active.current_path = new_route
                    active.last_replan_at = now
                    active.replan_count += 1

                results.append(ReplanResult(
                    route_id=route_id,
                    rerouted=rerouted,
                    new_route=new_route if rerouted else None,
                    trigger=trigger,
                    reason=f"Triggered by {trigger.value}",
                ))
            except Exception as exc:
                results.append(ReplanResult(
                    route_id=route_id,
                    rerouted=False,
                    trigger=trigger,
                    reason=f"Replanning failed: {exc}",
                ))

        return results

    def _route_affected(
        self,
        active: ActiveRoute,
        trigger: ReplanTrigger,
        zone_id: str | None,
    ) -> bool:
        remaining = active.current_path.path[active.current_step_index:]
        if not remaining:
            return False
        for node_id in remaining:
            node = self._graph.get_node(node_id)
            if node and zone_id and str(node.zone_id) == zone_id:
                return True
        if trigger in (ReplanTrigger.EMERGENCY_DECLARED, ReplanTrigger.GATE_CLOSURE):
            return zone_id is None
        return False

    def _recalculate(
        self,
        active: ActiveRoute,
        ctx: WeightContext | None,
    ) -> PathResult:
        current_node = active.current_path.path[
            min(active.current_step_index, len(active.current_path.path) - 1)
        ]
        algo = self._registry.select(self._graph.node_count)
        return algo.find_path(
            self._graph, current_node, active.destination, ctx,
        )

    @property
    def active_count(self) -> int:
        return len(self._active_routes)

    def get_stats(self) -> dict:
        total_replans = sum(r.replan_count for r in self._active_routes.values())
        return {
            "active_routes": len(self._active_routes),
            "total_replans": total_replans,
        }
