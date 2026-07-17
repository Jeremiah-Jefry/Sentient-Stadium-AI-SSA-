"""Zone and spatial reasoning — topology-based risk propagation and bottleneck detection."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

RISK_PROPAGATION_DECAY: float = 0.6
BOTTLENECK_THRESHOLD: float = 0.75
MAX_SPREAD_STEPS: int = 8
DENSITY_WARN_RATIO: float = 0.7
DENSITY_DANGER_RATIO: float = 0.9


@dataclass(slots=True)
class Bottleneck:
    """Identified bottleneck in the venue topology."""

    zone_id: str
    severity: float
    cause: str
    affected_neighbors: list[str] = field(default_factory=list)
    predicted_spread: list[dict] = field(default_factory=list)


class SpatialReasoner:
    """Reasons about spatial relationships, zone interactions, and crowd propagation.

    Integrates with the Digital Twin via the zone graph.
    Never reads sensors directly — works with fused data and zone topology.
    """

    def __init__(self, zone_graph: dict | None = None) -> None:
        self._zone_graph: dict = zone_graph or {}
        self._risk_cache: dict[str, float] = {}

    def compute_zone_risk(self, zone_id: str, zone_data: dict) -> float:
        """Compute risk for a single zone based on its current state."""
        capacity = zone_data.get("capacity", 1)
        current_occupancy = zone_data.get("occupancy", 0)
        if capacity <= 0:
            return 1.0
        occupancy_ratio = current_occupancy / capacity
        incident_count = len(zone_data.get("incidents", []))
        incident_factor = min(incident_count / 10.0, 1.0)
        blocked_exits = zone_data.get("blocked_exits", 0)
        total_exits = zone_data.get("total_exits", 1)
        exit_factor = blocked_exits / max(total_exits, 1)

        risk = 0.5 * occupancy_ratio + 0.3 * incident_factor + 0.2 * exit_factor
        risk = max(0.0, min(1.0, risk))
        self._risk_cache[zone_id] = risk
        return risk

    def compute_neighbor_influence(self, zone_id: str) -> float:
        """Compute risk influence from neighboring zones (risk propagation)."""
        neighbors = self._zone_graph.get(zone_id, {}).get("neighbors", [])
        if not neighbors:
            return 0.0

        max_neighbor_risk = 0.0
        for neighbor_id in neighbors:
            base_risk = self._risk_cache.get(neighbor_id, 0.0)
            propagated = base_risk * RISK_PROPAGATION_DECAY
            max_neighbor_risk = max(max_neighbor_risk, propagated)

        return max_neighbor_risk

    def find_bottlenecks(self, venue_data: dict) -> list[dict]:
        """Identify current and emerging bottlenecks in the venue."""
        bottlenecks: list[dict] = []

        for zone_id, zone_data in venue_data.items():
            zone_info = zone_data if isinstance(zone_data, dict) else {}
            capacity = zone_info.get("capacity", 1)
            occupancy = zone_info.get("occupancy", 0)

            if capacity <= 0:
                continue

            ratio = occupancy / capacity
            if ratio < DENSITY_WARN_RATIO:
                continue

            severity = self._classify_bottleneck_severity(ratio)
            cause = self._identify_bottleneck_cause(zone_info)
            neighbors = self._zone_graph.get(zone_id, {}).get("neighbors", [])

            spread = self.predict_congestion_spread(zone_id, severity, 3)

            bottlenecks.append({
                "zone_id": zone_id,
                "severity": round(severity, 4),
                "cause": cause,
                "affected_neighbors": neighbors,
                "predicted_spread": spread,
                "occupancy_ratio": round(ratio, 4),
            })

        bottlenecks.sort(key=lambda b: b["severity"], reverse=True)
        return bottlenecks

    def predict_congestion_spread(
        self, source_zone: str, intensity: float, steps: int,
    ) -> list[dict]:
        """Predict how congestion will spread from a source zone."""
        steps = min(steps, MAX_SPREAD_STEPS)
        visited: dict[str, float] = {source_zone: intensity}
        queue: deque[tuple[str, int, float]] = deque(
            [(source_zone, 0, intensity)],
        )
        spread: list[dict] = []

        while queue:
            zone, depth, current_intensity = queue.popleft()
            if depth >= steps:
                continue
            neighbors = self._zone_graph.get(zone, {}).get("neighbors", [])
            for neighbor in neighbors:
                if neighbor in visited:
                    continue
                propagated = current_intensity * RISK_PROPAGATION_DECAY
                visited[neighbor] = propagated
                spread.append({
                    "zone_id": neighbor,
                    "depth": depth + 1,
                    "predicted_intensity": round(propagated, 4),
                })
                if propagated > 0.1:
                    queue.append((neighbor, depth + 1, propagated))

        return spread

    def compute_route_impact(self, origin: str, destination: str) -> dict:
        """Assess impact on a route between two zones using BFS."""
        if origin == destination:
            return {"route": [origin], "impact_score": 0.0, "hops": 0}

        visited: set[str] = {origin}
        queue: deque[tuple[str, list[str]]] = deque([(origin, [origin])])

        while queue:
            current, path = queue.popleft()
            neighbors = self._zone_graph.get(current, {}).get("neighbors", [])
            for neighbor in neighbors:
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == destination:
                    return self._evaluate_route(new_path)
                visited.add(neighbor)
                queue.append((neighbor, new_path))

        return {"route": [], "impact_score": 1.0, "hops": -1}

    def get_evacuation_efficiency(self, zone_id: str) -> float:
        """Estimate evacuation efficiency for a zone (0-1)."""
        zone_info = self._zone_graph.get(zone_id, {})
        exit_count = zone_info.get("exit_count", 0)
        capacity = zone_info.get("capacity", 1)
        blocked_exits = zone_info.get("blocked_exits", 0)
        effective_exits = max(exit_count - blocked_exits, 0)

        if capacity <= 0 or exit_count <= 0:
            return 0.0

        exit_ratio = effective_exits / exit_count
        capacity_per_exit = capacity / max(effective_exits, 1)
        load_factor = 1.0 - min(capacity_per_exit / 1000.0, 1.0)

        return max(0.0, min(1.0, 0.6 * exit_ratio + 0.4 * load_factor))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _classify_bottleneck_severity(ratio: float) -> float:
        if ratio >= 1.0:
            return 1.0
        if ratio >= DENSITY_DANGER_RATIO:
            return 0.8 + 0.2 * ((ratio - DENSITY_DANGER_RATIO) / (1.0 - DENSITY_DANGER_RATIO))
        if ratio >= BOTTLENECK_THRESHOLD:
            denom = DENSITY_DANGER_RATIO - BOTTLENECK_THRESHOLD
            return 0.5 + 0.3 * ((ratio - BOTTLENECK_THRESHOLD) / denom)
        denom = BOTTLENECK_THRESHOLD - DENSITY_WARN_RATIO
        return 0.3 + 0.2 * ((ratio - DENSITY_WARN_RATIO) / denom)

    @staticmethod
    def _identify_bottleneck_cause(zone_info: dict) -> str:
        blocked_exits = zone_info.get("blocked_exits", 0)
        incidents = zone_info.get("incidents", [])
        if blocked_exits > 0:
            return f"blocked_exits:{blocked_exits}"
        if incidents:
            return f"incidents:{len(incidents)}"
        return "high_occupancy"

    def _evaluate_route(self, path: list[str]) -> dict:
        max_risk = 0.0
        for zone_id in path:
            risk = self._risk_cache.get(zone_id, 0.0)
            max_risk = max(max_risk, risk)

        avg_risk = sum(
            self._risk_cache.get(z, 0.0) for z in path
        ) / max(len(path), 1)

        impact = 0.7 * max_risk + 0.3 * avg_risk
        return {
            "route": path,
            "impact_score": round(impact, 4),
            "hops": len(path) - 1,
        }
