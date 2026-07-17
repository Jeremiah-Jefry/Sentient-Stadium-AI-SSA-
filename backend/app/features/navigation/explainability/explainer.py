"""Route explanation engine — generates structured reasoning for route decisions.

Every route must explain:
- Why it was selected
- Why alternatives were rejected
- Risk factors along the path
- Expected bottlenecks and predicted delays
- Accessibility considerations
- Tradeoffs made
"""

from __future__ import annotations

from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import (
    PathResult,
    QualityMetrics,
    RouteExplanation,
)
from app.features.navigation.models.enums import RoutingProfile


class RouteExplainer:
    """Generates structured explanations for computed routes."""

    def __init__(self, graph: NavigationGraph) -> None:
        self._graph = graph

    def explain(
        self,
        result: PathResult,
        metrics: QualityMetrics,
        profile: RoutingProfile,
        alternatives: list[PathResult] | None = None,
    ) -> RouteExplanation:
        """Generate comprehensive explanation for a route selection."""
        why_selected = self._why_selected(result, metrics, profile)
        why_rejected = self._why_rejected(alternatives, metrics)
        risk_factors = self._identify_risk_factors(result)
        bottlenecks = self._identify_bottlenecks(result)
        delays = self._predict_delays(result)
        accessibility_notes = self._accessibility_notes(result, profile)
        tradeoffs = self._identify_tradeoffs(result, metrics, alternatives)

        summary = self._build_summary(result, metrics, profile)

        return RouteExplanation(
            summary=summary,
            why_selected=why_selected,
            why_rejected_alternatives=why_rejected,
            risk_factors=risk_factors,
            expected_bottlenecks=bottlenecks,
            predicted_delays=delays,
            accessibility_notes=accessibility_notes,
            tradeoffs=tradeoffs,
        )

    def _why_selected(
        self,
        result: PathResult,
        metrics: QualityMetrics,
        profile: RoutingProfile,
    ) -> str:
        parts = [
            f"Route graded {metrics.grade} (score {metrics.overall_score:.0%}).",
            f"Travel time: {metrics.travel_time_seconds:.0f}s.",
            f"Distance: {metrics.walking_distance_meters:.0f}m.",
        ]
        if metrics.safety_score > 0.8:
            parts.append("High safety score along path.")
        if metrics.accessibility_score > 0.9:
            parts.append("Fully accessible route.")
        if metrics.crowd_exposure_score < 0.3:
            parts.append("Low crowd exposure.")
        return " ".join(parts)

    def _why_rejected(
        self,
        alternatives: list[PathResult] | None,
        best_metrics: QualityMetrics,
    ) -> list[str]:
        if not alternatives:
            return ["No alternatives evaluated."]
        reasons: list[str] = []
        for i, alt in enumerate(alternatives[:3]):
            if alt.total_time_seconds > best_metrics.travel_time_seconds * 1.3:
                pct = (
                    (alt.total_time_seconds
                     / best_metrics.travel_time_seconds - 1) * 100
                )
                reasons.append(
                    f"Alternative {i + 1}: {pct:.0f}% slower",
                )
            if alt.total_distance_meters > best_metrics.walking_distance_meters * 1.5:
                pct = (
                    (alt.total_distance_meters
                     / best_metrics.walking_distance_meters - 1) * 100
                )
                reasons.append(
                    f"Alternative {i + 1}: {pct:.0f}% longer distance",
                )
        return reasons or ["Alternatives had lower overall utility."]

    def _identify_risk_factors(self, result: PathResult) -> list[str]:
        factors: list[str] = []
        for node_id in result.path:
            node = self._graph.get_node(node_id)
            if node is None:
                continue
            if node.is_occupied and node.max_capacity > 0:
                ratio = node.current_capacity / node.max_capacity
                if ratio > 0.8:
                    factors.append(f"{node.name}: high occupancy ({ratio:.0%})")
        return factors[:5]

    def _identify_bottlenecks(self, result: PathResult) -> list[str]:
        bottlenecks: list[str] = []
        for node_id in result.path:
            node = self._graph.get_node(node_id)
            if node and node.max_capacity > 0:
                ratio = node.current_capacity / node.max_capacity
                if ratio > 0.7:
                    bottlenecks.append(
                        f"{node.name}: {ratio:.0%} capacity",
                    )
        return bottlenecks[:3]

    def _predict_delays(self, result: PathResult) -> list[str]:
        delays: list[str] = []
        if result.total_time_seconds > 300:
            delays.append("Long route: consider alternative destination")
        return delays

    def _accessibility_notes(
        self,
        result: PathResult,
        profile: RoutingProfile,
    ) -> list[str]:
        notes: list[str] = []
        if profile in (RoutingProfile.WHEELCHAIR_USER, RoutingProfile.BLIND_USER):
            for edge_type in result.edges:
                if edge_type == "elevator":
                    notes.append("Route uses elevator")
                    break
            for node_id in result.path:
                node = self._graph.get_node(node_id)
                if node and node.accessibility_level == "partial":
                    notes.append(f"{node.name}: partial accessibility")
        return notes

    def _identify_tradeoffs(
        self,
        result: PathResult,
        metrics: QualityMetrics,
        alternatives: list[PathResult] | None,
    ) -> list[str]:
        tradeoffs: list[str] = []
        if metrics.crowd_exposure_score > 0.5 and metrics.travel_time_seconds < 120:
            tradeoffs.append("Faster route chosen despite higher crowd exposure")
        if metrics.safety_score < 0.7:
            tradeoffs.append("Safety compromised for speed")
        if alternatives:
            tradeoffs.append(
                f"{len(alternatives)} alternative(s) available but not selected",
            )
        return tradeoffs

    def _build_summary(
        self,
        result: PathResult,
        metrics: QualityMetrics,
        profile: RoutingProfile,
    ) -> str:
        return (
            f"{profile.value} route: {metrics.travel_time_seconds:.0f}s, "
            f"{metrics.walking_distance_meters:.0f}m, "
            f"grade {metrics.grade}"
        )
