"""Synthetic data generator — creates realistic stadium event streams for testing."""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field

from app.features.event_streaming.engine.event_bus import EventBusEvent
from app.features.event_streaming.models.event_type import EventCategory, EventSeverity


@dataclass(slots=True)
class SyntheticProfile:
    """Configuration for synthetic event generation."""

    venue_id: str
    zone_ids: list[str] = field(default_factory=list)
    sensor_ids: list[str] = field(default_factory=list)
    base_crowd_density: int = 500
    peak_multiplier: float = 3.0
    event_rate_per_second: float = 10.0
    noise_factor: float = 0.1
    is_match_day: bool = True
    match_hour: int = 20


CROWD_DENSITY_PROFILES = {
    "pre_match": {"density_range": (200, 800), "rate_multiplier": 1.5},
    "match_active": {"density_range": (3000, 80000), "rate_multiplier": 2.0},
    "halftime": {"density_range": (5000, 40000), "rate_multiplier": 3.0},
    "post_match": {"density_range": (1000, 20000), "rate_multiplier": 2.5},
    "idle": {"density_range": (50, 200), "rate_multiplier": 0.5},
}

EVENT_TEMPLATES: dict[EventCategory, list[dict]] = {
    EventCategory.CROWD: [
        {"event_type": "crowd_density_update", "severity": EventSeverity.INFO},
        {"event_type": "crowd_surge_detected", "severity": EventSeverity.HIGH},
        {"event_type": "crowd_flow_change", "severity": EventSeverity.LOW},
    ],
    EventCategory.SECURITY: [
        {"event_type": "access_control_alert", "severity": EventSeverity.MEDIUM},
        {"event_type": "perimeter_breach", "severity": EventSeverity.HIGH},
        {"event_type": "unauthorized_entry", "severity": EventSeverity.CRITICAL},
    ],
    EventCategory.MEDICAL: [
        {"event_type": "medical_assistance_requested", "severity": EventSeverity.MEDIUM},
        {"event_type": "heat_stress_alert", "severity": EventSeverity.HIGH},
        {"event_type": "mass_casualty_alert", "severity": EventSeverity.EMERGENCY},
    ],
    EventCategory.INFRASTRUCTURE: [
        {"event_type": "equipment_status_change", "severity": EventSeverity.LOW},
        {"event_type": "power_fluctuation", "severity": EventSeverity.MEDIUM},
        {"event_type": "structural_alert", "severity": EventSeverity.CRITICAL},
    ],
    EventCategory.WEATHER: [
        {"event_type": "weather_update", "severity": EventSeverity.INFO},
        {"event_type": "extreme_weather_alert", "severity": EventSeverity.HIGH},
    ],
}


class SyntheticGenerator:
    """Generates realistic synthetic stadium events for testing and demo.

    Produces events across all categories with configurable profiles
    that simulate pre-match, match, halftime, and post-match scenarios.
    """

    def __init__(self, profile: SyntheticProfile) -> None:
        self._profile = profile
        self._event_count = 0
        self._start_time = time.monotonic()

    def generate_batch(self, count: int = 10) -> list[EventBusEvent]:
        """Generate a batch of synthetic events."""
        events: list[EventBusEvent] = []
        phase = self._current_phase()

        for _ in range(count):
            category = random.choice(list(EVENT_TEMPLATES.keys()))
            template = random.choice(EVENT_TEMPLATES[category])
            zone_id = random.choice(self._profile.zone_ids) if self._profile.zone_ids else None

            payload = self._generate_payload(category, template["event_type"], phase)

            event = EventBusEvent(
                event_id=str(uuid.uuid4()),
                category=category.value,
                event_type=template["event_type"],
                payload=payload,
                venue_id=self._profile.venue_id,
                entity_id=(
                    random.choice(self._profile.sensor_ids)
                    if self._profile.sensor_ids
                    else None
                ),
                zone_id=zone_id,
                priority="normal",
                severity=template["severity"].value,
                captured_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                producer="synthetic_generator",
            )
            events.append(event)
            self._event_count += 1

        return events

    def generate_stream(self, events_per_second: float | None = None) -> list[EventBusEvent]:
        """Generate a stream of events for a 1-second window."""
        rate = events_per_second or self._profile.event_rate_per_second
        phase = self._current_phase()
        multiplier = CROWD_DENSITY_PROFILES.get(phase, {}).get("rate_multiplier", 1.0)
        count = max(1, int(rate * multiplier))
        return self.generate_batch(count)

    def _generate_payload(self, category: EventCategory, event_type: str, phase: str) -> dict:
        """Generate a realistic payload based on event type."""
        if event_type == "crowd_density_update":
            density_range = CROWD_DENSITY_PROFILES.get(phase, {}).get(
                "density_range", (100, 1000),
            )
            return {
                "crowd_density": random.randint(*density_range),
                "zone_utilization": round(random.uniform(0.1, 1.0), 2),
                "flow_direction": random.choice(["inbound", "outbound", "static"]),
            }

        if "temperature" in event_type or "heat" in event_type:
            return {
                "temperature_celsius": round(random.uniform(15.0, 45.0), 1),
                "heat_index": round(random.uniform(15.0, 55.0), 1),
                "humidity_percent": round(random.uniform(20.0, 95.0), 1),
            }

        if "security" in category.value or "access" in event_type:
            return {
                "gate_id": f"gate_{random.randint(1, 20)}",
                "access_type": random.choice(["entry", "exit", "restricted"]),
                "credential_type": random.choice(["rfid", "nfc", "biometric"]),
            }

        return {
            "value": round(random.uniform(0.0, 100.0), 2),
            "unit": "generic",
            "source": "synthetic",
        }

    def _current_phase(self) -> str:
        """Determine the current match phase for realistic event generation."""
        if not self._profile.is_match_day:
            return "idle"

        elapsed = time.monotonic() - self._start_time
        if elapsed < 1800:
            return "pre_match"
        if elapsed < 5400:
            return "match_active"
        if elapsed < 6300:
            return "halftime"
        return "post_match"

    @property
    def stats(self) -> dict:
        elapsed = time.monotonic() - self._start_time
        return {
            "total_generated": self._event_count,
            "elapsed_seconds": round(elapsed, 1),
            "events_per_second": round(self._event_count / max(elapsed, 0.001), 1),
            "phase": self._current_phase(),
        }
