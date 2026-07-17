"""Stage 8 — Publish Recommendation as a publishable event."""

from __future__ import annotations

import logging
import uuid

from app.features.ai_intelligence.engine.context import IntelligenceContext

logger = logging.getLogger(__name__)

PUBLISHED_EVENT_CATEGORY: str = "intelligence"
PUBLISHED_EVENT_TYPE: str = "recommendation"
PUBLISHED_PRODUCER: str = "ai_intelligence_pipeline"
PUBLISHED_PRIORITY_NORMAL: str = "normal"
PUBLISHED_PRIORITY_HIGH: str = "high"
PUBLISHED_PRIORITY_CRITICAL: str = "critical"


class Stage8Publish:
    """Formats the IntelligenceContext as a publishable event payload.

    Actual bus publishing is delegated to the service layer — this stage
    prepares the payload and marks the context as published.
    """

    async def execute(self, ctx: IntelligenceContext) -> None:
        payload = self._build_payload(ctx)
        ctx.published = True
        ctx._publish_payload = payload  # type: ignore[attr-defined]
        logger.debug(
            "Stage 8 complete: event_type=%s priority=%s venue=%s",
            PUBLISHED_EVENT_TYPE,
            payload.get("priority", PUBLISHED_PRIORITY_NORMAL),
            ctx.venue_id,
        )

    def _build_payload(self, ctx: IntelligenceContext) -> dict:
        decision = ctx.decision
        risk = ctx.risk
        intelligence = ctx.intelligence

        priority = self._determine_priority(risk)

        payload: dict = {
            "event_id": str(uuid.uuid4()),
            "category": PUBLISHED_EVENT_CATEGORY,
            "event_type": PUBLISHED_EVENT_TYPE,
            "venue_id": ctx.venue_id,
            "zone_id": ctx.zone_id,
            "priority": priority,
            "producer": PUBLISHED_PRODUCER,
            "recommendation": self._format_recommendation(decision),
            "risk_summary": self._format_risk_summary(risk),
            "explanation": intelligence.explanation if intelligence else {},
            "volunteer_briefing": intelligence.volunteer_briefing if intelligence else "",
            "evidence": intelligence.evidence if intelligence else [],
            "contributing_factors": intelligence.contributing_factors if intelligence else [],
            "pipeline_metadata": {
                "stage_timings_ms": dict(ctx.stage_timings),
                "total_errors": len(ctx.errors),
                "published": True,
            },
        }
        return payload

    @staticmethod
    def _determine_priority(risk) -> str:
        if risk is None:
            return PUBLISHED_PRIORITY_NORMAL
        level = risk.overall_risk_level
        if level in ("critical", "red"):
            return PUBLISHED_PRIORITY_CRITICAL
        if level in ("orange", "yellow"):
            return PUBLISHED_PRIORITY_HIGH
        return PUBLISHED_PRIORITY_NORMAL

    @staticmethod
    def _format_recommendation(decision) -> dict:
        if decision is None:
            return {"intervention_type": "none", "status": "no_recommendation"}
        return {
            "intervention_type": decision.intervention_type,
            "intervention_params": decision.intervention_params,
            "confidence": decision.confidence,
            "risk_reduction": decision.risk_reduction,
            "resource_requirement": decision.resource_requirement,
            "reasoning": decision.reasoning,
        }

    @staticmethod
    def _format_risk_summary(risk) -> dict:
        if risk is None:
            return {"level": "green", "score": 0.0}
        return {
            "level": risk.overall_risk_level,
            "score": risk.overall_risk_score,
            "domain_risks": risk.domain_risks,
            "confidence": risk.confidence,
        }
