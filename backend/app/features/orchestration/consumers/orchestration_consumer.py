"""Event consumer that triggers orchestration from real-time events.

Subscribes to the event streaming bus and automatically triggers
orchestration when high-priority events (emergencies, incidents,
crowd alerts) require multi-agent coordination.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from app.features.orchestration.models.enums import (
    IntentType,
    RequestType,
    UserRole,
)

if TYPE_CHECKING:
    from app.features.event_streaming.engine.event_bus import EventBusEvent
    from app.features.orchestration.services.orchestration_service import (
        OrchestrationService,
    )

logger = logging.getLogger(__name__)

_SUBSCRIBER_ID = "orchestration-engine"

_EVENT_TO_INTENT: dict[str, IntentType] = {
    "crowd_density_critical": IntentType.CROWD_MANAGEMENT,
    "crowd_bottleneck_detected": IntentType.CROWD_MANAGEMENT,
    "emergency_detected": IntentType.EMERGENCY_RESPONSE,
    "medical_emergency": IntentType.MEDICAL,
    "incident_detected": IntentType.INCIDENT_RESPONSE,
    "security_alert": IntentType.SECURITY,
    "weather_severe": IntentType.WEATHER_ADVISORY,
    "accessibility_request": IntentType.ACCESSIBILITY,
    "evacuation_needed": IntentType.EVACUATION,
    "sensor_anomaly": IntentType.OPERATIONAL,
}

_HIGH_PRIORITY_INTENTS = {
    IntentType.EMERGENCY_RESPONSE,
    IntentType.MEDICAL,
    IntentType.EVACUATION,
    IntentType.SECURITY,
}


class OrchestrationConsumer:
    """Consumes events from the streaming bus and triggers orchestration.

    Automatically routes high-priority events to the orchestration engine
    with appropriate intent classification and priority escalation.
    """

    SUBSCRIBER_ID: str = _SUBSCRIBER_ID

    def __init__(self, service: OrchestrationService) -> None:
        self._service = service
        self._running = False
        self._processed_count = 0
        self._error_count = 0

    async def start(self) -> None:
        self._running = True
        logger.info("Orchestration consumer started")

    async def stop(self) -> None:
        self._running = False
        logger.info(
            "Orchestration consumer stopped (processed=%d, errors=%d)",
            self._processed_count,
            self._error_count,
        )

    async def handle_event(self, event: EventBusEvent) -> None:
        """Handle a single event from the streaming bus.

        Filters for events that require orchestration, classifies intent,
        and submits them to the orchestration service.
        """
        if not self._running:
            return

        event_type = event.event_type
        intent = _EVENT_TO_INTENT.get(event_type)

        if intent is None:
            return

        priority = 8 if intent in _HIGH_PRIORITY_INTENTS else 5
        zone_uuid = uuid.UUID(event.zone_id) if event.zone_id else None
        venue_uuid = uuid.UUID(event.venue_id) if event.venue_id else None

        from app.features.orchestration.dto.request import OrchestratorRequest

        request = OrchestratorRequest(
            request_id=uuid.uuid4(),
            request_type=RequestType.REALTIME_EVENT,
            intent=intent,
            query=event.payload.get("description", event_type),
            context={
                "source_event": {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "category": event.category,
                    "priority": event.priority,
                    "severity": event.severity,
                },
                "trigger": "event_consumer",
                "event_type": event_type,
            },
            venue_id=venue_uuid,
            zone_id=zone_uuid,
            user_role=UserRole.SYSTEM,
            priority=priority,
            timeout_seconds=30.0,
            metadata={
                "consumer": _SUBSCRIBER_ID,
                "event_id": event.event_id,
            },
        )

        try:
            await self._service.execute(request)
            self._processed_count += 1
            logger.info(
                "Orchestration triggered by event %s (intent=%s, priority=%d)",
                event_type,
                intent.value,
                priority,
            )
        except Exception:
            self._error_count += 1
            logger.exception(
                "Failed to orchestrate event %s",
                event_type,
            )

    @property
    def stats(self) -> dict[str, int]:
        return {
            "processed": self._processed_count,
            "errors": self._error_count,
            "running": int(self._running),
        }
