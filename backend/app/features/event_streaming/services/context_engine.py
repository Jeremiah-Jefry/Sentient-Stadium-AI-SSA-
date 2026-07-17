"""Context engine — enriches events with spatial, temporal, and entity context."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.features.event_streaming.fusion.engine import FusionEngine
from app.features.event_streaming.repositories.sensor_repository import SensorRepository
from app.shared.result import Success

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_CACHE_TTL_SECONDS = 60
DEFAULT_CONTEXT_CACHE_MAX_ENTRIES = 500


@dataclass(slots=True)
class ContextCacheEntry:
    """Cache entry with creation timestamp for TTL-based expiry."""

    value: dict
    created_at: float


class ContextEngine:
    """Enriches events with contextual information from the digital twin and sensor network.

    Provides spatial context (nearby entities, zone info), temporal context
    (time-of-day patterns, event history), and sensor context (fused readings).
    """

    def __init__(
        self,
        sensor_repo: SensorRepository,
        fusion_engine: FusionEngine,
        cache_ttl_seconds: int = DEFAULT_CONTEXT_CACHE_TTL_SECONDS,
        cache_max_entries: int = DEFAULT_CONTEXT_CACHE_MAX_ENTRIES,
    ) -> None:
        self._sensor_repo = sensor_repo
        self._fusion_engine = fusion_engine
        self._cache_ttl = cache_ttl_seconds
        self._cache_max = cache_max_entries
        self._context_cache: dict[str, ContextCacheEntry] = {}

    async def enrich_event(self, event_data: dict) -> dict:
        """Enrich an event with contextual metadata."""
        self._sweep_expired()

        venue_id = event_data.get("venue_id")
        entity_id = event_data.get("entity_id")
        zone_id = event_data.get("zone_id")

        context: dict = {
            "enrichment_timestamp": time.time(),
            "enrichment_version": "1.0",
        }

        if venue_id:
            sensor_ctx = await self._get_sensor_context(uuid.UUID(venue_id))
            context["sensor_context"] = sensor_ctx

        if zone_id:
            fused = self._fusion_engine.get_all_fused_results()
            zone_fused = {
                k: {"value": v.value, "confidence": v.confidence}
                for k, v in fused.items()
                if k.startswith(f"{zone_id}:")
            }
            context["fused_readings"] = zone_fused

        if entity_id:
            context["entity_context"] = await self._get_entity_context(entity_id)

        context["temporal_context"] = self._get_temporal_context()
        return context

    async def _get_sensor_context(self, venue_id: uuid.UUID) -> dict:
        """Get sensor status context for a venue."""
        cache_key = f"sensors:{venue_id}"
        cached = self._context_cache.get(cache_key)
        if cached is not None and not self._is_expired(cached):
            return cached.value

        sensors_result = await self._sensor_repo.get_active_by_venue(venue_id)
        if not isinstance(sensors_result, Success):
            return {"error": "Failed to fetch sensors"}

        sensors = sensors_result.value
        by_type: dict[str, int] = {}
        for s in sensors:
            by_type[s.sensor_type] = by_type.get(s.sensor_type, 0) + 1

        context = {
            "total_active_sensors": len(sensors),
            "by_type": by_type,
        }
        self._context_cache[cache_key] = ContextCacheEntry(
            value=context, created_at=time.monotonic(),
        )
        return context

    async def _get_entity_context(self, entity_id: str) -> dict:
        """Get basic entity context."""
        return {
            "entity_id": entity_id,
            "context_source": "context_engine",
        }

    @staticmethod
    def _get_temporal_context() -> dict:
        """Provide temporal context based on current time."""
        utc_hour = datetime.now(timezone.utc).hour

        if 6 <= utc_hour < 12:
            period = "morning"
        elif 12 <= utc_hour < 18:
            period = "afternoon"
        elif 18 <= utc_hour < 22:
            period = "evening"
        else:
            period = "night"

        return {
            "utc_hour": utc_hour,
            "period": period,
            "is_match_day": False,
        }

    def _is_expired(self, entry: ContextCacheEntry) -> bool:
        """Check if a cache entry has exceeded its TTL."""
        return time.monotonic() - entry.created_at > self._cache_ttl

    def _sweep_expired(self) -> None:
        """Remove expired entries and evict oldest if over capacity."""
        expired = [
            k for k, v in self._context_cache.items() if self._is_expired(v)
        ]
        for key in expired:
            del self._context_cache[key]

        while len(self._context_cache) > self._cache_max:
            oldest_key = next(iter(self._context_cache))
            del self._context_cache[oldest_key]

    def invalidate_cache(self, venue_id: str | None = None) -> None:
        """Clear the context cache for a venue or all venues."""
        if venue_id:
            keys_to_remove = [k for k in self._context_cache if venue_id in k]
            for key in keys_to_remove:
                del self._context_cache[key]
        else:
            self._context_cache.clear()
