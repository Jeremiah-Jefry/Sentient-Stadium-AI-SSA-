"""Tests for confidence computation and sensor agreement."""
from __future__ import annotations

import math

from app.features.ai_intelligence.confidence.confidence_engine import (
    FRESHNESS_HALF_LIFE_SECONDS,
    ConfidenceBreakdown,
    ConfidenceEngine,
)


class TestConfidenceEngine:
    """Tests for the ConfidenceEngine weighted geometric mean computation."""

    def setup_method(self) -> None:
        self.engine = ConfidenceEngine()

    def test_high_confidence_all_strong(self) -> None:
        """All strong signals should yield confidence > 0.7."""
        result = self.engine.compute_confidence(
            sensor_agreement=0.95,
            historical_similarity=0.90,
            model_agreement=0.92,
            data_freshness=0.95,
            evidence_count=20,
        )
        assert result.overall > 0.7, (
            f"Expected high confidence with all strong signals, got {result.overall}"
        )

    def test_low_confidence_weak_sensor(self) -> None:
        """Weak sensor agreement should significantly reduce confidence."""
        strong = self.engine.compute_confidence(
            sensor_agreement=0.95,
            historical_similarity=0.90,
            model_agreement=0.92,
            data_freshness=0.95,
            evidence_count=20,
        )
        weak = self.engine.compute_confidence(
            sensor_agreement=0.10,
            historical_similarity=0.90,
            model_agreement=0.92,
            data_freshness=0.95,
            evidence_count=20,
        )
        assert weak.overall < strong.overall, (
            f"Weak sensors should reduce confidence: weak={weak.overall} vs strong={strong.overall}"
        )
        assert weak.overall < 0.6, (
            f"Weak sensor agreement should bring confidence below 0.6, got {weak.overall}"
        )

    def test_geometric_mean_not_arithmetic(self) -> None:
        """One very low factor should drag down overall more than arithmetic mean."""
        result = self.engine.compute_confidence(
            sensor_agreement=0.01,
            historical_similarity=0.95,
            model_agreement=0.95,
            data_freshness=0.95,
            evidence_count=20,
        )
        values = [0.01, 0.95, 0.95, 0.95, self.engine._evidence_score(20)]
        weights = [0.25, 0.20, 0.25, 0.15, 0.15]
        total_weight = sum(weights)
        log_sum = sum(w * math.log(max(v, 1e-9)) for w, v in zip(weights, values))
        expected_geometric = math.exp(log_sum / total_weight)
        assert abs(result.overall - round(expected_geometric, 4)) < 0.01

    def test_minimum_evidence_threshold(self) -> None:
        """Very few evidence points should cap confidence."""
        result = self.engine.compute_confidence(
            sensor_agreement=0.9,
            historical_similarity=0.9,
            model_agreement=0.9,
            data_freshness=0.9,
            evidence_count=1,
        )
        result_many = self.engine.compute_confidence(
            sensor_agreement=0.9,
            historical_similarity=0.9,
            model_agreement=0.9,
            data_freshness=0.9,
            evidence_count=20,
        )
        assert result.overall < result_many.overall

    def test_bounds_check(self) -> None:
        """Confidence must always be between 0.0 and 1.0."""
        edge_cases = [
            (0.0, 0.0, 0.0, 0.0, 0),
            (1.0, 1.0, 1.0, 1.0, 100),
            (0.0, 0.0, 0.0, 0.0, 0),
        ]
        for s, h, m, f, e in edge_cases:
            result = self.engine.compute_confidence(s, h, m, f, e)
            assert 0.0 <= result.overall <= 1.0, (
                f"Confidence out of bounds: {result.overall} for inputs ({s},{h},{m},{f},{e})"
            )

    def test_breakdown_has_all_fields(self) -> None:
        """ConfidenceBreakdown should contain all component scores."""
        result = self.engine.compute_confidence(0.8, 0.7, 0.9, 0.85, 10)
        assert isinstance(result, ConfidenceBreakdown)
        assert result.sensor_agreement == 0.8
        assert result.historical_similarity == 0.7
        assert result.model_agreement == 0.9
        assert result.data_freshness == 0.85
        assert result.evidence_count == 10

    def test_reasoning_populated(self) -> None:
        """Breakdown should contain reasoning for extreme values."""
        result = self.engine.compute_confidence(0.95, 0.95, 0.95, 0.95, 20)
        assert len(result.reasoning) > 0
        assert "sensor_agreement" in result.reasoning

    def test_evidence_score_zero(self) -> None:
        """Zero evidence should yield zero evidence score."""
        score = self.engine._evidence_score(0)
        assert score == 0.0

    def test_evidence_score_diminishing_returns(self) -> None:
        """Evidence score should have diminishing returns."""
        score_5 = self.engine._evidence_score(5)
        score_10 = self.engine._evidence_score(10)
        score_50 = self.engine._evidence_score(50)
        assert score_5 < score_10 < score_50
        assert score_50 < 1.0


