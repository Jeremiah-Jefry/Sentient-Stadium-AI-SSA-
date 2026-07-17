"""Sensor fusion engine — orchestrates multi-sensor data fusion."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from app.features.event_streaming.fusion.algorithms import (
    FusedReading,
    FusionAlgorithms,
    SensorReading,
)

logger = logging.getLogger(__name__)

DEFAULT_FUSION_WINDOW_MS = 5000
DEFAULT_MIN_SENSORS = 2
DEFAULT_CONFIDENCE_THRESHOLD = 0.5


class FusionEngine:
    """Orchestrates sensor fusion across zones and sensor types.

    Collects readings within a configurable time window, applies the
    appropriate fusion algorithm, and produces a single FusedReading
    per sensor-type per zone.
    """

    def __init__(
        self,
        algorithms: FusionAlgorithms | None = None,
        fusion_window_ms: int = DEFAULT_FUSION_WINDOW_MS,
        min_sensors: int = DEFAULT_MIN_SENSORS,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self._algorithms = algorithms or FusionAlgorithms()
        self._fusion_window_ms = fusion_window_ms
        self._min_sensors = min_sensors
        self._confidence_threshold = confidence_threshold
        self._reading_buffer: dict[str, list[SensorReading]] = defaultdict(list)
        self._fused_results: dict[str, FusedReading] = {}
        self._total_fused = 0
        self._total_outliers_rejected = 0

    def add_reading(self, reading: SensorReading) -> FusedReading | None:
        """Add a sensor reading to the buffer. Returns fused result if window is ready."""
        key = self._buffer_key(reading.zone_id or "global", reading.sensor_type)
        self._reading_buffer[key].append(reading)
        self._evict_old_readings(key)

        if len(self._reading_buffer[key]) >= self._min_sensors:
            return self._fuse_buffer(key)
        return None

    def get_fused_result(self, zone_id: str, sensor_type: str) -> FusedReading | None:
        """Get the most recent fused result for a zone/sensor-type combination."""
        key = self._buffer_key(zone_id, sensor_type)
        return self._fused_results.get(key)

    def get_all_fused_results(self) -> dict[str, FusedReading]:
        """Get all current fused results."""
        return dict(self._fused_results)

    def select_algorithm(self, sensor_type: str, reading_count: int) -> str:
        """Select the best fusion algorithm based on sensor type and data volume."""
        if reading_count == 1:
            return "passthrough"
        if sensor_type in ("density_camera", "lidar", "radar"):
            return "kalman_filter"
        if reading_count >= 5:
            return "median"
        return "weighted_average"

    def _fuse_buffer(self, key: str) -> FusedReading:
        """Fuse all readings in a buffer key using the selected algorithm."""
        readings = self._reading_buffer[key]
        if not readings:
            return FusedReading(
                sensor_ids=[], value=0.0, confidence=0.0,
                variance=float("inf"), outlier_count=0,
                algorithm_used="none",
            )

        sensor_type = readings[0].sensor_type
        algorithm = self.select_algorithm(sensor_type, len(readings))

        if algorithm == "passthrough":
            result = self._algorithms.weighted_average(readings[:1])
        elif algorithm == "kalman_filter":
            tracker_id = key
            result = self._algorithms.kalman_filter(tracker_id, readings[-1])
        elif algorithm == "median":
            result = self._algorithms.median_fusion(readings)
        else:
            result = self._algorithms.weighted_average(readings)

        self._fused_results[key] = result
        self._total_fused += 1
        self._total_outliers_rejected += result.outlier_count

        logger.debug(
            "Fused %d readings for %s: value=%.2f confidence=%.2f algorithm=%s",
            len(readings), key, result.value, result.confidence, algorithm,
        )
        return result

    def _evict_old_readings(self, key: str) -> None:
        """Remove readings older than the fusion window."""
        cutoff = time.monotonic() - (self._fusion_window_ms / 1000)
        self._reading_buffer[key] = [
            r for r in self._reading_buffer[key] if r.timestamp >= cutoff
        ]

    @staticmethod
    def _buffer_key(zone_id: str, sensor_type: str) -> str:
        return f"{zone_id}:{sensor_type}"

    def sweep_stale_keys(self) -> int:
        """Remove buffer keys with no recent readings. Returns count removed."""
        cutoff = time.monotonic() - (self._fusion_window_ms / 1000)
        stale_keys = [
            k for k, readings in self._reading_buffer.items()
            if not readings or all(r.timestamp < cutoff for r in readings)
        ]
        for key in stale_keys:
            del self._reading_buffer[key]
        return len(stale_keys)

    def clear_buffer(self, zone_id: str | None = None) -> None:
        """Clear the reading buffer for a zone or all zones."""
        if zone_id:
            keys_to_remove = [k for k in self._reading_buffer if k.startswith(f"{zone_id}:")]
            for key in keys_to_remove:
                del self._reading_buffer[key]
        else:
            self._reading_buffer.clear()

    @property
    def stats(self) -> dict:
        """Fusion engine statistics for monitoring."""
        return {
            "total_fused": self._total_fused,
            "total_outliers_rejected": self._total_outliers_rejected,
            "active_buffers": len(self._reading_buffer),
            "total_readings_buffered": sum(len(v) for v in self._reading_buffer.values()),
        }
