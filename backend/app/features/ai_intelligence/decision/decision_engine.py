"""Decision engine: orchestrates candidate generation, scoring, and ranking."""

from __future__ import annotations

import logging

from app.features.ai_intelligence.engine.context import RiskBundle
from app.features.ai_intelligence.models.enums import InterventionType, RiskLevel

logger = logging.getLogger(__name__)

RISK_LEVEL_SCORES: dict[str, int] = {
    RiskLevel.GREEN.value: 0,
    RiskLevel.YELLOW.value: 1,
    RiskLevel.ORANGE.value: 2,
    RiskLevel.RED.value: 3,
    RiskLevel.CRITICAL.value: 4,
}

UTILITY_WEIGHTS: dict[str, float] = {
    "risk_reduction": 1.0,
    "confidence": 0.8,
    "resource_cost": 0.6,
    "side_effect_penalty": 0.15,
}

_RISK_CANDIDATE_MAP: dict[int, list[str]] = {
    0: [InterventionType.DO_NOTHING.value],
    1: [
        InterventionType.REDIRECT_VOLUNTEERS.value,
        InterventionType.MULTILINGUAL_ANNOUNCEMENT.value,
    ],
    2: [
        InterventionType.OPEN_SECONDARY_GATE.value,
        InterventionType.DEPLOY_MEDICAL.value,
        InterventionType.INCREASE_SECURITY.value,
    ],
    3: [
        InterventionType.CLOSE_CORRIDOR.value,
        InterventionType.REVERSE_FLOW.value,
        InterventionType.SPLIT_CROWD.value,
    ],
    4: [
        InterventionType.ACCESSIBILITY_PRIORITY_ROUTING.value,
    ],
}

_RESOURCE_COSTS: dict[str, float] = {
    InterventionType.DO_NOTHING.value: 0.0,
    InterventionType.MULTILINGUAL_ANNOUNCEMENT.value: 0.05,
    InterventionType.REDIRECT_VOLUNTEERS.value: 0.20,
    InterventionType.DEPLOY_MEDICAL.value: 0.45,
    InterventionType.INCREASE_SECURITY.value: 0.40,
    InterventionType.OPEN_SECONDARY_GATE.value: 0.35,
    InterventionType.CLOSE_CORRIDOR.value: 0.30,
    InterventionType.REVERSE_FLOW.value: 0.50,
    InterventionType.SPLIT_CROWD.value: 0.55,
    InterventionType.ACCESSIBILITY_PRIORITY_ROUTING.value: 0.30,
}

_BASE_RISK_REDUCTIONS: dict[str, float] = {
    InterventionType.DO_NOTHING.value: 0.0,
    InterventionType.MULTILINGUAL_ANNOUNCEMENT.value: 0.12,
    InterventionType.REDIRECT_VOLUNTEERS.value: 0.22,
    InterventionType.DEPLOY_MEDICAL.value: 0.38,
    InterventionType.INCREASE_SECURITY.value: 0.25,
    InterventionType.OPEN_SECONDARY_GATE.value: 0.30,
    InterventionType.CLOSE_CORRIDOR.value: 0.35,
    InterventionType.REVERSE_FLOW.value: 0.40,
    InterventionType.SPLIT_CROWD.value: 0.45,
    InterventionType.ACCESSIBILITY_PRIORITY_ROUTING.value: 0.20,
}

_BASE_CONFIDENCE: dict[str, float] = {
    InterventionType.DO_NOTHING.value: 1.0,
    InterventionType.MULTILINGUAL_ANNOUNCEMENT.value: 0.70,
    InterventionType.REDIRECT_VOLUNTEERS.value: 0.75,
    InterventionType.DEPLOY_MEDICAL.value: 0.80,
    InterventionType.INCREASE_SECURITY.value: 0.70,
    InterventionType.OPEN_SECONDARY_GATE.value: 0.65,
    InterventionType.CLOSE_CORRIDOR.value: 0.60,
    InterventionType.REVERSE_FLOW.value: 0.55,
    InterventionType.SPLIT_CROWD.value: 0.50,
    InterventionType.ACCESSIBILITY_PRIORITY_ROUTING.value: 0.72,
}


