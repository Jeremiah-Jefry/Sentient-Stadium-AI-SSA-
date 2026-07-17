"""Stage 2 — Crowd Behaviour Analysis: classifies movement patterns and detects anomalies."""

from __future__ import annotations

import logging

from app.features.ai_intelligence.context.spatial_reasoning import SpatialReasoner
from app.features.ai_intelligence.engine.context import (
    BehaviourAnalysis,
    IntelligenceContext,
)

logger = logging.getLogger(__name__)

NORMAL_FLOW_HEALTH_MIN: float = 0.6
SURGE_DENSITY_RATIO: float = 0.85
STAGNATION_FLOW_RATIO: float = 0.15
PANIC_THRESHOLD: float = 0.90
ANOMALY_ZSCORE_MIN: float = 2.0
HISTORY_WINDOW: int = 10


class Stage2Behaviour:
    """Analyses crowd movement patterns, flow health, and bottleneck risk."""

    def __init__(self, spatial_reasoner: SpatialReasoner) -> None:
        self._spatial = spatial_reasoner

    async def execute(self, ctx: IntelligenceContext) -> None:
        sit = ctx.situation
        if sit is None:
            ctx.behaviour = self._empty_analysis()
            return

        modifiers = sit.behavior_modifiers
        pattern = self._classify_pattern(sit, modifiers)
        flow_health = self._compute_flow_health(sit)
        stability = self._compute_stability(sit, modifiers)
        bottleneck_risk = self._compute_bottleneck_risk(sit)
        anomalies = self._detect_anomalies(sit, modifiers)
        graph_impacts = self._assess_zone_graph(sit)

        ctx.behaviour = BehaviourAnalysis(
            movement_pattern=pattern,
            flow_health=round(flow_health, 4),
            crowd_stability=round(stability, 4),
            bottleneck_risk=round(bottleneck_risk, 4),
            anomalies=anomalies,
            zone_graph_impacts=graph_impacts,
        )
        logger.debug(
            "Stage 2 complete: pattern=%s flow=%.3f stability=%.3f bottleneck=%.3f",
            pattern, flow_health, stability, bottleneck_risk,
        )

    def _classify_pattern(self, sit, modifiers: dict) -> str:
        density = sit.current_density
        flow = sit.flow_rate
        surge_mod = modifiers.get("density_surge", 0.0)
        intensity = modifiers.get("movement_intensity", 0.5)

        if density > PANIC_THRESHOLD and intensity > 0.8:
            return "panic"
        if density > SURGE_DENSITY_RATIO or surge_mod > 0.6:
            return "surge"
        if flow < STAGNATION_FLOW_RATIO and density > 0.4:
            return "stagnation"
        if flow < 0.0 and abs(flow) > 0.3:
            return "reverse"
        return "normal"

    @staticmethod
    def _compute_flow_health(sit) -> float:
        expected = max(sit.occupancy_percent / 100.0, 0.01)
        actual = max(sit.flow_rate, 0.0)
        if expected <= 0:
            return 0.0
        ratio = min(actual / expected, 2.0)
        health = 1.0 - abs(1.0 - ratio) * 0.5
        return max(0.0, min(1.0, health))

    @staticmethod
    def _compute_stability(sit, modifiers: dict) -> float:
        patience = modifiers.get("patience_factor", 0.5)
        density_stability = 1.0 - min(sit.current_density, 1.0)
        sensor_factor = min(sit.active_sensors / max(sit.active_sensors + 5, 1), 1.0)
        stability = 0.4 * patience + 0.35 * density_stability + 0.25 * sensor_factor
        return max(0.0, min(1.0, stability))

    def _compute_bottleneck_risk(self, sit) -> float:
        density_risk = min(sit.current_density * sit.occupancy_percent / 100.0, 1.0)
        flow_penalty = max(0.0, 1.0 - abs(sit.flow_rate))
        recent_pressure = min(len(sit.recent_events) / 10.0, 1.0)
        risk = 0.45 * density_risk + 0.30 * flow_penalty + 0.25 * recent_pressure
        return max(0.0, min(1.0, risk))

    @staticmethod
    def _detect_anomalies(sit, modifiers: dict) -> list[dict]:
        anomalies: list[dict] = []
        density = sit.current_density
        occupancy = sit.occupancy_percent / 100.0

        if density > SURGE_DENSITY_RATIO:
            anomalies.append({
                "type": "high_density",
                "severity": round(min(density, 1.0), 4),
                "description": f"Density {density:.2f} exceeds surge threshold",
            })
        if sit.flow_rate < -0.3:
            anomalies.append({
                "type": "reverse_flow",
                "severity": round(min(abs(sit.flow_rate), 1.0), 4),
                "description": "Negative flow rate indicates crowd reversal",
            })
        if sit.active_sensors == 0:
            anomalies.append({
                "type": "sensor_outage",
                "severity": 1.0,
                "description": "Zero active sensors in zone — blind spot",
            })
        if modifiers.get("security_alertness", 0.5) > 0.7:
            anomalies.append({
                "type": "elevated_security",
                "severity": round(modifiers["security_alertness"], 4),
                "description": "Match context demands heightened security",
            })
        if occupancy > 0.9 and modifiers.get("exit_demand", 0.0) > 0.5:
            anomalies.append({
                "type": "exit_pressure",
                "severity": round(occupancy * modifiers["exit_demand"], 4),
                "description": "High occupancy with elevated exit demand",
            })
        return anomalies

    def _assess_zone_graph(self, sit) -> list[dict]:
        impacts: list[dict] = []
        if not sit.zone_id:
            return impacts
        neighbor_influence = self._spatial.compute_neighbor_influence(sit.zone_id)
        if neighbor_influence > 0.3:
            impacts.append({
                "zone_id": sit.zone_id,
                "neighbor_influence": round(neighbor_influence, 4),
                "description": "Neighboring zones elevating local risk",
            })
        evacuation_eff = self._spatial.get_evacuation_efficiency(sit.zone_id)
        if evacuation_eff < 0.4:
            impacts.append({
                "zone_id": sit.zone_id,
                "evacuation_efficiency": round(evacuation_eff, 4),
                "description": "Low evacuation efficiency detected",
            })
        return impacts

    @staticmethod
    def _empty_analysis() -> BehaviourAnalysis:
        return BehaviourAnalysis(
            movement_pattern="unknown",
            flow_health=0.0,
            crowd_stability=0.0,
            bottleneck_risk=0.0,
            anomalies=[],
            zone_graph_impacts=[],
        )
