"""Sensor fusion service — orchestrates multi-sensor data fusion for events."""

from __future__ import annotations

import logging
import time
import uuid

from app.features.event_streaming.fusion.algorithms import SensorReading
from app.features.event_streaming.fusion.engine import FusionEngine
from app.features.event_streaming.repositories.sensor_repository import SensorRepository
from app.shared.result import Result, Success

logger = logging.getLogger(__name__)


class SensorFusionService:
    """Orchestrates sensor fusion: collects readings, applies algorithms, emits fused events.

    Bridges the gap between raw sensor data and high-level contextual events
    by fusing multiple sensor inputs into unified readings.
    """

    def __init__(
        self,
        fusion_engine: FusionEngine,
        sensor_repo: SensorRepository,
    ) -> None:
        self._fusion_engine = fusion_engine
        self._sensor_repo = sensor_repo
        self._total_fused = 0

    async def process_sensor_reading(
        self,
        sensor_id: str,
        value: float,
        sensor_type: str,
        venue_id: str,
        zone_id: str | None = None,
    ) -> Result[dict]:
        """Process a single sensor reading through fusion."""
        sensor_result = await self._sensor_repo.get_by_id(uuid.UUID(sensor_id))
        if not isinstance(sensor_result, Success) or sensor_result.value is None:
            return Success({"fused": False, "reason": "sensor_not_found"})

        sensor = sensor_result.value
        if not sensor.is_active:
            return Success({"fused": False, "reason": "sensor_inactive"})

        reading = SensorReading(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            value=value,
            accuracy=sensor.accuracy or 0.5,
            timestamp=time.monotonic(),
            zone_id=zone_id,
        )

        fused = self._fusion_engine.add_reading(reading)
        if fused is None:
            return Success({"fused": False, "reason": "insufficient_readings"})

        self._total_fused += 1
        return Success({
            "fused": True,
            "value": fused.value,
            "confidence": fused.confidence,
            "variance": fused.variance,
            "outlier_count": fused.outlier_count,
            "algorithm": fused.algorithm_used,
            "sensor_count": len(fused.sensor_ids),
        })

    def get_zone_status(self, zone_id: str) -> dict:
        """Get the current fused status for all sensor types in a zone."""
        results = self._fusion_engine.get_all_fused_results()
        zone_results = {}
        for key, fused in results.items():
            if key.startswith(f"{zone_id}:"):
                sensor_type = key.split(":", 1)[1]
                zone_results[sensor_type] = {
                    "value": fused.value,
                    "confidence": fused.confidence,
                    "algorithm": fused.algorithm_used,
                    "sensor_count": len(fused.sensor_ids),
                }
        return zone_results

    @property
    def stats(self) -> dict:
        return {
            "total_fused": self._total_fused,
            "engine_stats": self._fusion_engine.stats,
        }