class TestSensorAgreement:
    """Tests for the sensor agreement computation."""

    def setup_method(self) -> None:
        self.engine = ConfidenceEngine()

    def test_identical_readings(self) -> None:
        """Identical readings should yield perfect agreement (1.0)."""
        readings = [{"value": 42.0}, {"value": 42.0}, {"value": 42.0}]
        agreement = self.engine.compute_sensor_agreement(readings)
        assert agreement == 1.0, f"Identical readings should yield 1.0, got {agreement}"

    def test_divergent_readings(self) -> None:
        """Divergent readings should yield low agreement."""
        readings = [{"value": 0.0}, {"value": 100.0}]
        agreement = self.engine.compute_sensor_agreement(readings)
        assert agreement < 0.5, f"Divergent readings should yield low agreement, got {agreement}"

    def test_single_reading(self) -> None:
        """Single reading should return 0.5 (no disagreement possible)."""
        agreement = self.engine.compute_sensor_agreement([{"value": 50.0}])
        assert agreement == 0.5

    def test_all_zero_readings(self) -> None:
        """All zero readings should yield 1.0 (perfect agreement at zero)."""
        readings = [{"value": 0.0}, {"value": 0.0}]
        agreement = self.engine.compute_sensor_agreement(readings)
        assert agreement == 1.0

    def test_empty_readings(self) -> None:
        """Empty readings should return 0.5 (single-reading path)."""
        agreement = self.engine.compute_sensor_agreement([])
        assert agreement == 0.5

    def test_close_readings_high_agreement(self) -> None:
        """Close readings should yield high agreement."""
        readings = [{"value": 49.0}, {"value": 50.0}, {"value": 51.0}]
        agreement = self.engine.compute_sensor_agreement(readings)
        assert agreement > 0.9, f"Close readings should yield high agreement, got {agreement}"


class TestHistoricalSimilarity:
    """Tests for historical pattern comparison."""

    def setup_method(self) -> None:
        self.engine = ConfidenceEngine()

    def test_exact_match(self) -> None:
        """Exact pattern match should yield high similarity."""
        current = {"density": 0.8, "flow_rate": 50.0}
        patterns = [{"density": 0.8, "flow_rate": 50.0}]
        sim = self.engine.compute_historical_similarity(current, patterns)
        assert sim > 0.95

    def test_no_patterns(self) -> None:
        """No historical patterns should return 0.3."""
        sim = self.engine.compute_historical_similarity({"density": 0.5}, [])
        assert sim == 0.3

    def test_no_common_keys(self) -> None:
        """No overlapping numeric keys should return 0.0."""
        current = {"foo": 1.0}
        patterns = [{"bar": 1.0}]
        sim = self.engine.compute_historical_similarity(current, patterns)
        assert sim == 0.0


class TestDataFreshness:
    """Tests for data freshness scoring."""

    def setup_method(self) -> None:
        self.engine = ConfidenceEngine()

    def test_fresh_data(self) -> None:
        """Very recent data should yield high freshness."""
        freshness = self.engine.compute_data_freshness(
            data_timestamps=[100.0, 101.0, 102.0],
            current_time=103.0,
        )
        assert freshness > 0.9

    def test_stale_data(self) -> None:
        """Old data should yield low freshness."""
        freshness = self.engine.compute_data_freshness(
            data_timestamps=[0.0, 1.0],
            current_time=600.0,
        )
        assert freshness < 0.1

    def test_empty_timestamps(self) -> None:
        """No timestamps should return 0.0."""
        freshness = self.engine.compute_data_freshness([], current_time=100.0)
        assert freshness == 0.0

    def test_half_life(self) -> None:
        """Data at half-life age should yield ~0.5 freshness."""
        freshness = self.engine.compute_data_freshness(
            data_timestamps=[0.0],
            current_time=FRESHNESS_HALF_LIFE_SECONDS,
        )
        assert 0.45 < freshness < 0.55
