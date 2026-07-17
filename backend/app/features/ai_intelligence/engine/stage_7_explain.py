"""Stage 7 — Explainable AI: generates structured explanations for the selected decision."""

from __future__ import annotations

import logging

from app.features.ai_intelligence.engine.context import (
    IntelligenceContext,
    IntelligenceOutput,
)
from app.features.ai_intelligence.explainability.explainability_engine import (
    ExplainabilityEngine,
)
from app.features.ai_intelligence.knowledge.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

MAX_KNOWLEDGE_ENTRIES: int = 5
BRIEFING_MAX_CHARS: int = 280


class Stage7Explain:
    """Builds human-readable and machine-structured explanations for decisions."""

    def __init__(
        self,
        explainability_engine: ExplainabilityEngine,
        knowledge_base: KnowledgeBase,
    ) -> None:
        self._xai = explainability_engine
        self._kb = knowledge_base

    async def execute(self, ctx: IntelligenceContext) -> None:
        decision = ctx.decision
        risk = ctx.risk
        if decision is None:
            ctx.intelligence = self._empty_output()
            return

        decision_dict = self._decision_to_dict(decision, risk)
        alternatives = decision.alternatives_rejected
        context_dict = self._build_context(ctx)

        explanation = self._xai.explain_decision(decision_dict, alternatives, context_dict)
        volunteer_briefing = self._xai.format_volunteer_briefing(explanation)
        knowledge = await self._retrieve_knowledge(ctx)

        evidence = list(explanation.evidence)
        for entry in knowledge:
            evidence.append({
                "source": "knowledge_base",
                "entry_id": entry.id,
                "title": entry.title,
                "relevance": entry.relevance_score,
            })

        contributing = list(explanation.contributing_factors)
        if risk:
            top_risk_factors = sorted(
                risk.risk_factors.items(), key=lambda kv: kv[1], reverse=True,
            )[:3]
            for factor_name, factor_value in top_risk_factors:
                contributing.append({
                    "factor": factor_name,
                    "risk_value": factor_value,
                    "source": "risk_engine",
                })

        truncated_briefing = _truncate_briefing(volunteer_briefing)

        ctx.intelligence = IntelligenceOutput(
            explanation={
                "summary": explanation.summary,
                "reason": explanation.reason,
                "confidence": explanation.confidence,
                "expected_outcome": explanation.expected_outcome,
                "tradeoffs": explanation.tradeoffs,
                "alternatives_considered": explanation.alternatives_considered,
            },
            volunteer_briefing=truncated_briefing,
            evidence=evidence[:10],
            contributing_factors=contributing[:5],
        )
        logger.debug(
            "Stage 7 complete: briefing_len=%d evidence=%d factors=%d",
            len(truncated_briefing), len(evidence), len(contributing),
        )

    @staticmethod
    def _decision_to_dict(decision, risk) -> dict:
        return {
            "intervention_type": decision.intervention_type,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "expected_outcome": {
                "risk_reduction": decision.risk_reduction,
                "risk_level_before": risk.overall_risk_level if risk else "unknown",
                "description": f"Reduce risk via {decision.intervention_type}",
            },
        }

    @staticmethod
    def _build_context(ctx) -> dict:
        context: dict = {"venue_id": ctx.venue_id, "zone_id": ctx.zone_id}
        if ctx.situation:
            context["match_phase"] = ctx.situation.match_phase
            context["density"] = ctx.situation.current_density
        if ctx.risk:
            context["risk_level"] = ctx.risk.overall_risk_level
        if ctx.behaviour:
            context["movement_pattern"] = ctx.behaviour.movement_pattern
        return context

    async def _retrieve_knowledge(self, ctx) -> list:
        context_dict: dict = {"venue_id": ctx.venue_id}
        if ctx.situation:
            context_dict["match_phase"] = ctx.situation.match_phase
        risk_level = ctx.risk.overall_risk_level if ctx.risk else "green"
        try:
            guidelines = await self._kb.retrieve_safety_guidelines(context_dict)
            sops = await self._kb.retrieve_emergency_sops(risk_level, context_dict)
            all_entries = guidelines + sops
            all_entries.sort(key=lambda e: e.relevance_score, reverse=True)
            return all_entries[:MAX_KNOWLEDGE_ENTRIES]
        except Exception:
            logger.exception("Knowledge retrieval failed in Stage 7")
            return []

    @staticmethod
    def _empty_output() -> IntelligenceOutput:
        return IntelligenceOutput(
            explanation={"summary": "No decision to explain"},
            volunteer_briefing="No action required",
            evidence=[],
            contributing_factors=[],
        )


def _truncate_briefing(text: str) -> str:
    if len(text) <= BRIEFING_MAX_CHARS:
        return text
    truncated = text[: BRIEFING_MAX_CHARS - 3].rsplit(" ", 1)[0]
    return truncated + "..."
