"""Intervention simulator: models the effect of each intervention type on venue risk."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from app.features.ai_intelligence.models.enums import InterventionType, RiskLevel

logger = logging.getLogger(__name__)

RISK_SCORE_MAP: dict[str, float] = {
    RiskLevel.GREEN.value: 0.10,
    RiskLevel.YELLOW.value: 0.35,
    RiskLevel.ORANGE.value: 0.60,
    RiskLevel.RED.value: 0.82,
    RiskLevel.CRITICAL.value: 0.95,
}

RISK_ORDER: list[str] = [
    RiskLevel.GREEN.value,
    RiskLevel.YELLOW.value,
    RiskLevel.ORANGE.value,
    RiskLevel.RED.value,
    RiskLevel.CRITICAL.value,
]

DECAY_PER_SECOND: float = 0.0005
TIME_HORIZON_SCALE: float = 0.85


@dataclass(slots=True)
class SimulatedResult:
    """Outcome of a single intervention simulation."""

    risk_before: str
    risk_after: str
    risk_reduction: float
    confidence: float
    side_effects: list[str] = field(default_factory=list)
    resource_cost: float = 0.0
    evaluation_factors: list[dict] = field(default_factory=list)


class InterventionSimulator:
    """Simulates the effect of an intervention on the current venue state.

    Each intervention type has a dedicated simulation model that
    computes risk_before → risk_after, confidence, side effects,
    and resource cost.
    """

    def simulate(
        self,
        intervention_type: str,
        strategy_params: dict,
        current_state: dict,
        time_horizon_seconds: int,
    ) -> SimulatedResult:
        """Simulate the effect of an intervention."""
        risk_level = current_state.get("risk_level", RiskLevel.GREEN.value)
        base_score = RISK_SCORE_MAP.get(risk_level, 0.1)
        time_factor = 1.0 - math.exp(-DECAY_PER_SECOND * time_horizon_seconds)
        adjusted_time = time_factor * TIME_HORIZON_SCALE

        handler = self._get_handler(intervention_type)
        sim_output = handler(strategy_params, current_state, adjusted_time)

        post_score = max(0.0, base_score - sim_output["reduction"])
        risk_after = _score_to_level(post_score)
        reduction = base_score - post_score

        return SimulatedResult(
            risk_before=risk_level,
            risk_after=risk_after,
            risk_reduction=round(reduction, 4),
            confidence=round(sim_output["confidence"], 4),
            side_effects=sim_output.get("side_effects", []),
            resource_cost=round(sim_output.get("resource_cost", 0.0), 4),
            evaluation_factors=[
                {"factor": "reduction", "value": round(reduction, 4)},
                {"factor": "confidence", "value": round(sim_output["confidence"], 4)},
                {"factor": "time_factor", "value": round(adjusted_time, 4)},
            ],
        )

    def _get_handler(self, intervention_type: str):
        handlers = {
            InterventionType.DO_NOTHING.value: self._simulate_do_nothing,
            InterventionType.REDIRECT_VOLUNTEERS.value: self._simulate_redirect_volunteers,
            InterventionType.OPEN_SECONDARY_GATE.value: self._simulate_open_secondary_gate,
            InterventionType.DEPLOY_MEDICAL.value: self._simulate_deploy_medical,
            InterventionType.CLOSE_CORRIDOR.value: self._simulate_close_corridor,
            InterventionType.REVERSE_FLOW.value: self._simulate_reverse_flow,
            InterventionType.SPLIT_CROWD.value: self._simulate_split_crowd,
            InterventionType.MULTILINGUAL_ANNOUNCEMENT.value: (
                self._simulate_multilingual_announcement
            ),
            InterventionType.INCREASE_SECURITY.value: (
                self._simulate_increase_security
            ),
            InterventionType.ACCESSIBILITY_PRIORITY_ROUTING.value: (
                self._simulate_accessibility_routing
            ),
        }
        return handlers.get(intervention_type, self._simulate_do_nothing)

    @staticmethod
    def _simulate_do_nothing(params, state, time_factor):
        return {"reduction": 0.0, "confidence": 1.0, "side_effects": [], "resource_cost": 0.0}

    @staticmethod
    def _simulate_redirect_volunteers(params, state, time_factor):
        target_count = max(len(params.get("target_zones", [])), 1)
        base = 0.15 + 0.05 * min(target_count, 3)
        reduction = base * (0.7 + 0.3 * time_factor)
        return {
            "reduction": reduction,
            "confidence": 0.75,
            "side_effects": ["Reduced volunteer coverage in source zones"],
            "resource_cost": 0.20,
        }

    @staticmethod
    def _simulate_open_secondary_gate(params, state, time_factor):
        gate_count = max(len(params.get("gate_ids", [])), 1)
        base = 0.20 + 0.05 * min(gate_count, 4)
        reduction = base * (0.6 + 0.4 * time_factor)
        return {
            "reduction": reduction,
            "confidence": 0.65,
            "side_effects": [
                "Requires gate staff reassignment",
                "May create new congestion at secondary gate",
            ],
            "resource_cost": 0.35,
        }

    @staticmethod
    def _simulate_deploy_medical(params, state, time_factor):
        team_count = max(params.get("team_count", 1), 1)
        base = 0.25 + 0.05 * min(team_count, 3)
        reduction = base * (0.8 + 0.2 * time_factor)
        return {
            "reduction": reduction,
            "confidence": 0.80,
            "side_effects": ["Reduced medical coverage in other zones"],
            "resource_cost": 0.45,
        }

    @staticmethod
    def _simulate_close_corridor(params, state, time_factor):
        corridor_count = max(len(params.get("corridor_ids", [])), 1)
        base = 0.25 + 0.05 * min(corridor_count, 3)
        reduction = base * (0.6 + 0.4 * time_factor)
        return {
            "reduction": reduction,
            "confidence": 0.60,
            "side_effects": [
                "Reduces available routes for nearby spectators",
                "May increase density in adjacent corridors",
            ],
            "resource_cost": 0.30,
        }

    @staticmethod
    def _simulate_reverse_flow(params, state, time_factor):
        zone_count = max(len(params.get("flow_zones", [])), 1)
        base = 0.30 + 0.05 * min(zone_count, 2)
        reduction = base * (0.5 + 0.5 * time_factor)
        return {
            "reduction": reduction,
            "confidence": 0.55,
            "side_effects": [
                "Temporary confusion for spectators in affected zone",
                "Requires volunteer support to guide reversed flow",
            ],
            "resource_cost": 0.50,
        }

    @staticmethod
    def _simulate_split_crowd(params, state, time_factor):
        split_ratio = params.get("split_ratio", 0.5)
        split_ratio = max(0.1, min(0.9, split_ratio))
        base = 0.30 + 0.15 * split_ratio
        reduction = base * (0.5 + 0.5 * time_factor)
        return {
            "reduction": reduction,
            "confidence": 0.50,
            "side_effects": [
                "Splits existing flow",
                "May cause short-term congestion at split points",
                "Complex to execute safely",
            ],
            "resource_cost": 0.55,
        }

    @staticmethod
    def _simulate_multilingual_announcement(params, state, time_factor):
        message_risk = 0.08
        modifier = 1.5 if params.get("message_key") == "emergency" else 1.0
        reduction = message_risk * modifier * (0.6 + 0.4 * time_factor)
        return {
            "reduction": reduction,
            "confidence": 0.70,
            "side_effects": [],
            "resource_cost": 0.05,
        }

    @staticmethod
    def _simulate_increase_security(params, state, time_factor):
        unit_count = max(params.get("unit_count", 1), 1)
        base = 0.18 + 0.04 * min(unit_count, 3)
        reduction = base * (0.7 + 0.3 * time_factor)
        return {
            "reduction": reduction,
            "confidence": 0.70,
            "side_effects": ["Reduces security presence elsewhere in the venue"],
            "resource_cost": 0.40,
        }

    @staticmethod
    def _simulate_accessibility_routing(params, state, time_factor):
        priority_map = {"low": 0.10, "medium": 0.15, "high": 0.20}
        priority = params.get("priority_level", "medium")
        base = priority_map.get(priority, 0.15)
        reduction = base * (0.7 + 0.3 * time_factor)
        return {
            "reduction": reduction,
            "confidence": 0.72,
            "side_effects": ["Priority routing may delay non-accessible spectators"],
            "resource_cost": 0.30,
        }


def _score_to_level(score: float) -> str:
    """Map continuous risk score to discrete risk level name."""
    result = RiskLevel.GREEN.value
    thresholds = [
        (0.25, RiskLevel.YELLOW.value),
        (0.50, RiskLevel.ORANGE.value),
        (0.75, RiskLevel.RED.value),
        (0.90, RiskLevel.CRITICAL.value),
    ]
    for threshold, level in thresholds:
        if score >= threshold:
            result = level
    return result
