"""Stage 5 — Intervention Simulation: generates and simulates candidate interventions."""

from __future__ import annotations

import logging

from app.features.ai_intelligence.engine.context import (
    IntelligenceContext,
    SimulatedIntervention,
)
from app.features.ai_intelligence.models.enums import InterventionType

logger = logging.getLogger(__name__)

RISK_LEVEL_ORDER: dict[str, int] = {
    "green": 0, "yellow": 1, "orange": 2, "red": 3, "critical": 4,
}

BASELINE_RESOURCE_COST: float = 0.0
DO_NOTHING_REDUCTION: float = 0.0
DO_NOTHING_CONFIDENCE: float = 1.0

_RISK_TO_CANDIDATES: dict[int, list[tuple[str, dict]]] = {
    0: [(InterventionType.DO_NOTHING.value, {})],
    1: [
        (InterventionType.DO_NOTHING.value, {}),
        (InterventionType.REDIRECT_VOLUNTEERS.value, {"target_zones": []}),
        (InterventionType.MULTILINGUAL_ANNOUNCEMENT.value, {"message_key": "general_advisory"}),
    ],
    2: [
        (InterventionType.DO_NOTHING.value, {}),
        (InterventionType.REDIRECT_VOLUNTEERS.value, {"target_zones": []}),
        (InterventionType.MULTILINGUAL_ANNOUNCEMENT.value, {"message_key": "general_advisory"}),
        (InterventionType.OPEN_SECONDARY_GATE.value, {"gate_ids": []}),
        (InterventionType.DEPLOY_MEDICAL.value, {"team_count": 1}),
        (InterventionType.INCREASE_SECURITY.value, {"unit_count": 1}),
    ],
    3: [
        (InterventionType.DO_NOTHING.value, {}),
        (InterventionType.REDIRECT_VOLUNTEERS.value, {"target_zones": []}),
        (InterventionType.MULTILINGUAL_ANNOUNCEMENT.value, {"message_key": "crowd_management"}),
        (InterventionType.OPEN_SECONDARY_GATE.value, {"gate_ids": []}),
        (InterventionType.DEPLOY_MEDICAL.value, {"team_count": 2}),
        (InterventionType.INCREASE_SECURITY.value, {"unit_count": 2}),
        (InterventionType.CLOSE_CORRIDOR.value, {"corridor_ids": []}),
        (InterventionType.REVERSE_FLOW.value, {"flow_zones": []}),
        (InterventionType.SPLIT_CROWD.value, {"split_ratio": 0.5}),
    ],
    4: [
        (InterventionType.DO_NOTHING.value, {}),
        (InterventionType.REDIRECT_VOLUNTEERS.value, {"target_zones": []}),
        (InterventionType.MULTILINGUAL_ANNOUNCEMENT.value, {"message_key": "emergency"}),
        (InterventionType.OPEN_SECONDARY_GATE.value, {"gate_ids": []}),
        (InterventionType.DEPLOY_MEDICAL.value, {"team_count": 3}),
        (InterventionType.INCREASE_SECURITY.value, {"unit_count": 3}),
        (InterventionType.CLOSE_CORRIDOR.value, {"corridor_ids": []}),
        (InterventionType.REVERSE_FLOW.value, {"flow_zones": []}),
        (InterventionType.SPLIT_CROWD.value, {"split_ratio": 0.4}),
        (InterventionType.ACCESSIBILITY_PRIORITY_ROUTING.value, {"priority_level": "high"}),
    ],
}

_SIMULATION_MODELS: dict[str, dict[str, float]] = {
    InterventionType.DO_NOTHING.value: {
        "risk_reduction": 0.0, "confidence": 1.0, "resource_cost": 0.0,
    },
    InterventionType.REDIRECT_VOLUNTEERS.value: {
        "risk_reduction": 0.22, "confidence": 0.75, "resource_cost": 0.20,
    },
    InterventionType.MULTILINGUAL_ANNOUNCEMENT.value: {
        "risk_reduction": 0.12, "confidence": 0.70, "resource_cost": 0.05,
    },
    InterventionType.OPEN_SECONDARY_GATE.value: {
        "risk_reduction": 0.30, "confidence": 0.65, "resource_cost": 0.35,
    },
    InterventionType.DEPLOY_MEDICAL.value: {
        "risk_reduction": 0.38, "confidence": 0.80, "resource_cost": 0.45,
    },
    InterventionType.INCREASE_SECURITY.value: {
        "risk_reduction": 0.25, "confidence": 0.70, "resource_cost": 0.40,
    },
    InterventionType.CLOSE_CORRIDOR.value: {
        "risk_reduction": 0.35, "confidence": 0.60, "resource_cost": 0.30,
    },
    InterventionType.REVERSE_FLOW.value: {
        "risk_reduction": 0.40, "confidence": 0.55, "resource_cost": 0.50,
    },
    InterventionType.SPLIT_CROWD.value: {
        "risk_reduction": 0.45, "confidence": 0.50, "resource_cost": 0.55,
    },
    InterventionType.ACCESSIBILITY_PRIORITY_ROUTING.value: {
        "risk_reduction": 0.20, "confidence": 0.72, "resource_cost": 0.30,
    },
}


