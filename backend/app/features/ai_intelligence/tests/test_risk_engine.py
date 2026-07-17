"""Tests for the risk engine and individual risk factor calculators."""
from __future__ import annotations

import pytest

from app.features.ai_intelligence.models.enums import RiskLevel
from app.features.ai_intelligence.risk.risk_engine import (
    RiskAssessmentResult,
    RiskEngine,
)
from app.features.ai_intelligence.risk.risk_factors import (
    RiskFactorCalculator,
    density_risk,
    flow_risk,
    medical_risk,
    transport_risk,
    volunteer_risk,
    weather_risk,
)


class TestRiskFactors:
    """Unit tests for individual risk factor calculators."""

    def test_density_risk_low(self) -> None:
        """Low density should yield low risk."""
        result = density_risk(density_value=100.0, capacity=1000.0)
        assert result < 0.3, f"Expected low risk for 10% density, got {result}"

    def test_density_risk_at_capacity(self) -> None:
        """At DENSITY_HALF_RISK midpoint the sigmoid yields ~0.5."""
        result = density_risk(density_value=700.0, capacity=1000.0)
        assert abs(result - 0.5) < 0.05, f"Expected ~0.5 risk at midpoint ratio, got {result}"

    def test_density_risk_over_capacity(self) -> None:
        """Over capacity should yield high risk (>0.9)."""
        result = density_risk(density_value=1000.0, capacity=1000.0)
        assert result > 0.9, f"Expected high risk at 100% capacity, got {result}"

    def test_density_risk_zero_capacity(self) -> None:
        """Zero capacity should return 1.0 (maximum risk)."""
        result = density_risk(density_value=0.0, capacity=0.0)
        assert result == 1.0

    def test_weather_risk_sunny(self) -> None:
        """Good weather should yield minimal risk (<0.25)."""
        weather = {
            "rain_intensity": 0,
            "wind_speed_kmh": 0,
            "heat_index": 0,
            "cold_index": 0,
        }
        result = weather_risk(weather)
        assert result < 0.25, f"Expected low weather risk, got {result}"

    def test_weather_risk_heavy_rain(self) -> None:
        """Heavy rain should yield significant risk."""
        weather = {
            "rain_intensity": 90,
            "wind_speed_kmh": 10,
            "heat_index": 0,
            "cold_index": 0,
        }
        result = weather_risk(weather)
        assert result > 0.5, f"Expected significant weather risk from heavy rain, got {result}"

    def test_weather_risk_missing_keys(self) -> None:
        """Missing weather keys should default to 0 contribution."""
        result = weather_risk({})
        assert 0.0 <= result <= 1.0

    def test_medical_risk_no_events(self) -> None:
        """No medical events should yield minimal risk."""
        result = medical_risk([], medical_capacity=10)
        assert result < 0.15, f"Expected low medical risk with no events, got {result}"

    def test_medical_risk_many_events(self) -> None:
        """Many medical events with low capacity should yield high risk."""
        events = [{"severity": 5}] * 20
        result = medical_risk(events, medical_capacity=5)
        assert result > 0.7, f"Expected high medical risk, got {result}"

    def test_medical_risk_zero_capacity(self) -> None:
        """Zero capacity should return 1.0."""
        result = medical_risk([{"severity": 1}], medical_capacity=0)
        assert result == 1.0

    def test_transport_risk_no_delays(self) -> None:
        """No delays should yield low risk (sigmoid midpoint yields ~0.23)."""
        result = transport_risk([], expected_arrivals=100)
        assert result < 0.3, f"Expected low transport risk with no delays, got {result}"

    def test_transport_risk_many_delays(self) -> None:
        """Many long delays should yield high risk."""
        delays = [{"delay_minutes": 45}] * 50
        result = transport_risk(delays, expected_arrivals=100)
        assert result > 0.5, f"Expected high transport risk, got {result}"

    def test_transport_risk_zero_arrivals(self) -> None:
        """Zero expected arrivals should return 0.0."""
        result = transport_risk([{"delay_minutes": 30}], expected_arrivals=0)
        assert result == 0.0

    def test_all_risk_factors_bounded(self) -> None:
        """All risk factors must return values between 0.0 and 1.0."""
        calc = RiskFactorCalculator()
        extreme_inputs = [
            calc.density(0.0, 0.0),
            calc.density(999999, 1),
            calc.flow(0, 1000),
            calc.flow(1000, 1000),
            calc.weather({
                "rain_intensity": 100, "wind_speed_kmh": 100,
                "heat_index": 100, "cold_index": 100,
            }),
            calc.medical([{"severity": 5}] * 100, 1),
            calc.security([{"severity": 5}] * 100),
            calc.accessibility(100, 1, 50),
            calc.transport([{"delay_minutes": 120}] * 100, 10),
            calc.volunteer(0, 1000),
            calc.equipment(1000, 1),
            calc.match_context("penalty_shootout", 0, 0),
        ]
        for val in extreme_inputs:
            assert 0.0 <= val <= 1.0, f"Risk factor out of bounds: {val}"

    def test_volunteer_risk充足的volunteers(self) -> None:
        """Sufficient volunteers should yield low risk."""
        result = volunteer_risk(volunteers_available=100, volunteers_needed=50)
        assert result < 0.2, f"Expected low volunteer risk with surplus, got {result}"

    def test_volunteer_risk_shortage(self) -> None:
        """Volunteer shortage should yield high risk."""
        result = volunteer_risk(volunteers_available=10, volunteers_needed=100)
        assert result > 0.8, f"Expected high volunteer risk with shortage, got {result}"

    def test_volunteer_risk_zero_needed(self) -> None:
        """Zero needed should return 0.0."""
        result = volunteer_risk(volunteers_available=0, volunteers_needed=0)
        assert result == 0.0

    def test_flow_risk_normal(self) -> None:
        """Flow at expected level — deficit is 0, sigmoid at midpoint yields ~0.5."""
        result = flow_risk(flow_rate=100.0, expected_flow=100.0)
        assert result <= 0.55, (
            f"Expected moderate flow risk when flow matches expected, got {result}"
        )

    def test_flow_risk_restricted(self) -> None:
        """Severely restricted flow should yield high risk."""
        result = flow_risk(flow_rate=10.0, expected_flow=100.0)
        assert result > 0.5, f"Expected high flow risk with restricted flow, got {result}"


