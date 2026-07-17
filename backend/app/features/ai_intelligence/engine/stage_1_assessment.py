"""Stage 1 — Realtime Situation Assessment: builds SituationAssessment from event data."""

from __future__ import annotations

import logging
import time

from app.features.ai_intelligence.context.match_context import MatchContextTracker
from app.features.ai_intelligence.engine.context import (
    IntelligenceContext,
    SituationAssessment,
)

logger = logging.getLogger(__name__)

SENSOR_AVAILABILITY_THRESHOLD: float = 0.5
DENSITY_DEFAULT: float = 0.0
FLOW_RATE_DEFAULT: float = 0.0
OCCUPANCY_DEFAULT: float = 0.0


class Stage1Assessment:
    """Extracts and normalises a SituationAssessment from the triggering event."""

    def __init__(self, match_context: MatchContextTracker) -> None:
        self._match_context = match_context

    async def execute(self, ctx: IntelligenceContext) -> None:
        event = ctx.triggering_event
        payload = getattr(event, "payload", {}) or {}

        density = self._extract_density(payload)
        flow_rate = self._extract_flow_rate(payload)
        occupancy = self._extract_occupancy(payload)
        active_sensors = self._extract_active_sensors(payload)
        recent = self._extract_recent_events(payload)
        modifiers = self._match_context.get_behavior_modifiers()

        ctx.situation = SituationAssessment(
            venue_id=ctx.venue_id,
            zone_id=ctx.zone_id or payload.get("zone_id"),
            current_density=density,
            flow_rate=flow_rate,
            occupancy_percent=occupancy,
            active_sensors=active_sensors,
            recent_events=recent,
            match_phase=self._match_context.current_phase.value,
            behavior_modifiers=modifiers,
            timestamp=time.time(),
        )
        logger.debug(
            "Stage 1 complete: density=%.3f flow=%.3f occupancy=%.3f sensors=%d",
            density, flow_rate, occupancy, active_sensors,
        )

    @staticmethod
    def _extract_density(payload: dict) -> float:
        raw = payload.get("density", payload.get("crowd_density", DENSITY_DEFAULT))
        capacity = max(payload.get("capacity", 1.0), 0.01)
        if isinstance(raw, (int, float)) and raw > 1.0:
            return min(raw / capacity, 10.0)
        return float(raw) if isinstance(raw, (int, float)) else DENSITY_DEFAULT

    @staticmethod
    def _extract_flow_rate(payload: dict) -> float:
        raw = payload.get("flow_rate", payload.get("pedestrian_flow", FLOW_RATE_DEFAULT))
        return float(raw) if isinstance(raw, (int, float)) else FLOW_RATE_DEFAULT

    @staticmethod
    def _extract_occupancy(payload: dict) -> float:
        raw = payload.get("occupancy_percent", payload.get("occupancy", OCCUPANCY_DEFAULT))
        if isinstance(raw, (int, float)):
            return max(0.0, min(100.0, float(raw)))
        return OCCUPANCY_DEFAULT

    @staticmethod
    def _extract_active_sensors(payload: dict) -> int:
        active = payload.get("active_sensors", payload.get("sensor_count", 0))
        total = payload.get("total_sensors", active)
        if total > 0 and active / total < SENSOR_AVAILABILITY_THRESHOLD:
            logger.warning(
                "Low sensor availability: %d/%d active", active, total,
            )
        return int(active) if isinstance(active, (int, float)) else 0

    @staticmethod
    def _extract_recent_events(payload: dict) -> list[dict]:
        recent = payload.get("recent_events", [])
        if not isinstance(recent, list):
            return []
        return recent[:20]
