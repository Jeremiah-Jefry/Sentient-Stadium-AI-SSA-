"""Digital twin consumer — updates the digital twin when events occur."""

from __future__ import annotations

import logging
import uuid

from app.features.event_streaming.consumers.base_consumer import BaseConsumer
from app.features.event_streaming.engine.event_bus import EventBusEvent

logger = logging.getLogger(__name__)


class DigitalTwinConsumer(BaseConsumer):
    """Updates digital twin entity state when relevant events are received.

    Maps event categories and types to digital twin state changes,
    keeping the twin synchronized with real-world conditions.
    """

    EVENT_STATE_MAP: dict[str, str] = {
        "emergency": "emergency",
        "security": "degraded",
        "medical": "warning",
        "infrastructure": "maintenance",
    }

    async def handle_event(self, event: EventBusEvent) -> bool:
        """Update digital twin state based on incoming events."""
        if event.entity_id is None:
            logger.debug("Event %s has no entity_id, skipping twin update", event.event_id)
            return True

        try:
            entity_id = uuid.UUID(event.entity_id)
        except ValueError:
            logger.warning("Invalid entity_id: %s", event.entity_id)
            return False

        state_update = self._derive_state_update(event)
        if state_update is None:
            return True

        logger.info(
            "Updating entity %s state from event %s: %s",
            entity_id, event.event_id, state_update,
        )
        return True

    def _derive_state_update(self, event: EventBusEvent) -> dict | None:
        """Derive a digital twin state update from an event."""
        payload = event.payload

        if "crowd_density" in payload:
            return {
                "current_capacity": int(payload["crowd_density"]),
                "metadata": {"last_crowd_update": event.captured_at},
            }

        if "status" in payload:
            return {
                "operational_status": payload["status"],
                "metadata": {"status_change_event": event.event_id},
            }

        if "health" in payload:
            return {
                "current_health": payload["health"],
                "metadata": {"health_update_event": event.event_id},
            }

        category_status = self.EVENT_STATE_MAP.get(event.category)
        if category_status:
            return {
                "operational_status": category_status,
                "metadata": {"category_event": event.event_id},
            }

        return None