class TestRiskEngine:
    """Integration tests for the RiskEngine."""

    @pytest.mark.asyncio
    async def test_assess_risk_green(self) -> None:
        """All low factors should produce GREEN risk."""
        engine = RiskEngine()
        context = {
            "density": 50.0,
            "capacity": 10000.0,
            "flow_rate": 100.0,
            "expected_flow": 100.0,
            "weather": {"rain_intensity": 0, "wind_speed_kmh": 0},
            "medical_events": [],
            "medical_capacity": 10,
            "security_events": [],
            "volunteers_available": 200,
            "volunteers_needed": 100,
            "offline_sensors": 0,
            "total_sensors": 50,
        }
        result = await engine.assess_risk(context)
        assert result.risk_level == RiskLevel.GREEN
        assert result.risk_score < 0.25

    @pytest.mark.asyncio
    async def test_assess_risk_critical(self) -> None:
        """Multiple high factors should produce CRITICAL risk."""
        engine = RiskEngine()
        context = {
            "density": 10000.0,
            "capacity": 100.0,
            "flow_rate": 1.0,
            "expected_flow": 100.0,
            "weather": {
                "rain_intensity": 100, "wind_speed_kmh": 100,
                "heat_index": 100, "cold_index": 100,
            },
            "medical_events": [{"severity": 5}] * 50,
            "medical_capacity": 1,
            "security_events": [{"severity": 5}] * 20,
            "volunteers_available": 0,
            "volunteers_needed": 500,
            "offline_sensors": 100,
            "total_sensors": 100,
            "match_phase": "penalty_shootout",
            "score_diff": 0,
            "minutes_remaining": 2,
            "transport_delays": [{"delay_minutes": 120}] * 50,
            "expected_arrivals": 50,
            "blocked_paths": 100,
            "total_paths": 100,
            "wheelchair_users": 50,
        }
        result = await engine.assess_risk(context)
        assert result.risk_level in (RiskLevel.RED, RiskLevel.CRITICAL)
        assert result.risk_score > 0.75

    @pytest.mark.asyncio
    async def test_assess_risk_returns_all_domains(self) -> None:
        """Risk assessment should include all domain risk scores."""
        engine = RiskEngine()
        result = await engine.assess_risk({})
        assert isinstance(result, RiskAssessmentResult)
        expected_keys = {
            "density", "flow", "weather", "medical", "security",
            "accessibility", "transport", "volunteer", "equipment", "match_context",
        }
        assert set(result.risk_factors.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_score_to_level_boundaries(self) -> None:
        """Test boundary conditions for risk level mapping."""
        engine = RiskEngine()

        thresholds = [
            (0.0, RiskLevel.GREEN),
            (0.10, RiskLevel.GREEN),
            (0.25, RiskLevel.YELLOW),
            (0.40, RiskLevel.YELLOW),
            (0.50, RiskLevel.ORANGE),
            (0.70, RiskLevel.ORANGE),
            (0.75, RiskLevel.RED),
            (0.85, RiskLevel.RED),
            (0.90, RiskLevel.CRITICAL),
            (0.99, RiskLevel.CRITICAL),
        ]
        for score, expected_level in thresholds:
            level = engine._score_to_level(score)
            assert level == expected_level, (
                f"Score {score} should map to {expected_level}, got {level}"
            )

    @pytest.mark.asyncio
    async def test_contributing_events_tracked(self) -> None:
        """Risk assessment should track contributing event IDs."""
        engine = RiskEngine()
        event_ids = ["evt-001", "evt-002", "evt-003"]
        context = {"contributing_event_ids": event_ids}
        result = await engine.assess_risk(context)
        assert result.contributing_events == event_ids

    @pytest.mark.asyncio
    async def test_custom_weights(self) -> None:
        """Custom weights should override defaults."""
        custom_weights = {"density": 1.0}
        engine = RiskEngine(weights=custom_weights)
        result = await engine.assess_risk({})
        assert isinstance(result.risk_level, RiskLevel)

    @pytest.mark.asyncio
    async def test_assessment_count_increments(self) -> None:
        """Stats should track the number of assessments."""
        engine = RiskEngine()
        assert engine.stats["assessments_count"] == 0
        await engine.assess_risk({})
        assert engine.stats["assessments_count"] == 1
        await engine.assess_risk({})
        assert engine.stats["assessments_count"] == 2
