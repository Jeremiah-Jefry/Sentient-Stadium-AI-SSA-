"""EventBus consumer — bridges Module 3 events to the navigation engine.

Subscribes to relevant event categories and updates the DynamicWeightEngine
with realtime conditions: crowd density, incidents, weather, infrastructure.
"""

from __future__ import annotations

import logging

from app.features.event_streaming.engine.event_bus import (
    EventBusEvent,
    Subscriber,
)
from app.features.navigation.graph.dynamic_weights import (
    DynamicWeightEngine,
    IncidentState,
    InfrastructureState,
)

logger = logging.getLogger(__name__)


class NavigationConsumer:
    """Consumes Module 3 events and updates navigation weight engine."""

    SUBSCRIBER_ID = "navigation-engine"

    def __init__(self, weight_engine: DynamicWeightEngine) -> None:
        self._weight_engine = weight_engine
        self._running = False

    async def handle_event(self, event: EventBusEvent) -> None:
        """Route event to appropriate handler based on category."""
        handler = self._HANDLERS.get(event.category)
        if handler:
            try:
                await handler(self, event)
            except Exception:
                logger.exception(
                    "Navigation consumer failed for %s", event.event_id,
                )

    async def _handle_crowd(self, event: EventBusEvent) -> None:
        payload = event.payload
        zone_id = event.zone_id or payload.get("zone_id", "")
        density = float(payload.get("density", 0.0))
        flow_rate = float(payload.get("flow_rate", 0.0))
        predicted_5m = payload.get("predicted_density_5m")
        predicted_15m = payload.get("predicted_density_15m")
        self._weight_engine.update_crowd_density(
            zone_id=zone_id,
            density=density,
            flow_rate=flow_rate,
            predicted_5m=float(predicted_5m) if predicted_5m is not None else None,
            predicted_15m=float(predicted_15m) if predicted_15m is not None else None,
        )

    async def _handle_weather(self, event: EventBusEvent) -> None:
        payload = event.payload
        self._weight_engine.update_weather(
            rain=float(payload.get("rain_intensity", 0.0)),
            wind=float(payload.get("wind_speed_kmh", 0.0)),
            heat=float(payload.get("heat_index", 0.0)),
            visibility=float(payload.get("visibility", 1.0)),
        )

    async def _handle_emergency(self, event: EventBusEvent) -> None:
        payload = event.payload
        incident = IncidentState(
            incident_type=event.event_type,
            severity=float(payload.get("severity", 1.0)),
            zone_id=event.zone_id or "",
            affected_edges=payload.get("affected_edges", []),
        )
        self._weight_engine.add_incident(incident)

    async def _handle_medical(self, event: EventBusEvent) -> None:
        payload = event.payload
        incident = IncidentState(
            incident_type="medical",
            severity=float(payload.get("severity", 1.0)),
            zone_id=event.zone_id or "",
        )
        self._weight_engine.add_incident(incident)

    async def _handle_security(self, event: EventBusEvent) -> None:
        payload = event.payload
        incident = IncidentState(
            incident_type="security",
            severity=float(payload.get("severity", 1.0)),
            zone_id=event.zone_id or "",
        )
        self._weight_engine.add_incident(incident)

    async def _handle_infrastructure(self, event: EventBusEvent) -> None:
        payload = event.payload
        infra = InfrastructureState(
            escalator_status=payload.get("escalator_status", {}),
            elevator_status=payload.get("elevator_status", {}),
            closed_corridors=set(payload.get("closed_corridors", [])),
            maintenance_zones=set(payload.get("maintenance_zones", [])),
        )
        self._weight_engine.update_infrastructure(infra)

    async def start(self) -> None:
        self._running = True
        logger.info("Navigation consumer started")

    async def stop(self) -> None:
        self._running = False
        logger.info("Navigation consumer stopped")

    @property
    def subscriber(self) -> Subscriber:
        """Create EventBus subscriber for navigation events."""
        return Subscriber(
            subscriber_id=self.SUBSCRIBER_ID,
            callback=self.handle_event,
            categories={"crowd", "weather", "emergency", "medical",
                        "security", "infrastructure"},
        )

    _HANDLERS = {
        "crowd": _handle_crowd,
        "weather": _handle_weather,
        "emergency": _handle_emergency,
        "medical": _handle_medical,
        "security": _handle_security,
        "infrastructure": _handle_infrastructure,
    }