class DecisionEngine:
    """Generates, scores, and ranks candidate interventions."""

    def generate_candidates(
        self, risk: RiskBundle, context: dict,
    ) -> list[dict]:
        """Generate candidate interventions based on current risk profile."""
        risk_idx = RISK_LEVEL_SCORES.get(risk.overall_risk_level, 0)
        candidates: list[str] = [InterventionType.DO_NOTHING.value]
        for level in range(1, risk_idx + 1):
            candidates.extend(_RISK_CANDIDATE_MAP.get(level, []))
        deduped = list(dict.fromkeys(candidates))
        return [
            {
                "intervention_type": it,
                "strategy_params": _default_params(it, context),
                "estimated_risk_reduction": _BASE_RISK_REDUCTIONS.get(it, 0.0),
                "estimated_confidence": _BASE_CONFIDENCE.get(it, 0.5),
                "resource_cost": _RESOURCE_COSTS.get(it, 0.5),
            }
            for it in deduped
        ]

    def score_candidate(
        self, candidate: dict, risk: RiskBundle, context: dict,
    ) -> float:
        """Score a candidate intervention on 0-1 utility scale."""
        risk_reduction = candidate.get("estimated_risk_reduction", 0.0)
        confidence = candidate.get("estimated_confidence", 0.5)
        resource_cost = candidate.get("resource_cost", 0.5)
        risk_level_idx = RISK_LEVEL_SCORES.get(risk.overall_risk_level, 0)
        risk_amplifier = 0.7 + 0.3 * (risk_level_idx / 4.0)
        adjusted_reduction = risk_reduction * risk_amplifier
        side_effects = _estimate_side_effect_count(
            candidate.get("intervention_type", ""),
        )
        penalty = UTILITY_WEIGHTS["side_effect_penalty"] * min(side_effects / 3.0, 1.0)
        utility = (
            UTILITY_WEIGHTS["risk_reduction"] * adjusted_reduction
            + UTILITY_WEIGHTS["confidence"] * confidence
            - UTILITY_WEIGHTS["resource_cost"] * resource_cost
            - penalty
        )
        return max(0.0, min(1.0, utility))

    def rank_candidates(
        self, candidates: list[dict], risk: RiskBundle, context: dict,
    ) -> list[tuple[dict, float]]:
        """Score and rank all candidates. Returns (candidate, score) sorted desc."""
        scored = [
            (c, self.score_candidate(c, risk, context)) for c in candidates
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored


def _default_params(intervention_type: str, context: dict) -> dict:
    zone_id = context.get("zone_id", "")
    if intervention_type == InterventionType.REDIRECT_VOLUNTEERS.value:
        return {"target_zones": [zone_id] if zone_id else []}
    if intervention_type == InterventionType.OPEN_SECONDARY_GATE.value:
        return {"gate_ids": context.get("available_gates", [])}
    if intervention_type == InterventionType.DEPLOY_MEDICAL.value:
        return {"team_count": max(1, context.get("medical_incidents", 1))}
    if intervention_type == InterventionType.INCREASE_SECURITY.value:
        return {"unit_count": max(1, context.get("security_level", 1))}
    if intervention_type == InterventionType.CLOSE_CORRIDOR.value:
        return {"corridor_ids": context.get("high_density_corridors", [])}
    if intervention_type == InterventionType.REVERSE_FLOW.value:
        return {"flow_zones": [zone_id] if zone_id else []}
    if intervention_type == InterventionType.SPLIT_CROWD.value:
        return {"split_ratio": 0.5}
    if intervention_type == InterventionType.MULTILINGUAL_ANNOUNCEMENT.value:
        return {"message_key": "general_advisory"}
    if intervention_type == InterventionType.ACCESSIBILITY_PRIORITY_ROUTING.value:
        return {"priority_level": "high"}
    return {}


def _estimate_side_effect_count(intervention_type: str) -> int:
    side_effect_counts: dict[str, int] = {
        InterventionType.DO_NOTHING.value: 0,
        InterventionType.MULTILINGUAL_ANNOUNCEMENT.value: 0,
        InterventionType.REDIRECT_VOLUNTEERS.value: 1,
        InterventionType.DEPLOY_MEDICAL.value: 1,
        InterventionType.INCREASE_SECURITY.value: 1,
        InterventionType.OPEN_SECONDARY_GATE.value: 2,
        InterventionType.ACCESSIBILITY_PRIORITY_ROUTING.value: 1,
        InterventionType.CLOSE_CORRIDOR.value: 2,
        InterventionType.REVERSE_FLOW.value: 2,
        InterventionType.SPLIT_CROWD.value: 3,
    }
    return side_effect_counts.get(intervention_type, 1)
