"""Intelligence persistence — DB writes and event publishing for intelligence pipeline."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.features.ai_intelligence.engine.context import IntelligenceContext
from app.features.ai_intelligence.models.decision import DecisionHistory
from app.features.ai_intelligence.models.enums import DecisionStatus, RiskLevel
from app.features.ai_intelligence.models.prediction import PredictionStore
from app.features.ai_intelligence.models.risk_history import RiskHistory
from app.features.ai_intelligence.repositories.decision_repository import DecisionRepository
from app.features.ai_intelligence.repositories.prediction_repository import PredictionRepository
from app.features.ai_intelligence.repositories.risk_repository import RiskRepository
from app.features.event_streaming.engine.event_bus import EventBus
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)

INTELLIGENCE_EVENT_CATEGORY = "intelligence"


def classify_risk(score: float) -> str:
    """Map a risk score to a RiskLevel string."""
    if score >= 0.8:
        return RiskLevel.CRITICAL.value
    if score >= 0.6:
        return RiskLevel.RED.value
    if score >= 0.4:
        return RiskLevel.ORANGE.value
    if score >= 0.2:
        return RiskLevel.YELLOW.value
    return RiskLevel.GREEN.value


class IntelligencePersistence:
    """Encapsulates DB persistence and EventBus publishing for pipeline outputs."""

    def __init__(
        self,
        event_bus: EventBus,
        prediction_repo: PredictionRepository,
        risk_repo: RiskRepository,
        decision_repo: DecisionRepository,
    ) -> None:
        self._event_bus = event_bus
        self._prediction_repo = prediction_repo
        self._risk_repo = risk_repo
        self._decision_repo = decision_repo

    async def persist_results(self, ctx: IntelligenceContext) -> Result[None]:
        """Persist predictions, risk assessment, and decision from pipeline output."""
        now = datetime.now(timezone.utc)
        venue_uuid = uuid.UUID(ctx.venue_id)
        zone_uuid = uuid.UUID(ctx.zone_id) if ctx.zone_id else None

        pred_result = await self._persist_predictions(ctx, venue_uuid, zone_uuid, now)
        if isinstance(pred_result, Failure):
            return pred_result

        risk_result = await self._persist_risk(ctx, venue_uuid, zone_uuid, now)
        if isinstance(risk_result, Failure):
            return risk_result

        dec_result = await self._persist_decision(ctx, venue_uuid, zone_uuid, now)
        if isinstance(dec_result, Failure):
            return dec_result

        return Success(None)

    async def publish_intelligence_events(self, ctx: IntelligenceContext) -> None:
        """Publish intelligence results back to the EventBus."""
        if ctx.risk:
            await self._publish_risk_event(ctx)
        if ctx.decision:
            await self._publish_decision_event(ctx)

    async def _persist_predictions(
        self,
        ctx: IntelligenceContext,
        venue_uuid: uuid.UUID,
        zone_uuid: uuid.UUID | None,
        now: datetime,
    ) -> Result[None]:
        """Persist prediction bundle from pipeline output."""
        if not ctx.predictions or not ctx.predictions.predictions:
            return Success(None)

        predictions = [
            PredictionStore(
                venue_id=venue_uuid,
                zone_id=zone_uuid,
                prediction_type=p.get("type", "unknown"),
                predicted_value=p.get("value", 0.0),
                confidence=p.get("confidence", 0.0),
                confidence_breakdown=p.get("confidence_breakdown", {}),
                prediction_window_seconds=p.get("window_seconds", 300),
                predicted_at=now,
                valid_until=now,
                evidence_events=p.get("evidence", []),
                contributing_factors=p.get("factors", {}),
                model_version=p.get("model_version", "unknown"),
            )
            for p in ctx.predictions.predictions
        ]
        result = await self._prediction_repo.save_many(predictions)
        if isinstance(result, Failure):
            return Failure(
                error_code=result.error_code,
                message=f"Failed to save predictions: {result.message}",
            )
        return Success(None)

    async def _persist_risk(
        self,
        ctx: IntelligenceContext,
        venue_uuid: uuid.UUID,
        zone_uuid: uuid.UUID | None,
        now: datetime,
    ) -> Result[None]:
        """Persist risk assessment from pipeline output."""
        if not ctx.risk:
            return Success(None)

        dr = ctx.risk
        record = RiskHistory(
            venue_id=venue_uuid,
            zone_id=zone_uuid,
            risk_level=dr.overall_risk_level,
            risk_score=dr.overall_risk_score,
            risk_factors=dr.risk_factors,
            contributing_events=[],
            venue_risk=dr.domain_risks.get("venue", 0.0),
            zone_risk=dr.domain_risks.get("zone", 0.0),
            medical_risk=dr.domain_risks.get("medical", 0.0),
            security_risk=dr.domain_risks.get("security", 0.0),
            accessibility_risk=dr.domain_risks.get("accessibility", 0.0),
            transport_risk=dr.domain_risks.get("transport", 0.0),
            weather_risk=dr.domain_risks.get("weather", 0.0),
            assessed_at=now,
        )
        result = await self._risk_repo.save(record)
        if isinstance(result, Failure):
            return Failure(
                error_code=result.error_code,
                message=f"Failed to save risk: {result.message}",
            )
        return Success(None)

    async def _persist_decision(
        self,
        ctx: IntelligenceContext,
        venue_uuid: uuid.UUID,
        zone_uuid: uuid.UUID | None,
        now: datetime,
    ) -> Result[None]:
        """Persist decision from pipeline output."""
        if not ctx.decision:
            return Success(None)

        record = DecisionHistory(
            venue_id=venue_uuid,
            zone_id=zone_uuid,
            decision_status=DecisionStatus.PUBLISHED.value,
            intervention_type=ctx.decision.intervention_type,
            intervention_params=ctx.decision.intervention_params,
            risk_level_at_decision=(
                ctx.risk.overall_risk_level if ctx.risk else "green"
            ),
            confidence=ctx.decision.confidence,
            reasoning=ctx.decision.reasoning,
            alternative_decisions=ctx.decision.alternatives_rejected,
            expected_outcome={},
            published_at=now,
        )
        result = await self._decision_repo.save(record)
        if isinstance(result, Failure):
            return Failure(
                error_code=result.error_code,
                message=f"Failed to save decision: {result.message}",
            )
        return Success(None)

    async def _publish_risk_event(self, ctx: IntelligenceContext) -> None:
        """Publish a RiskAssessed event to the bus."""
        assert ctx.risk is not None
        event = EventBus.create_event(
            event_type="RiskAssessed",
            category=INTELLIGENCE_EVENT_CATEGORY,
            payload={
                "venue_id": ctx.venue_id,
                "zone_id": ctx.zone_id,
                "risk_level": ctx.risk.overall_risk_level,
                "risk_score": ctx.risk.overall_risk_score,
                "domain_risks": ctx.risk.domain_risks,
            },
            venue_id=ctx.venue_id,
            zone_id=ctx.zone_id,
        )
        await self._event_bus.publish(event)

    async def _publish_decision_event(self, ctx: IntelligenceContext) -> None:
        """Publish a DecisionPublished event to the bus."""
        assert ctx.decision is not None
        event = EventBus.create_event(
            event_type="DecisionPublished",
            category=INTELLIGENCE_EVENT_CATEGORY,
            payload={
                "venue_id": ctx.venue_id,
                "zone_id": ctx.zone_id,
                "intervention_type": ctx.decision.intervention_type,
                "confidence": ctx.decision.confidence,
                "reasoning": ctx.decision.reasoning,
            },
            venue_id=ctx.venue_id,
            zone_id=ctx.zone_id,
        )
        await self._event_bus.publish(event)
