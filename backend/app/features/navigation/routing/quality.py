"""Route quality engine — multi-metric scoring and grading.

Every computed route receives a quality assessment with:
- Travel time, distance, safety, accessibility, crowd exposure
- Energy cost, route reliability, confidence
- Overall score and letter grade
"""

from __future__ import annotations

from app.features.navigation.graph.graph_manager import NavigationGraph
from app.features.navigation.graph.models import (
    PathResult,
    QualityMetrics,
    WeightContext,
)
from app.features.navigation.models.enums import ObjectiveWeight, RoutingProfile
from app.features.navigation.routing.profile import get_profile_config

GRADE_THRESHOLDS = [
    (0.9, "A+"),
    (0.85, "A"),
    (0.8, "A-"),
    (0.75, "B+"),
    (0.7, "B"),
    (0.65, "B-"),
    (0.6, "C+"),
    (0.55, "C"),
    (0.5, "C-"),
    (0.4, "D"),
    (0.0, "F"),
]


class RouteQualityEngine:
    """Evaluates route quality across multiple dimensions."""

    def __init__(self, graph: NavigationGraph) -> None:
        self._graph = graph

    def assess(
        self,
        result: PathResult,
        profile: RoutingProfile,
        ctx: WeightContext | None = None,
    ) -> QualityMetrics:
        """Compute multi-metric quality assessment for a route."""
        config = get_profile_config(profile)
        weight_ctx = ctx or WeightContext()

        safety_score = self._compute_safety(result, weight_ctx)
        accessibility_score = self._compute_accessibility(result)
        crowd_exposure = self._compute_crowd_exposure(result, weight_ctx)
        risk_score = self._compute_risk(result, weight_ctx)
        energy_cost = self._compute_energy_cost(result)
        reliability = self._compute_reliability(result)
        confidence = result.confidence if result.confidence < 1.0 else reliability

        weights = config.objective_weights
        overall = self._weighted_overall(
            result, weights, safety_score, accessibility_score,
            crowd_exposure, risk_score, energy_cost, reliability,
        )
        grade = self._score_to_grade(overall)

        return QualityMetrics(
            travel_time_seconds=result.total_time_seconds,
            walking_distance_meters=result.total_distance_meters,
            safety_score=safety_score,
            accessibility_score=accessibility_score,
            crowd_exposure_score=crowd_exposure,
            risk_score=risk_score,
            energy_cost=energy_cost,
            route_reliability=reliability,
            confidence=confidence,
            overall_score=overall,
            grade=grade,
        )

    def _compute_safety(
        self,
        result: PathResult,
        ctx: WeightContext,
    ) -> float:
        score = 1.0
        if ctx.emergency_active:
            score *= 0.3
        if ctx.risk_score > 0.7:
            score *= 0.5
        elif ctx.risk_score > 0.4:
            score *= 0.8
        if ctx.medical_incident_nearby:
            score *= 0.7
        for node_id in result.path:
            node = self._graph.get_node(node_id)
            if node and node.accessibility_level == "none":
                score *= 0.9
        return max(0.0, min(1.0, score))

    def _compute_accessibility(self, result: PathResult) -> float:
        if not result.path:
            return 1.0
        accessible_count = 0
        for node_id in result.path:
            node = self._graph.get_node(node_id)
            if node and node.accessibility_level != "none":
                accessible_count += 1
        return accessible_count / len(result.path) if result.path else 1.0

    def _compute_crowd_exposure(
        self,
        result: PathResult,
        ctx: WeightContext,
    ) -> float:
        return min(1.0, ctx.crowd_density + ctx.predicted_congestion)

    def _compute_risk(
        self,
        result: PathResult,
        ctx: WeightContext,
    ) -> float:
        return min(1.0, ctx.risk_score)

    def _compute_energy_cost(self, result: PathResult) -> float:
        distance_factor = result.total_distance_meters / 1000.0
        floor_changes = sum(
            1 for e in result.edges
            if e in ("stairs", "escalator", "ramp")
        )
        return distance_factor + floor_changes * 0.1

    def _compute_reliability(self, result: PathResult) -> float:
        score = 1.0
        if result.nodes_visited > 1000:
            score *= 0.95
        if result.computation_ms > 50:
            score *= 0.9
        return max(0.0, min(1.0, score))

    def _weighted_overall(
        self,
        result: PathResult,
        weights: dict[ObjectiveWeight, float],
        safety: float,
        accessibility: float,
        crowd: float,
        risk: float,
        energy: float,
        reliability: float,
    ) -> float:
        time_score = max(0, 1.0 - result.total_time_seconds / 600.0)
        dist_score = max(0, 1.0 - result.total_distance_meters / 2000.0)

        score = (
            time_score * weights.get("travel_time", 0.3)
            + safety * weights.get("safety", 0.2)
            + accessibility * weights.get("accessibility", 0.1)
            + (1.0 - crowd) * weights.get("crowd_exposure", 0.1)
            + dist_score * weights.get("walking_distance", 0.1)
            + (1.0 - risk) * weights.get("risk", 0.05)
            + reliability * weights.get("route_reliability", 0.05)
        )
        return max(0.0, min(1.0, score))

    @staticmethod
    def _score_to_grade(score: float) -> str:
        for threshold, grade in GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"