class Stage5Simulation:
    """Generates candidate interventions and simulates each one's impact."""

    async def execute(self, ctx: IntelligenceContext) -> None:
        risk = ctx.risk
        sit = ctx.situation
        if risk is None or sit is None:
            ctx.interventions = []
            return

        risk_level_idx = RISK_LEVEL_ORDER.get(risk.overall_risk_level, 0)
        candidates = self._generate_candidates(risk_level_idx, risk, sit)
        simulated = [self._simulate(c, risk, sit) for c in candidates]
        simulated.sort(key=lambda s: s.simulated_risk_reduction, reverse=True)

        ctx.interventions = simulated
        logger.debug(
            "Stage 5 complete: %d candidates simulated for risk level %s",
            len(simulated), risk.overall_risk_level,
        )

    @staticmethod
    def _generate_candidates(
        risk_level_idx: int, risk, sit,
    ) -> list[tuple[str, dict]]:
        candidates: list[tuple[str, dict]] = []
        for level in range(risk_level_idx + 1):
            candidates.extend(_RISK_TO_CANDIDATES.get(level, []))
        deduped: dict[str, tuple[str, dict]] = {}
        for intervention_type, params in candidates:
            if intervention_type not in deduped:
                deduped[intervention_type] = (intervention_type, params)
        return list(deduped.values())

    @staticmethod
    def _simulate(
        candidate: tuple[str, dict], risk, sit,
    ) -> SimulatedIntervention:
        intervention_type, strategy_params = candidate
        default = _SIMULATION_MODELS[InterventionType.DO_NOTHING.value]
        model = _SIMULATION_MODELS.get(intervention_type, default)

        base_reduction = model["risk_reduction"]
        risk_modifier = RISK_LEVEL_ORDER.get(risk.overall_risk_level, 0) / 4.0
        adjusted_reduction = base_reduction * (0.7 + 0.3 * risk_modifier)
        adjusted_reduction = min(adjusted_reduction, risk.overall_risk_score)

        confidence = model["confidence"] * risk.confidence
        resource_cost = model["resource_cost"]

        risk_before = risk.overall_risk_level
        post_score = max(0.0, risk.overall_risk_score - adjusted_reduction)
        risk_after = _score_to_level_name(post_score)

        side_effects = _compute_side_effects(intervention_type, strategy_params)
        eval_factors = [
            {"factor": "risk_reduction", "value": round(adjusted_reduction, 4)},
            {"factor": "confidence", "value": round(confidence, 4)},
            {"factor": "resource_cost", "value": round(resource_cost, 4)},
            {"factor": "side_effect_count", "value": len(side_effects)},
        ]

        return SimulatedIntervention(
            intervention_type=intervention_type,
            strategy_params=strategy_params,
            simulated_risk_reduction=round(adjusted_reduction, 4),
            simulated_confidence=round(confidence, 4),
            risk_before=risk_before,
            risk_after=risk_after,
            evaluation_factors=eval_factors,
            side_effects=side_effects,
            resource_cost=round(resource_cost, 4),
        )


def _score_to_level_name(score: float) -> str:
    if score >= 0.90:
        return "critical"
    if score >= 0.75:
        return "red"
    if score >= 0.50:
        return "orange"
    if score >= 0.25:
        return "yellow"
    return "green"


def _compute_side_effects(intervention_type: str, params: dict) -> list[str]:
    effects: list[str] = []
    if intervention_type == InterventionType.CLOSE_CORRIDOR.value:
        effects.append("Reduces available routes for nearby spectators")
        effects.append("May increase density in adjacent corridors")
    elif intervention_type == InterventionType.REVERSE_FLOW.value:
        effects.append("Temporary confusion for spectators in affected zone")
        effects.append("Requires volunteer support to guide reversed flow")
    elif intervention_type == InterventionType.SPLIT_CROWD.value:
        effects.append("Splits existing flow — may cause short-term congestion at split points")
    elif intervention_type == InterventionType.OPEN_SECONDARY_GATE.value:
        effects.append("Requires gate staff reassignment from primary entrances")
    elif intervention_type == InterventionType.DEPLOY_MEDICAL.value:
        effects.append("Reduces medical coverage in other zones during deployment")
    elif intervention_type == InterventionType.INCREASE_SECURITY.value:
        effects.append("Reduces security presence elsewhere in the venue")
    elif intervention_type == InterventionType.ACCESSIBILITY_PRIORITY_ROUTING.value:
        effects.append("Priority routing may delay non-accessible spectators")
    return effects
