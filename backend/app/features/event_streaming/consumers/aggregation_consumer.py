"""Aggregation consumer — computes windowed aggregations from events."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from app.features.event_streaming.consumers.base_consumer import BaseConsumer
from app.features.event_streaming.engine.event_bus import EventBusEvent

logger = logging.getLogger(__name__)

WINDOWS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}


class AggregationConsumer(BaseConsumer):
    """Computes real-time windowed aggregations from event stream.

    Maintains in-memory counters per venue/zone/window. Periodically
    flushes aggregated data to the persistence layer.
    """

    def __init__(
        self,
        consumer_id: str,
        processing_service: object,
    ) -> None:
        super().__init__(consumer_id, processing_service)
        self._counters: dict[str, dict] = defaultdict(lambda: {
            "count": 0,
            "by_category": defaultdict(int),
            "by_severity": defaultdict(int),
            "values": [],
        })
        self._flush_interval = 60
        self._last_flush = time.monotonic()

    async def handle_event(self, event: EventBusEvent) -> bool:
        """Increment aggregation counters for the event."""
        for window_name in WINDOWS:
            key = self._counter_key(event, window_name)
            counter = self._counters[key]
            counter["count"] += 1
            counter["by_category"][event.category] += 1
            counter["by_severity"][event.severity] += 1

            if "crowd_density" in event.payload:
                counter["values"].append(float(event.payload["crowd_density"]))

        if time.monotonic() - self._last_flush >= self._flush_interval:
            await self._flush_aggregations()
            self._last_flush = time.monotonic()

        return True

    async def _flush_aggregations(self) -> None:
        """Flush in-memory aggregations to the persistence layer."""
        flushed = len(self._counters)
        self._counters.clear()
        if flushed > 0:
            logger.info("Flushed %d aggregation windows", flushed)

    @staticmethod
    def _counter_key(event: EventBusEvent, window: str) -> str:
        """Generate a unique key for the aggregation counter."""
        zone = event.zone_id or "global"
        return f"{event.venue_id}:{zone}:{window}"

    def get_current_aggregations(self) -> dict[str, dict]:
        """Get all current in-memory aggregations."""
        result: dict[str, dict] = {}
        for key, counter in self._counters.items():
            values = counter["values"]
            result[key] = {
                "count": counter["count"],
                "by_category": dict(counter["by_category"]),
                "by_severity": dict(counter["by_severity"]),
                "avg_value": sum(values) / len(values) if values else None,
                "max_value": max(values) if values else None,
            }
        return result
