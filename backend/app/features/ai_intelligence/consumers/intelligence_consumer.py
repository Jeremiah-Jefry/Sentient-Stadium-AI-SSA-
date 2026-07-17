"""Intelligence consumer — bridges Module 3 events to the AI Intelligence Engine."""

from __future__ import annotations

import logging
import time

from app.features.ai_intelligence.services.intelligence_service import IntelligenceService
from app.features.ai_intelligence.services.monitoring_service import MonitoringService
from app.features.event_streaming.consumers.base_consumer import BaseConsumer
from app.features.event_streaming.engine.event_bus import EventBusEvent
from app.features.event_streaming.services.processing_service import ProcessingService
from app.shared.result import is_success

logger = logging.getLogger(__name__)

CATEGORIES_OF_INTEREST = frozenset({
    "crowd",
    "security",
    "medical",
    "transport",
    "weather",
    "infrastructure",
    "operations",
    "emergency",
})


class IntelligenceConsumer(BaseConsumer):
    """Consumes validated events from the Event Bus and feeds them to the AI Intelligence Engine.

    Filters: only processes events from relevant categories
    (crowd, security, medical, transport, weather, infrastructure, operations, emergency).
    Ignores: sensor events, system events (these are pre-processed by Module 3).
    """

    def __init__(
        self,
        consumer_id: str,
        processing_service: ProcessingService,
        intelligence_service: IntelligenceService,
        monitoring_service: MonitoringService,
    ) -> None:
        super().__init__(consumer_id, processing_service)
        self._intelligence = intelligence_service
        self._monitoring = monitoring_service

    async def handle_event(self, event: EventBusEvent) -> bool:
        """Process an event through the intelligence pipeline."""
        if event.category not in CATEGORIES_OF_INTEREST:
            logger.debug(
                "Skipping event %s: category '%s' not in scope",
                event.event_id, event.category,
            )
            return True

        start_ms = time.monotonic() * 1000

        result = await self._intelligence.process_event(event)

        latency_ms = (time.monotonic() * 1000) - start_ms
        self._monitoring.record_latency(latency_ms)

        if is_success(result):
            ctx = result.value
            risk_level = ctx.risk.overall_risk_level if ctx.risk else None
            decision_type = ctx.decision.intervention_type if ctx.decision else None

            logger.info(
                "Intelligence processed event %s: risk=%s decision=%s latency=%.1fms",
                event.event_id, risk_level, decision_type, latency_ms,
            )
            return True

        logger.warning(
            "Intelligence failed for event %s: %s",
            event.event_id, result.message,
        )
        self._monitoring.record_prediction(event.event_id, was_correct=None)
        return False
