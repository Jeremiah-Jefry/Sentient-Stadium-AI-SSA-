"""Dynamic weight engine — computes edge weights from realtime conditions.

Consumes context from:
- Module 3 EventBus (crowd density, incidents, weather)
- Module 4 AI Intelligence (risk scores, predictions)
- Module 2 Digital Twin (entity status, capacity)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.features.navigation.graph.models import WeightContext


@dataclass
class CrowdState:
    """Current crowd density state for a zone or edge."""

    density: float = 0.0
    flow_rate: float = 0.0
    predicted_density_5m: float = 0.0
    predicted_density_15m: float = 0.0
    trend: str = "stable"
    updated_at: float = 0.0


@dataclass
class WeatherState:
    """Current weather conditions affecting navigation."""

    rain_intensity: float = 0.0
    wind_speed_kmh: float = 0.0
    heat_index: float = 0.0
    visibility: float = 1.0
    updated_at: float = 0.0


@dataclass
class IncidentState:
    """Active incident affecting navigation."""

    incident_type: str = ""
    severity: float = 0.0
    zone_id: str = ""
    affected_edges: list[str] = field(default_factory=list)
    updated_at: float = 0.0


@dataclass
class InfrastructureState:
    """Status of vertical connectors and pathways."""

    escalator_status: dict[str, bool] = field(default_factory=dict)
    elevator_status: dict[str, bool] = field(default_factory=dict)
    closed_corridors: set[str] = field(default_factory=set)
    maintenance_zones: set[str] = field(default_factory=set)


class DynamicWeightEngine:
    """Computes WeightContext from aggregated realtime conditions.

    Maintains internal state buffers that are updated by the EventBus
    consumer. Weight computation is purely functional given the current state.
    """

    def __init__(self) -> None:
        self._crowd_states: dict[str, CrowdState] = {}
        self._weather = WeatherState()
        self._incidents: list[IncidentState] = []
        self._infrastructure = InfrastructureState()
        self._risk_scores: dict[str, float] = {}
        self._last_update: float = 0.0

    def update_crowd_density(
        self,
        zone_id: str,
        density: float,
        flow_rate: float = 0.0,
        predicted_5m: float | None = None,
        predicted_15m: float | None = None,
    ) -> None:
        now = time.monotonic()
        existing = self._crowd_states.get(zone_id)
        if existing:
            existing.density = density
            existing.flow_rate = flow_rate
            if predicted_5m is not None:
                existing.predicted_density_5m = predicted_5m
            if predicted_15m is not None:
                existing.predicted_density_15m = predicted_15m
            existing.updated_at = now
        else:
            self._crowd_states[zone_id] = CrowdState(
                density=density,
                flow_rate=flow_rate,
                predicted_density_5m=(
                    predicted_5m if predicted_5m is not None
                    else density
                ),
                predicted_density_15m=(
                    predicted_15m if predicted_15m is not None
                    else density
                ),
                updated_at=now,
            )
        self._last_update = now

    def update_weather(
        self,
        rain: float = 0.0,
        wind: float = 0.0,
        heat: float = 0.0,
        visibility: float = 1.0,
    ) -> None:
        self._weather = WeatherState(
            rain_intensity=rain,
            wind_speed_kmh=wind,
            heat_index=heat,
            visibility=visibility,
            updated_at=time.monotonic(),
        )
        self._last_update = time.monotonic()

    def add_incident(self, incident: IncidentState) -> None:
        self._incidents.append(incident)
        self._last_update = time.monotonic()

    def remove_incident(self, incident_type: str, zone_id: str) -> None:
        self._incidents = [
            i for i in self._incidents
            if not (i.incident_type == incident_type and i.zone_id == zone_id)
        ]
        self._last_update = time.monotonic()

    def update_infrastructure(self, infra: InfrastructureState) -> None:
        self._infrastructure = infra
        self._last_update = time.monotonic()

    def update_risk_score(self, zone_id: str, score: float) -> None:
        self._risk_scores[zone_id] = score
        self._last_update = time.monotonic()

    def build_context(
        self,
        zone_id: str | None = None,
        edge_types: list[str] | None = None,
    ) -> WeightContext:
        """Build a WeightContext from current aggregated state."""
        crowd_density = 0.0
        predicted_congestion = 0.0
        if zone_id and zone_id in self._crowd_states:
            cs = self._crowd_states[zone_id]
            crowd_density = cs.density
            predicted_congestion = cs.predicted_density_5m

        weather_penalty = self._compute_weather_penalty()
        risk_score = 0.0
        if zone_id:
            risk_score = self._risk_scores.get(zone_id, 0.0)

        emergency_active = any(
            i.incident_type in ("fire", "chemical_hazard", "flooding", "power_outage")
            for i in self._incidents
        )
        medical_nearby = any(
            i.incident_type == "medical" for i in self._incidents
        )
        security_restricted = any(
            i.incident_type == "security" for i in self._incidents
        )

        broken_infra = (
            any(v is False for v in self._infrastructure.escalator_status.values())
            or any(v is False for v in self._infrastructure.elevator_status.values())
            or bool(self._infrastructure.closed_corridors)
            or bool(self._infrastructure.maintenance_zones)
        )

        return WeightContext(
            crowd_density=crowd_density,
            weather_penalty=weather_penalty,
            emergency_active=emergency_active,
            maintenance_active=broken_infra,
            security_restricted=security_restricted,
            medical_incident_nearby=medical_nearby,
            risk_score=risk_score,
            predicted_congestion=predicted_congestion,
        )

    def _compute_weather_penalty(self) -> float:
        penalty = 0.0
        if self._weather.rain_intensity > 50:
            penalty += 0.3
        elif self._weather.rain_intensity > 10:
            penalty += 0.1
        if self._weather.wind_speed_kmh > 40:
            penalty += 0.2
        elif self._weather.wind_speed_kmh > 20:
            penalty += 0.1
        if self._weather.heat_index > 35:
            penalty += 0.2
        if self._weather.visibility < 0.5:
            penalty += 0.3
        return min(penalty, 1.0)

    @property
    def last_update(self) -> float:
        return self._last_update

    def snapshot(self) -> dict:
        return {
            "crowd_zones": len(self._crowd_states),
            "active_incidents": len(self._incidents),
            "risk_zones": len(self._risk_scores),
            "weather_penalty": self._compute_weather_penalty(),
            "last_update": self._last_update,
        }
