"""Stage 4 — Risk Scoring: computes multi-domain risk from assessment and behaviour data."""

from __future__ import annotations

import logging

from app.features.ai_intelligence.engine.context import (
    IntelligenceContext,
    RiskBundle,
)
from app.features.ai_intelligence.risk.risk_engine import RiskEngine

logger = logging.getLogger(__name__)

DOMAIN_WEIGHTS: dict[str, float] = {
    "medical": 0.20,
    "security": 0.18,
    "accessibility": 0.12,
    "transport": 0.10,
    "weather": 0.10,
    "venue": 0.15,
    "zone": 0.15,
}

CONFIDENCE_ESTIMATE_FACTORS: list[str] = [
    "active_sensors",
    "data_freshness",
    "model_agreement",
]


class Stage4Risk:
    """Runs RiskEngine with enriched context and produces a RiskBundle."""

    def __init__(self, risk_engine: RiskEngine) -> None:
        self._engine = risk_engine

    async def execute(self, ctx: IntelligenceContext) -> None:
        sit = ctx.situation
        behav = ctx.behaviour
        if sit is None:
            ctx.risk = self._minimal_risk()
            return

        context = self._build_risk_context(sit, behav, ctx)
        result = await self._engine.assess_risk(context)

        domain_risks = {
            "medical": result.medical_risk,
            "security": result.security_risk,
            "accessibility": result.accessibility_risk,
            "transport": result.transport_risk,
            "weather": result.weather_risk,
            "venue": result.venue_risk,
            "zone": result.zone_risk,
        }
        confidence = self._estimate_confidence(sit)

        ctx.risk = RiskBundle(
            overall_risk_level=result.risk_level.value,
            overall_risk_score=result.risk_score,
            domain_risks=domain_risks,
            risk_factors=result.risk_factors,
            confidence=round(confidence, 4),
        )
        logger.debug(
            "Stage 4 complete: level=%s score=%.3f confidence=%.3f",
            result.risk_level.value, result.risk_score, confidence,
        )

    @staticmethod
    def _build_risk_context(sit, behav, ctx) -> dict:
        modifiers = sit.behavior_modifiers
        event = ctx.triggering_event
        payload = getattr(event, "payload", {}) or {}

        bottleneck_penalty = 0.0
        if behav and behav.bottleneck_risk > 0.5:
            bottleneck_penalty = (behav.bottleneck_risk - 0.5) * 0.4

        density = sit.current_density * (1.0 + modifiers.get("density_surge", 0.0) * 0.3)
        capacity = max(sit.occupancy_percent, 1.0)

        return {
            "venue_id": sit.venue_id,
            "zone_id": sit.zone_id,
            "density": min(density, 5.0),
            "capacity": capacity,
            "flow_rate": sit.flow_rate,
            "expected_flow": max(1.0 - modifiers.get("movement_intensity", 0.5), 0.1),
            "weather": payload.get("weather", {}),
            "medical_events": payload.get("medical_events", []),
            "medical_capacity": payload.get("medical_capacity", 1),
            "security_events": payload.get("security_events", []),
            "blocked_paths": payload.get("blocked_paths", 0),
            "total_paths": max(payload.get("total_paths", 1), 1),
            "wheelchair_users": payload.get("wheelchair_users", 0),
            "transport_delays": payload.get("transport_delays", []),
            "expected_arrivals": max(payload.get("expected_arrivals", 1), 1),
            "volunteers_available": payload.get("volunteers_available", 10),
            "volunteers_needed": max(payload.get("volunteers_needed", 10), 1),
            "offline_sensors": max(
                payload.get("total_sensors", 0) - sit.active_sensors, 0,
            ),
            "total_sensors": max(payload.get("total_sensors", sit.active_sensors), 1),
            "match_phase": sit.match_phase,
            "score_diff": payload.get("score_diff", 0),
            "minutes_remaining": payload.get("minutes_remaining", 90),
            "contributing_event_ids": [
                e.get("id", "") for e in sit.recent_events if isinstance(e, dict)
            ],
        }

    @staticmethod
    def _estimate_confidence(sit) -> float:
        sensor_ratio = min(sit.active_sensors / max(sit.active_sensors + 10, 1), 1.0)
        data_density = min(len(sit.recent_events) / 15.0, 1.0)
        freshness = 1.0 if sit.timestamp > 0 else 0.5
        confidence = 0.45 * sensor_ratio + 0.35 * data_density + 0.20 * freshness
        return max(0.1, min(1.0, confidence))

    @staticmethod
    def _minimal_risk() -> RiskBundle:
        return RiskBundle(
            overall_risk_level="green",
            overall_risk_score=0.0,
            domain_risks={},
            risk_factors={},
            confidence=0.0,
        )
