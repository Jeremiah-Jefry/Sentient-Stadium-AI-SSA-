"""Individual risk factor calculators — nonlinear scoring for each risk domain."""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunable thresholds for sigmoid-like curves
# ---------------------------------------------------------------------------
DENSITY_HALF_RISK: float = 0.7
FLOW_DEFICIT_K: float = 8.0
WEATHER_SEVERITY_K: float = 2.5
MEDICAL_OVERLOAD_K: float = 4.0
SECURITY_SEVERITY_K: float = 3.0
ACCESSIBILITY_PENALTY_K: float = 6.0
TRANSPORT_DELAY_K: float = 3.0
VOLUNTEER_DEFICIT_K: float = 5.0
EQUIPMENT_FAILURE_K: float = 4.0
MATCH_TENSION_K: float = 2.0

# Weights used to describe contribution labels
_DOMAIN_LABELS: dict[str, str] = {
    "density": "crowd density vs capacity",
    "flow": "restricted pedestrian flow",
    "weather": "adverse weather conditions",
    "medical": "medical event pressure",
    "security": "security incident load",
    "accessibility": "accessibility path blockage",
    "transport": "transport disruption",
    "volunteer": "volunteer shortfall",
    "equipment": "sensor/camera equipment failure",
    "match_context": "match-phase crowd tension",
}


def _sigmoid(x: float, k: float, midpoint: float = 0.0) -> float:
    """Generalised logistic curve mapped to (0, 1)."""
    try:
        return 1.0 / (1.0 + math.exp(-k * (x - midpoint)))
    except OverflowError:
        return 0.0 if x < midpoint else 1.0


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ------------------------------------------------------------------
# Individual factor calculators
# ------------------------------------------------------------------


def density_risk(density_value: float, capacity: float) -> float:
    """Risk 0-1 based on density vs capacity ratio with nonlinear scaling.

    Uses a sigmoid centred at DENSITY_HALF_RISK so risk accelerates
    once the venue reaches ~70 % of safe-density threshold.
    """
    if capacity <= 0.0:
        logger.warning("density_risk called with non-positive capacity %s", capacity)
        return 1.0
    ratio = density_value / capacity
    score = _sigmoid(ratio, k=FLOW_DEFICIT_K, midpoint=DENSITY_HALF_RISK)
    return _clamp(score)


def flow_risk(flow_rate: float, expected_flow: float) -> float:
    """Restricted flow increases risk.

    Risk rises when actual flow drops significantly below expected flow.
    If flow exceeds expectation the risk is minimal.
    """
    if expected_flow <= 0.0:
        logger.warning("flow_risk called with non-positive expected_flow %s", expected_flow)
        return 0.0
    deficit_ratio = 1.0 - (flow_rate / expected_flow)
    score = _sigmoid(deficit_ratio, k=FLOW_DEFICIT_K, midpoint=0.0)
    return _clamp(score)


def weather_risk(weather_data: dict) -> float:
    """Composite weather risk from rain, wind, heat, and cold indices.

    Expected keys (0-100 normalised):
      rain_intensity, wind_speed_kmh, heat_index, cold_index.
    Missing keys default to 0 risk contribution.
    """
    rain = _clamp(float(weather_data.get("rain_intensity", 0)) / 100.0)
    wind = _clamp(float(weather_data.get("wind_speed_kmh", 0)) / 100.0)
    heat = _clamp(float(weather_data.get("heat_index", 0)) / 100.0)
    cold = _clamp(float(weather_data.get("cold_index", 0)) / 100.0)
    composite = max(rain, wind, heat, cold)
    weighted = 0.4 * rain + 0.25 * wind + 0.2 * heat + 0.15 * cold
    score = _sigmoid(composite, k=WEATHER_SEVERITY_K, midpoint=0.4)
    blended = 0.6 * score + 0.4 * weighted
    return _clamp(blended)


def medical_risk(medical_events: list[dict], medical_capacity: int) -> float:
    """Medical event pressure relative to capacity.

    Severity of events is extracted from a ``severity`` field (1-5).
    """
    if medical_capacity <= 0:
        logger.warning("medical_risk called with non-positive capacity %s", medical_capacity)
        return 1.0
    severity_sum = sum(float(e.get("severity", 1)) for e in medical_events)
    severity_norm = severity_sum / (medical_capacity * 5.0)
    score = _sigmoid(severity_norm, k=MEDICAL_OVERLOAD_K, midpoint=0.5)
    return _clamp(score)


def security_risk(security_events: list[dict]) -> float:
    """Security risk based on incident count and severity.

    Severity fields are expected 1-5.
    """
    if not security_events:
        return 0.0
    count_factor = _clamp(len(security_events) / 20.0)
    severity_sum = sum(float(e.get("severity", 1)) for e in security_events)
    avg_severity = severity_sum / len(security_events) if security_events else 0.0
    severity_factor = _clamp(avg_severity / 5.0)
    composite = 0.5 * count_factor + 0.5 * severity_factor
    score = _sigmoid(composite, k=SECURITY_SEVERITY_K, midpoint=0.3)
    return _clamp(score)


