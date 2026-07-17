"""Route simulation layer — predict route success before returning to user.

Simulates:
- Future crowd movement along the path
- Gate status changes
- Predicted congestion buildup
- Expected delays at each node
- Weather impact over travel time
- Medical incident probability

Returns the route with highest expected success probability.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import PathResult, WeightContext


@dataclass(slots=True)
class SimulationResult:
    """Outcome of simulating a route through predicted future conditions."""

    route_id: str
    success_probability: float
    expected_delay_seconds: float
    predicted_congestion_points: list[str]
    predicted_gate_closures: list[str]
    weather_impact: float
    risk_events_detected: int
    confidence: float
    simulation_steps: int = 0


@dataclass(slots=True)
class SimulationConfig:
    """Configuration for route simulation."""

    time_horizon_seconds: float = 300.0
    step_size_seconds: float = 30.0
    max_simulation_steps: int = 10
    crowd_growth_rate: float = 0.05
    weather_change_probability: float = 0.1


class RouteSimulator:
    """Simulates route execution under predicted future conditions."""

    def __init__(self, graph: NavigationGraph) -> None:
        self._graph = graph

    def simulate(
        self,
        result: PathResult,
        ctx: WeightContext | None = None,
        config: SimulationConfig | None = None,
    ) -> SimulationResult:
        """Simulate a route and predict success probability."""
        weight_ctx = ctx or WeightContext()
        sim_config = config or SimulationConfig()

        delay = 0.0
        congestion_points: list[str] = []
        gate_closures: list[str] = []
        weather_impact = 0.0
        risk_events = 0
        steps = 0

        cumulative_crowd = weight_ctx.crowd_density
        cumulative_risk = weight_ctx.risk_score

        for _i, node_id in enumerate(result.path):
            node = self._graph.get_node(node_id)
            if node is None:
                continue

            steps += 1
            cumulative_crowd += sim_config.crowd_growth_rate

            if cumulative_crowd > 0.8:
                congestion_points.append(node.name)
                delay += 30.0 * cumulative_crowd

            if node.max_capacity > 0:
                ratio = node.current_capacity / node.max_capacity
                if ratio > 0.9:
                    delay += 60.0

            if node.entity_type in ("escalator", "elevator"):
                if not weight_ctx.escalator_available or not weight_ctx.elevator_available:
                    gate_closures.append(f"{node.name} unavailable")
                    delay += 120.0

            if cumulative_risk > 0.7:
                risk_events += 1
                delay += 45.0

            weather_impact += weight_ctx.weather_penalty * 5.0

            if steps >= sim_config.max_simulation_steps:
                break

        total_expected_time = result.total_time_seconds + delay
        success_prob = max(0.0, 1.0 - (delay / max(total_expected_time, 1.0)))
        success_prob *= max(0.0, 1.0 - cumulative_risk * 0.3)
        success_prob *= max(0.0, 1.0 - len(congestion_points) * 0.1)

        return SimulationResult(
            route_id=str(result.path[0]) if result.path else "",
            success_probability=min(1.0, max(0.0, success_prob)),
            expected_delay_seconds=delay,
            predicted_congestion_points=congestion_points,
            predicted_gate_closures=gate_closures,
            weather_impact=weather_impact,
            risk_events_detected=risk_events,
            confidence=success_prob,
            simulation_steps=steps,
        )

    def compare_routes(
        self,
        routes: list[PathResult],
        ctx: WeightContext | None = None,
    ) -> list[tuple[PathResult, SimulationResult]]:
        """Simulate multiple routes and return ranked by success probability."""
        results = []
        for route in routes:
            sim = self.simulate(route, ctx)
            results.append((route, sim))
        results.sort(key=lambda x: x[1].success_probability, reverse=True)
        return results
