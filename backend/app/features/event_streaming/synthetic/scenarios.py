"""Predefined synthetic scenarios for testing and demo."""

from __future__ import annotations

from dataclasses import dataclass

from app.features.event_streaming.synthetic.generator import SyntheticProfile


@dataclass(frozen=True)
class StadiumScenario:
    """A predefined scenario with venue configuration and event profiles."""

    name: str
    description: str
    venue_id: str
    zone_ids: list[str]
    sensor_ids: list[str]
    profile: SyntheticProfile


def create_world_cup_scenario(venue_id: str) -> StadiumScenario:
    """FIFA World Cup 2026 match day scenario with 80K capacity."""
    zones = [f"zone_{i}" for i in range(1, 13)]
    sensors = [f"sensor_{i}" for i in range(1, 51)]

    profile = SyntheticProfile(
        venue_id=venue_id,
        zone_ids=zones,
        sensor_ids=sensors,
        base_crowd_density=5000,
        peak_multiplier=4.0,
        event_rate_per_second=50.0,
        noise_factor=0.15,
        is_match_day=True,
        match_hour=20,
    )

    return StadiumScenario(
        name="FIFA World Cup 2026 - Match Day",
        description="Full stadium with 80K fans, all sensors active, high event throughput",
        venue_id=venue_id,
        zone_ids=zones,
        sensor_ids=sensors,
        profile=profile,
    )


def create_emergency_scenario(venue_id: str) -> StadiumScenario:
    """Emergency evacuation scenario with high-priority events."""
    zones = [f"zone_{i}" for i in range(1, 7)]
    sensors = [f"sensor_{i}" for i in range(1, 21)]

    profile = SyntheticProfile(
        venue_id=venue_id,
        zone_ids=zones,
        sensor_ids=sensors,
        base_crowd_density=30000,
        peak_multiplier=1.0,
        event_rate_per_second=100.0,
        noise_factor=0.05,
        is_match_day=True,
        match_hour=20,
    )

    return StadiumScenario(
        name="Emergency Evacuation",
        description="Simulated emergency with evacuation orders and crowd flow changes",
        venue_id=venue_id,
        zone_ids=zones,
        sensor_ids=sensors,
        profile=profile,
    )


def create_sensor_failure_scenario(venue_id: str) -> StadiumScenario:
    """Scenario with intermittent sensor failures and data gaps."""
    zones = [f"zone_{i}" for i in range(1, 5)]
    sensors = [f"sensor_{i}" for i in range(1, 11)]

    profile = SyntheticProfile(
        venue_id=venue_id,
        zone_ids=zones,
        sensor_ids=sensors,
        base_crowd_density=1000,
        peak_multiplier=2.0,
        event_rate_per_second=20.0,
        noise_factor=0.4,
        is_match_day=False,
        match_hour=14,
    )

    return StadiumScenario(
        name="Sensor Failure",
        description="Degraded sensor network with high noise and intermittent failures",
        venue_id=venue_id,
        zone_ids=zones,
        sensor_ids=sensors,
        profile=profile,
    )


SCENARIO_REGISTRY: dict[str, StadiumScenario] = {}


def register_scenario(scenario: StadiumScenario) -> None:
    """Register a scenario in the global registry."""
    SCENARIO_REGISTRY[scenario.name] = scenario


def get_scenario(name: str) -> StadiumScenario | None:
    """Retrieve a scenario by name."""
    return SCENARIO_REGISTRY.get(name)


def list_scenarios() -> list[str]:
    """List all registered scenario names."""
    return list(SCENARIO_REGISTRY.keys())
