"""Notification consumer — broadcasts events to WebSocket subscribers."""

from __future__ import annotations

import logging

from app.features.event_streaming.consumers.base_consumer import BaseConsumer
from app.features.event_streaming.engine.event_bus import EventBusEvent
from app.features.event_streaming.models.event_type import EventSeverity

logger = logging.getLogger(__name__)

SEVERITY_BROADCAST_THRESHOLD = EventSeverity.MEDIUM


class NotificationConsumer(BaseConsumer):
    """Broadcasts events to connected WebSocket clients via the ConnectionManager.

    Routes events to the appropriate subscribers based on venue/entity
    subscriptions. Filters low-severity events to reduce noise.
    """

    def __init__(
        self,
        consumer_id: str,
        processing_service: object,
        connection_manager: object,
    ) -> None:
        super().__init__(consumer_id, processing_service)
        self._manager = connection_manager

    async def handle_event(self, event: EventBusEvent) -> bool:
        """Broadcast the event to relevant WebSocket subscribers."""
        ws_event = {
            "event_type": event.event_type,
            "category": event.category,
            "severity": event.severity,
            "entity_id": event.entity_id,
            "venue_id": event.venue_id,
            "data": event.payload,
            "timestamp": event.captured_at,
            "producer": event.producer,
        }

        if event.venue_id:
            await self._manager.broadcast_to_venue(event.venue_id, ws_event)

        if event.entity_id:
            await self._manager.broadcast_to_entity(event.entity_id, ws_event)

        if self._should_broadcast_global(event):
            await self._manager.broadcast_all(ws_event)

        return True

    @staticmethod
    def _should_broadcast_global(event: EventBusEvent) -> bool:
        """Determine if an event should be broadcast to all clients."""
        high_severity = event.severity in (
            EventSeverity.CRITICAL.value, EventSeverity.EMERGENCY.value,
        )
        is_emergency = event.category == "emergency"
        return high_severity or is_emergency