def accessibility_risk(
    blocked_paths: int, total_paths: int, wheelchair_users: int,
) -> float:
    """Risk when accessible routes are blocked and vulnerable users exist."""
    if total_paths <= 0:
        return 1.0 if wheelchair_users > 0 else 0.0
    block_ratio = blocked_paths / total_paths
    user_factor = _clamp(wheelchair_users / 50.0)
    base = _sigmoid(block_ratio, k=ACCESSIBILITY_PENALTY_K, midpoint=0.2)
    amplified = base * (1.0 + 0.5 * user_factor)
    return _clamp(amplified)


def transport_risk(delays: list[dict], expected_arrivals: int) -> float:
    """Delay impact on crowd accumulation risk.

    Each delay dict should contain ``delay_minutes`` (float).
    """
    if expected_arrivals <= 0:
        return 0.0
    total_delay = sum(float(d.get("delay_minutes", 0)) for d in delays)
    avg_delay = total_delay / max(len(delays), 1)
    delay_factor = _clamp(avg_delay / 60.0)
    volume_factor = _clamp(len(delays) / max(expected_arrivals, 1))
    composite = 0.6 * delay_factor + 0.4 * volume_factor
    score = _sigmoid(composite, k=TRANSPORT_DELAY_K, midpoint=0.4)
    return _clamp(score)


def volunteer_risk(volunteers_available: int, volunteers_needed: int) -> float:
    """Risk from volunteer shortfall — critical for operations."""
    if volunteers_needed <= 0:
        return 0.0
    deficit_ratio = 1.0 - min(volunteers_available / volunteers_needed, 1.5)
    score = _sigmoid(deficit_ratio, k=VOLUNTEER_DEFICIT_K, midpoint=0.0)
    return _clamp(score)


def equipment_risk(offline_count: int, total_count: int) -> float:
    """Sensor/camera failure risk — loss of visibility degrades all other systems."""
    if total_count <= 0:
        return 1.0
    failure_ratio = offline_count / total_count
    score = _sigmoid(failure_ratio, k=EQUIPMENT_FAILURE_K, midpoint=0.3)
    return _clamp(score)


def match_context_risk(
    match_phase: str, score_diff: int, minutes_remaining: int,
) -> float:
    """Risk modulation from match state — high tension phases increase risk.

    Penalty shootouts, close scores, and final minutes carry the highest
    crowd-behaviour risk.
    """
    high_tension_phases = {"penalty_shootout", "extra_time", "second_half"}
    medium_tension_phases = {"first_half", "kickoff"}

    if match_phase in high_tension_phases:
        phase_factor = 0.7
    elif match_phase in medium_tension_phases:
        phase_factor = 0.4
    elif match_phase == "halftime":
        phase_factor = 0.3
    elif match_phase == "post_match":
        phase_factor = 0.5
    else:
        phase_factor = 0.1

    close_score = 1.0 - _clamp(abs(score_diff) / 5.0)
    time_pressure = _clamp(1.0 - minutes_remaining / 90.0) if minutes_remaining <= 90 else 0.0
    composite = 0.4 * phase_factor + 0.3 * close_score + 0.3 * time_pressure
    score = _sigmoid(composite, k=MATCH_TENSION_K, midpoint=0.4)
    return _clamp(score)


# ------------------------------------------------------------------
# Dataclass aggregating all factor functions
# ------------------------------------------------------------------
from dataclasses import dataclass  # noqa: E402


@dataclass(slots=True)
class RiskFactorCalculator:
    """Convenience container that delegates to the module-level functions.

    Allows unit-testing each factor in isolation while providing a
    single entry point for the risk engine.
    """

    density_half_risk: float = DENSITY_HALF_RISK
    flow_deficit_k: float = FLOW_DEFICIT_K

    def density(self, density_value: float, capacity: float) -> float:
        return density_risk(density_value, capacity)

    def flow(self, flow_rate: float, expected_flow: float) -> float:
        return flow_risk(flow_rate, expected_flow)

    def weather(self, weather_data: dict) -> float:
        return weather_risk(weather_data)

    def medical(self, medical_events: list[dict], medical_capacity: int) -> float:
        return medical_risk(medical_events, medical_capacity)

    def security(self, security_events: list[dict]) -> float:
        return security_risk(security_events)

    def accessibility(
        self, blocked_paths: int, total_paths: int, wheelchair_users: int,
    ) -> float:
        return accessibility_risk(blocked_paths, total_paths, wheelchair_users)

    def transport(self, delays: list[dict], expected_arrivals: int) -> float:
        return transport_risk(delays, expected_arrivals)

    def volunteer(self, volunteers_available: int, volunteers_needed: int) -> float:
        return volunteer_risk(volunteers_available, volunteers_needed)

    def equipment(self, offline_count: int, total_count: int) -> float:
        return equipment_risk(offline_count, total_count)

    def match_context(
        self, match_phase: str, score_diff: int, minutes_remaining: int,
    ) -> float:
        return match_context_risk(match_phase, score_diff, minutes_remaining)
