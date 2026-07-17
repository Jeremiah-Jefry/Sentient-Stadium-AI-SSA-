"""Intelligence service — main orchestrator for the AI Intelligence Engine."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from app.features.ai_intelligence.engine.context import IntelligenceContext
from app.features.ai_intelligence.engine.pipeline import IntelligencePipeline
from app.features.ai_intelligence.models.enums import RiskLevel
from app.features.ai_intelligence.repositories.decision_repository import DecisionRepository
from app.features.ai_intelligence.repositories.outcome_repository import OutcomeRepository
from app.features.ai_intelligence.repositories.prediction_repository import PredictionRepository
from app.features.ai_intelligence.repositories.risk_repository import RiskRepository
from app.features.ai_intelligence.services.intelligence_persistence import (
    IntelligencePersistence,
    classify_risk,
)
from app.features.event_streaming.engine.event_bus import EventBus, EventBusEvent
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)


class IntelligenceService:
    """Main orchestrator — runs events through the pipeline and publishes intelligence."""

    def __init__(
        self,
        pipeline: IntelligencePipeline,
        event_bus: EventBus,
        prediction_repo: PredictionRepository,
        risk_repo: RiskRepository,
        decision_repo: DecisionRepository,
        outcome_repo: OutcomeRepository,
    ) -> None:
        self._pipeline = pipeline
        self._persistence = IntelligencePersistence(
            event_bus, prediction_repo, risk_repo, decision_repo,
        )
        self._prediction_repo = prediction_repo
        self._risk_repo = risk_repo
        self._decision_repo = decision_repo
        self._outcome_repo = outcome_repo
        self._total_processed = 0
        self._total_errors = 0
        self._last_assessment_at: str | None = None

    async def process_event(self, event: EventBusEvent) -> Result[IntelligenceContext]:
        start_ms = time.monotonic() * 1000
        venue_id = event.venue_id or event.payload.get("venue_id", "")
        if not venue_id:
            return Failure(error_code="MISSING_VENUE_ID", message="No venue_id")

        ctx = IntelligenceContext(
            triggering_event=event,
            venue_id=venue_id,
            zone_id=event.zone_id or event.payload.get("zone_id"),
            pipeline_start_ms=start_ms,
        )

        try:
            ctx = await self._pipeline.process(ctx)
        except Exception as exc:
            logger.exception("Pipeline failed for event %s", event.event_id)
            self._total_errors += 1
            return Failure(
                error_code="PIPELINE_FAILED",
                message=f"Pipeline failed: {exc}",
                details={"event_id": event.event_id},
            )

        persist_result = await self._persistence.persist_results(ctx)
        if isinstance(persist_result, Failure):
            return Failure(
                error_code="PERSIST_FAILED",
                message=persist_result.message,
                details=persist_result.details,
            )

        await self._persistence.publish_intelligence_events(ctx)
        self._total_processed += 1
        self._last_assessment_at = datetime.now(timezone.utc).isoformat()

        latency_ms = (time.monotonic() * 1000) - start_ms
        logger.info(
            "Event %s processed in %.1fms: risk=%s decision=%s",
            event.event_id, latency_ms,
            ctx.risk.overall_risk_level if ctx.risk else "none",
            ctx.decision.intervention_type if ctx.decision else "none",
        )
        return Success(ctx)

    async def get_current_risk(
        self, venue_id: str, zone_id: str | None = None,
    ) -> Result[dict]:
        v_uuid = uuid.UUID(venue_id)
        z_uuid = uuid.UUID(zone_id) if zone_id else None
        result = await self._risk_repo.get_latest_by_venue(v_uuid, z_uuid)
        if isinstance(result, Failure):
            return Failure(error_code=result.error_code, message=result.message)

        risk = result.value
        if risk is None:
            empty = {"venue_id": venue_id, "zone_id": zone_id,
                     "risk_level": RiskLevel.GREEN.value, "risk_score": 0.0}
            return Success(empty)

        return Success({
            "venue_id": str(risk.venue_id),
            "zone_id": str(risk.zone_id) if risk.zone_id else None,
            "risk_level": risk.risk_level, "risk_score": risk.risk_score,
            "venue_risk": risk.venue_risk, "zone_risk": risk.zone_risk,
            "medical_risk": risk.medical_risk,
            "security_risk": risk.security_risk,
            "accessibility_risk": risk.accessibility_risk,
            "transport_risk": risk.transport_risk,
            "weather_risk": risk.weather_risk,
            "risk_factors": risk.risk_factors,
            "assessed_at": risk.assessed_at.isoformat(),
        })

    async def get_predictions(
        self, venue_id: str, zone_id: str | None = None,
        prediction_type: str | None = None, min_confidence: float = 0.0,
        page: int = 1, page_size: int = 50,
    ) -> Result[tuple[list[dict], int]]:
        v_uuid = uuid.UUID(venue_id)
        z_uuid = uuid.UUID(zone_id) if zone_id else None
        result = await self._prediction_repo.get_active_by_venue(
            venue_id=v_uuid, zone_id=z_uuid,
            min_confidence=min_confidence, page=page, page_size=page_size,
        )
        if isinstance(result, Failure):
            return Failure(error_code=result.error_code, message=result.message)
        predictions, total = result.value
        if prediction_type:
            predictions = [p for p in predictions if p.prediction_type == prediction_type]

        return Success((
            [{"id": str(p.id), "venue_id": str(p.venue_id),
              "zone_id": str(p.zone_id) if p.zone_id else None,
              "prediction_type": p.prediction_type,
              "predicted_value": p.predicted_value, "confidence": p.confidence,
              "prediction_window_seconds": p.prediction_window_seconds,
              "predicted_at": p.predicted_at.isoformat(),
              "valid_until": p.valid_until.isoformat(),
              "contributing_factors": p.contributing_factors,
              "evidence_events": p.evidence_events,
              "model_version": p.model_version} for p in predictions], total,
        ))

    async def get_decision_history(
        self, venue_id: str, status: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> Result[tuple[list[dict], int]]:
        v_uuid = uuid.UUID(venue_id)
        result = await self._decision_repo.get_by_venue(
            venue_id=v_uuid, status=status, page=page, page_size=page_size,
        )
        if isinstance(result, Failure):
            return Failure(error_code=result.error_code, message=result.message)
        decisions, total = result.value
        return Success((
            [{"id": str(d.id), "venue_id": str(d.venue_id),
              "zone_id": str(d.zone_id) if d.zone_id else None,
              "decision_status": d.decision_status,
              "intervention_type": d.intervention_type,
              "confidence": d.confidence,
              "risk_level_at_decision": d.risk_level_at_decision,
              "reasoning": d.reasoning,
              "expected_outcome": d.expected_outcome,
              "published_at": (d.published_at.isoformat()
                               if d.published_at else None)}
             for d in decisions], total,
        ))

    async def explain_decision(self, decision_id: str) -> Result[dict]:
        d_uuid = uuid.UUID(decision_id)
        result = await self._decision_repo.get_by_id(d_uuid)
        if isinstance(result, Failure):
            return Failure(error_code=result.error_code, message=result.message)

        d = result.value
        if d is None:
            return Failure(error_code="DECISION_NOT_FOUND",
                           message=f"Decision {decision_id} not found")
        return Success({
            "decision_id": decision_id,
            "summary": f"Recommended {d.intervention_type} at {d.confidence:.0%}",
            "reasoning": d.reasoning,
            "alternative_decisions": d.alternative_decisions,
            "expected_outcome": d.expected_outcome,
            "risk_level_at_decision": d.risk_level_at_decision,
            "intervention_params": d.intervention_params,
        })

    async def simulate_intervention(
        self, venue_id: str, intervention_type: str,
        strategy_params: dict, zone_id: str | None = None,
    ) -> Result[dict]:
        v_uuid = uuid.UUID(venue_id)
        z_uuid = uuid.UUID(zone_id) if zone_id else None
        risk_result = await self._risk_repo.get_latest_by_venue(v_uuid, z_uuid)
        if isinstance(risk_result, Failure):
            return Failure(
                error_code=risk_result.error_code, message=risk_result.message,
            )

        current = risk_result.value
        risk_before = current.risk_level if current else RiskLevel.GREEN.value
        score_before = current.risk_score if current else 0.0
        reduction = min(score_before * 0.3, 0.5)
        sim_score = max(0.0, score_before - reduction)
        return Success({
            "venue_id": venue_id, "zone_id": zone_id,
            "intervention_type": intervention_type,
            "strategy_params": strategy_params,
            "risk_before": risk_before,
            "risk_score_before": round(score_before, 4),
            "simulated_risk_reduction": round(reduction, 4),
            "simulated_risk_score": round(sim_score, 4),
            "risk_after": classify_risk(sim_score),
            "confidence": 0.75,
        })

    @property
    def status(self) -> dict:
        return {
            "total_processed": self._total_processed,
            "total_errors": self._total_errors,
            "last_assessment_at": self._last_assessment_at,
            "engine_active": True,
        }

    @property
    def stats(self) -> dict:
        rate = (
            round(self._total_errors / self._total_processed, 4)
            if self._total_processed > 0 else 0.0
        )
        return {
            "total_processed": self._total_processed,
            "total_errors": self._total_errors,
            "error_rate": rate,
            "last_assessment_at": self._last_assessment_at,
        }
