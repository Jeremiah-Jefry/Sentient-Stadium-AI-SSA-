"""Observation service — preprocesses incoming events into feature vectors for the pipeline."""

from __future__ import annotations

import logging
import time

from app.features.ai_intelligence.context.match_context import MatchContextTracker
from app.features.ai_intelligence.context.spatial_reasoning import SpatialReasoner
from app.features.event_streaming.engine.event_bus import EventBusEvent

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_SECONDS: int = 300
DEFAULT_WINDOW_MAX_SIZE: int = 100
EVENT_HISTORY_KEY: str = "recent_events"


class ObservationService:
    """Preprocesses incoming events into feature dicts for the intelligence pipeline.

    Never reads sensors directly. Only works with validated events from Module 3.
    """

    def __init__(
        self,
        match_context: MatchContextTracker,
        spatial_reasoner: SpatialReasoner,
    ) -> None:
        self._match_context = match_context
        self._spatial = spatial_reasoner
        self._event_window: list[dict] = []
        self._window_max_size = DEFAULT_WINDOW_MAX_SIZE

    async def observe(self, event: EventBusEvent) -> dict:
        """Convert an EventBusEvent into a feature dict for the pipeline."""
        self._match_context.update_from_event(event.payload)

        features = self._extract_features(event)

        spatial_context = self._compute_spatial_context(event)
        features.update(spatial_context)

        recent = self._get_recent_events(DEFAULT_WINDOW_SECONDS)
        features[EVENT_HISTORY_KEY] = recent

        self._sliding_window_cleanup()
        logger.debug(
            "Observed event %s: category=%s type=%s",
            event.event_id, event.category, event.event_type,
        )
        return features

    def _extract_features(self, event: EventBusEvent) -> dict:
        """Extract relevant features from event payload."""
        payload = event.payload
        return {
            "event_id": event.event_id,
            "category": event.category,
            "event_type": event.event_type,
            "venue_id": event.venue_id or payload.get("venue_id"),
            "zone_id": event.zone_id or payload.get("zone_id"),
            "severity": event.severity,
            "priority": event.priority,
            "captured_at": event.captured_at,
            "density": payload.get("density", payload.get("crowd_density", 0.0)),
            "flow_rate": payload.get("flow_rate", payload.get("pedestrian_flow", 0.0)),
            "occupancy_percent": payload.get("occupancy_percent", payload.get("occupancy", 0.0)),
            "capacity": payload.get("capacity", 0),
            "active_sensors": payload.get("active_sensors", payload.get("sensor_count", 0)),
            "total_sensors": payload.get("total_sensors", 0),
            "incidents": payload.get("incidents", []),
            "blocked_exits": payload.get("blocked_exits", 0),
            "total_exits": payload.get("total_exits", 0),
            "match_phase": self._match_context.current_phase.value,
            "match_time_minutes": self._match_context.match_time_minutes,
            "scores": self._match_context.scores,
            "behavior_modifiers": self._match_context.get_behavior_modifiers(),
            "window_size": len(self._event_window),
        }

    def _compute_spatial_context(self, event: EventBusEvent) -> dict:
        """Compute spatial context using the spatial reasoner."""
        payload = event.payload
        zone_id = event.zone_id or payload.get("zone_id", "")

        venue_data = payload.get("venue_zones", {})
        bottlenecks = self._spatial.find_bottlenecks(venue_data) if venue_data else []

        zone_risk = 0.0
        neighbor_influence = 0.0
        if zone_id:
            zone_info = {
                "capacity": payload.get("capacity", 1),
                "occupancy": payload.get("occupancy", 0),
                "incidents": payload.get("incidents", []),
                "blocked_exits": payload.get("blocked_exits", 0),
                "total_exits": payload.get("total_exits", 1),
            }
            zone_risk = self._spatial.compute_zone_risk(zone_id, zone_info)
            neighbor_influence = self._spatial.compute_neighbor_influence(zone_id)

        evacuation_eff = 0.0
        if zone_id:
            evacuation_eff = self._spatial.get_evacuation_efficiency(zone_id)

        return {
            "spatial_zone_risk": zone_risk,
            "spatial_neighbor_influence": neighbor_influence,
            "spatial_bottlenecks": bottlenecks[:5],
            "spatial_evacuation_efficiency": evacuation_eff,
        }

    def _get_recent_events(self, window_seconds: int = DEFAULT_WINDOW_SECONDS) -> list[dict]:
        """Get recent events within the time window."""
        cutoff = time.time() - window_seconds
        return [
            e for e in self._event_window
            if e.get("timestamp", 0) >= cutoff
        ]

    def _sliding_window_cleanup(self) -> None:
        """Remove events outside the sliding window and enforce max size."""
        cutoff = time.time() - DEFAULT_WINDOW_SECONDS
        self._event_window = [
            e for e in self._event_window
            if e.get("timestamp", 0) >= cutoff
        ]

        if len(self._event_window) > self._window_max_size:
            excess = len(self._event_window) - self._window_max_size
            self._event_window = self._event_window[excess:]
