"""Tests for the sensor fusion engine and algorithms."""

from __future__ import annotations

from app.features.event_streaming.fusion.algorithms import (
    FusionAlgorithms,
    SensorReading,
)
from app.features.event_streaming.fusion.engine import FusionEngine


def _reading(
    sensor_id: str = "sensor-1",
    value: float = 25.0,
    accuracy: float = 0.9,
    sensor_type: str = "temperature",
    zone_id: str | None = "zone-1",
) -> SensorReading:
    import time
    return SensorReading(
        sensor_id=sensor_id,
        sensor_type=sensor_type,
        value=value,
        accuracy=accuracy,
        timestamp=time.monotonic(),
        zone_id=zone_id,
    )


class TestFusionAlgorithms:
    def test_weighted_average_single_reading(self) -> None:
        alg = FusionAlgorithms()
        r = _reading(value=30.0, accuracy=0.9)
        result = alg.weighted_average([r])
        assert result.value == 30.0
        assert result.confidence == 0.9

    def test_weighted_average_multiple_readings(self) -> None:
        alg = FusionAlgorithms()
        readings = [
            _reading(sensor_id="s1", value=20.0, accuracy=0.8),
            _reading(sensor_id="s2", value=30.0, accuracy=0.9),
        ]
        result = alg.weighted_average(readings)
        expected = (20.0 * 0.8 + 30.0 * 0.9) / (0.8 + 0.9)
        assert abs(result.value - expected) < 0.01
        assert len(result.sensor_ids) == 2

    def test_weighted_average_empty(self) -> None:
        alg = FusionAlgorithms()
        result = alg.weighted_average([])
        assert result.value == 0.0
        assert result.confidence == 0.0

    def test_kalman_filter_first_reading(self) -> None:
        alg = FusionAlgorithms()
        r = _reading(value=25.0)
        result = alg.kalman_filter("tracker-1", r)
        assert result.value == 25.0
        assert result.algorithm_used == "kalman_filter"

    def test_kalman_filter_convergence(self) -> None:
        alg = FusionAlgorithms()
        for i in range(10):
            r = _reading(value=25.0 + (i % 2) * 0.1)
            result = alg.kalman_filter("tracker-2", r)
        assert abs(result.value - 25.05) < 0.5

    def test_median_fusion(self) -> None:
        alg = FusionAlgorithms()
        readings = [
            _reading(sensor_id="s1", value=10.0),
            _reading(sensor_id="s2", value=20.0),
            _reading(sensor_id="s3", value=30.0),
        ]
        result = alg.median_fusion(readings)
        assert result.value == 20.0

    def test_reject_outliers(self) -> None:
        alg = FusionAlgorithms()
        readings = [
            _reading(sensor_id="s1", value=20.0),
            _reading(sensor_id="s2", value=21.0),
            _reading(sensor_id="s3", value=20.5),
            _reading(sensor_id="s4", value=100.0),
        ]
        result = alg.weighted_average(readings)
        assert result.outlier_count >= 1

    def test_reset_tracker(self) -> None:
        alg = FusionAlgorithms()
        r = _reading(value=25.0)
        alg.kalman_filter("tracker-3", r)
        alg.reset_tracker("tracker-3")
        assert "tracker-3" not in alg._kalman_states


class TestFusionEngine:
    def test_add_reading_below_threshold(self) -> None:
        engine = FusionEngine(min_sensors=3)
        r = _reading()
        result = engine.add_reading(r)
        assert result is None

    def test_add_reading_triggers_fusion(self) -> None:
        engine = FusionEngine(min_sensors=2)
        engine.add_reading(_reading(sensor_id="s1", value=20.0))
        result = engine.add_reading(_reading(sensor_id="s2", value=22.0))
        assert result is not None
        assert abs(result.value - 21.0) < 1.0

    def test_get_fused_result(self) -> None:
        engine = FusionEngine(min_sensors=2)
        engine.add_reading(_reading(sensor_id="s1", value=20.0))
        engine.add_reading(_reading(sensor_id="s2", value=22.0))
        result = engine.get_fused_result("zone-1", "temperature")
        assert result is not None

    def test_select_algorithm(self) -> None:
        engine = FusionEngine()
        assert engine.select_algorithm("temperature", 3) == "weighted_average"
        assert engine.select_algorithm("density_camera", 5) == "kalman_filter"
        assert engine.select_algorithm("noise_level", 6) == "median"
        assert engine.select_algorithm("unknown", 1) == "passthrough"

    def test_clear_buffer(self) -> None:
        engine = FusionEngine(min_sensors=2)
        engine.add_reading(_reading())
        engine.clear_buffer("zone-1")
        assert len(engine._reading_buffer) == 0

    def test_stats(self) -> None:
        engine = FusionEngine(min_sensors=2)
        engine.add_reading(_reading(sensor_id="s1", value=20.0))
        engine.add_reading(_reading(sensor_id="s2", value=22.0))
        stats = engine.stats
        assert stats["total_fused"] == 1
