"""Sensor fusion algorithms — Kalman filter, weighted average, outlier rejection."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_KALMAN_PROCESS_NOISE = 0.01
DEFAULT_KALMAN_MEASUREMENT_NOISE = 0.1
DEFAULT_OUTLIER_THRESHOLD_SIGMA = 3.0


@dataclass(slots=True)
class FusedReading:
    """Result of fusing multiple sensor readings into a single value."""

    sensor_ids: list[str]
    value: float
    confidence: float
    variance: float
    outlier_count: int
    algorithm_used: str


@dataclass(slots=True)
class SensorReading:
    """A single sensor reading with metadata for fusion."""

    sensor_id: str
    sensor_type: str
    value: float
    accuracy: float
    timestamp: float
    zone_id: str | None = None


@dataclass(slots=True)
class KalmanState:
    """Internal state for a Kalman filter tracker."""

    estimate: float = 0.0
    variance: float = 1.0
    initialized: bool = False


class FusionAlgorithms:
    """Collection of sensor fusion algorithms for combining noisy readings."""

    def __init__(
        self,
        outlier_threshold_sigma: float = DEFAULT_OUTLIER_THRESHOLD_SIGMA,
    ) -> None:
        self._outlier_threshold = outlier_threshold_sigma
        self._kalman_states: dict[str, KalmanState] = {}

    def weighted_average(self, readings: list[SensorReading]) -> FusedReading:
        """Fuse readings using accuracy-weighted average.

        Higher accuracy sensors contribute more to the final value.
        Returns FusedReading with confidence proportional to agreement.
        """
        if not readings:
            return FusedReading(
                sensor_ids=[], value=0.0, confidence=0.0,
                variance=float("inf"), outlier_count=0,
                algorithm_used="weighted_average",
            )

        if len(readings) == 1:
            return FusedReading(
                sensor_ids=[readings[0].sensor_id],
                value=readings[0].value,
                confidence=readings[0].accuracy,
                variance=1.0 - readings[0].accuracy,
                outlier_count=0,
                algorithm_used="weighted_average",
            )

        clean = self._reject_outliers(readings)
        outlier_count = len(readings) - len(clean)

        if not clean:
            clean = readings

        total_weight = sum(r.accuracy for r in clean)
        if total_weight == 0:
            return FusedReading(
                sensor_ids=[r.sensor_id for r in clean],
                value=sum(r.value for r in clean) / len(clean),
                confidence=0.0, variance=float("inf"),
                outlier_count=outlier_count,
                algorithm_used="weighted_average",
            )

        fused_value = sum(r.value * r.accuracy for r in clean) / total_weight
        confidence = total_weight / len(clean)
        variance = self._compute_variance(clean, fused_value)

        return FusedReading(
            sensor_ids=[r.sensor_id for r in clean],
            value=fused_value,
            confidence=min(confidence, 1.0),
            variance=variance,
            outlier_count=outlier_count,
            algorithm_used="weighted_average",
        )

    def kalman_filter(
        self,
        tracker_id: str,
        reading: SensorReading,
        process_noise: float = DEFAULT_KALMAN_PROCESS_NOISE,
        measurement_noise: float = DEFAULT_KALMAN_MEASUREMENT_NOISE,
    ) -> FusedReading:
        """Apply a simple 1D Kalman filter to a sequential reading.

        Maintains state across calls via tracker_id. Ideal for tracking
        a single sensor's value over time.
        """
        state = self._kalman_states.get(tracker_id, KalmanState())

        if not state.initialized:
            state.estimate = reading.value
            state.variance = measurement_noise
            state.initialized = True
        else:
            prediction_variance = state.variance + process_noise
            kalman_gain = prediction_variance / (prediction_variance + measurement_noise)
            state.estimate = state.estimate + kalman_gain * (reading.value - state.estimate)
            state.variance = (1 - kalman_gain) * prediction_variance

        self._kalman_states[tracker_id] = state
        confidence = max(0.0, 1.0 - state.variance)

        return FusedReading(
            sensor_ids=[reading.sensor_id],
            value=state.estimate,
            confidence=confidence,
            variance=state.variance,
            outlier_count=0,
            algorithm_used="kalman_filter",
        )

    def median_fusion(self, readings: list[SensorReading]) -> FusedReading:
        """Fuse readings using median — robust against outlier sensors."""
        if not readings:
            return FusedReading(
                sensor_ids=[], value=0.0, confidence=0.0,
                variance=float("inf"), outlier_count=0,
                algorithm_used="median",
            )

        sorted_values = sorted(readings, key=lambda r: r.value)
        mid = len(sorted_values) // 2

        if len(sorted_values) % 2 == 0:
            median_val = (sorted_values[mid - 1].value + sorted_values[mid].value) / 2
        else:
            median_val = sorted_values[mid].value

        close = [r for r in readings if abs(r.value - median_val) < median_val * 0.1]
        confidence = len(close) / len(readings) if readings else 0.0

        return FusedReading(
            sensor_ids=[r.sensor_id for r in readings],
            value=median_val,
            confidence=confidence,
            variance=self._compute_variance(readings, median_val),
            outlier_count=0,
            algorithm_used="median",
        )

    def _reject_outliers(self, readings: list[SensorReading]) -> list[SensorReading]:
        """Remove readings that are more than threshold MAD from the median."""
        if len(readings) < 3:
            return readings

        sorted_vals = sorted(r.value for r in readings)
        n = len(sorted_vals)
        mid_idx = n // 2
        if n % 2:
            median = sorted_vals[mid_idx]
        else:
            median = (sorted_vals[mid_idx - 1] + sorted_vals[mid_idx]) / 2

        deviations = [abs(r.value - median) for r in readings]
        mad = sorted(deviations)[n // 2]

        if mad == 0:
            return readings

        return [
            r for r in readings
            if abs(r.value - median) <= self._outlier_threshold * mad
        ]

    @staticmethod
    def _compute_variance(readings: list[SensorReading], mean: float) -> float:
        """Compute variance of reading values around a mean."""
        if len(readings) < 2:
            return 0.0
        return sum((r.value - mean) ** 2 for r in readings) / (len(readings) - 1)

    def reset_tracker(self, tracker_id: str) -> None:
        """Reset a Kalman filter tracker's state."""
        self._kalman_states.pop(tracker_id, None)
