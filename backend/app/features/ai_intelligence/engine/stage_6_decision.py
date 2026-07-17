"""Stage 6 — Decision Selection: scores simulated interventions and selects the best one."""

from __future__ import annotations

import logging

from app.features.ai_intelligence.engine.context import (
    IntelligenceContext,
    SelectedDecision,
)

logger = logging.getLogger(__name__)

UTILITY_RISK_WEIGHT: float = 1.0
UTILITY_CONFIDENCE_WEIGHT: float = 0.8
UTILITY_COST_WEIGHT: float = 0.6
UTILITY_SIDE_EFFECT_PENALTY: float = 0.15
UTILITY_RESOURCE_THRESHOLD: float = 0.7

_RESOURCE_LABELS: dict[str, str] = {
    "do_nothing": "none",
    "multilingual_announcement": "low",
    "redirect_volunteers": "low",
    "deploy_medical": "medium",
    "increase_security": "medium",
    "open_secondary_gate": "medium",
    "close_corridor": "medium",
    "reverse_flow": "high",
    "split_crowd": "high",
    "accessibility_priority_routing": "medium",
}


class Stage6Decision:
    """Selects the highest-utility intervention from simulated candidates."""

    async def execute(self, ctx: IntelligenceContext) -> None:
        candidates = ctx.interventions
        risk = ctx.risk

        if not candidates or risk is None:
            ctx.decision = self._default_decision()
            return

        scored = [
            (c, self._compute_utility(c)) for c in candidates
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)

        best, best_utility = scored[0]
        rejected = self._build_rejected(scored[1:], best)

        reasoning = {
            "utility_score": round(best_utility, 4),
            "utility_weights": {
                "risk_weight": UTILITY_RISK_WEIGHT,
                "confidence_weight": UTILITY_CONFIDENCE_WEIGHT,
                "cost_weight": UTILITY_COST_WEIGHT,
                "side_effect_penalty": UTILITY_SIDE_EFFECT_PENALTY,
            },
            "risk_at_decision": risk.overall_risk_level,
            "total_candidates_evaluated": len(candidates),
            "factors": best.evaluation_factors,
        }

        ctx.decision = SelectedDecision(
            intervention_type=best.intervention_type,
            intervention_params=best.strategy_params,
            confidence=best.simulated_confidence,
            risk_reduction=best.simulated_risk_reduction,
            reasoning=reasoning,
            alternatives_rejected=rejected,
            resource_requirement=_RESOURCE_LABELS.get(
                best.intervention_type, "unknown",
            ),
        )
        logger.debug(
            "Stage 6 complete: selected=%s utility=%.3f confidence=%.3f",
            best.intervention_type, best_utility, best.simulated_confidence,
        )

    @staticmethod
    def _compute_utility(candidate) -> float:
        risk_term = UTILITY_RISK_WEIGHT * candidate.simulated_risk_reduction
        confidence_term = UTILITY_CONFIDENCE_WEIGHT * candidate.simulated_confidence
        cost_term = UTILITY_COST_WEIGHT * candidate.resource_cost
        side_effect_count = len(candidate.side_effects)
        penalty = UTILITY_SIDE_EFFECT_PENALTY * min(side_effect_count / 3.0, 1.0)
        utility = risk_term + confidence_term - cost_term - penalty
        return max(0.0, min(1.0, utility))

    @staticmethod
    def _build_rejected(
        remaining: list[tuple], best_type: str,
    ) -> list[dict]:
        rejected: list[dict] = []
        for candidate, utility in remaining:
            rejection_reason = "lower_utility_score"
            if candidate.resource_cost > UTILITY_RESOURCE_THRESHOLD:
                rejection_reason = "high_resource_cost"
            elif candidate.simulated_confidence < 0.3:
                rejection_reason = "low_confidence"
            elif len(candidate.side_effects) > 3:
                rejection_reason = "excessive_side_effects"
            rejected.append({
                "intervention_type": candidate.intervention_type,
                "utility": round(utility, 4),
                "risk_reduction": round(candidate.simulated_risk_reduction, 4),
                "confidence": round(candidate.simulated_confidence, 4),
                "reason": rejection_reason,
            })
        return rejected

    @staticmethod
    def _default_decision() -> SelectedDecision:
        return SelectedDecision(
            intervention_type="do_nothing",
            intervention_params={},
            confidence=1.0,
            risk_reduction=0.0,
            reasoning={"status": "no_candidates"},
            alternatives_rejected=[],
            resource_requirement="none",
        )
