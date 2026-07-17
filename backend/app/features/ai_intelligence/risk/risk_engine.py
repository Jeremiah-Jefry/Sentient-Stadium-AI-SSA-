"""Core risk scoring engine — multi-factor weighted risk assessment."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from app.features.ai_intelligence.models.enums import RiskLevel
from app.features.ai_intelligence.risk.risk_factors import RiskFactorCalculator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------
DEFAULT_RISK_WEIGHTS: dict[str, float] = {
    "density": 0.20,
    "flow": 0.15,
    "weather": 0.10,
    "medical": 0.12,
    "security": 0.12,
    "accessibility": 0.08,
    "transport": 0.08,
    "volunteer": 0.05,
    "equipment": 0.05,
    "match_context": 0.05,
}

DEFAULT_RISK_THRESHOLDS: dict[str, float] = {
    "green": 0.0,
    "yellow": 0.25,
    "orange": 0.50,
    "red": 0.75,
    "critical": 0.90,
}

LEVEL_MAP: dict[str, RiskLevel] = {
    "green": RiskLevel.GREEN,
    "yellow": RiskLevel.YELLOW,
    "orange": RiskLevel.ORANGE,
    "red": RiskLevel.RED,
    "critical": RiskLevel.CRITICAL,
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class RiskAssessmentResult:
    """Immutable result of a risk assessment cycle."""

    risk_level: RiskLevel
    risk_score: float
    venue_risk: float
    zone_risk: float
    medical_risk: float
    security_risk: float
    accessibility_risk: float
    transport_risk: float
    weather_risk: float
    risk_factors: dict[str, float] = field(default_factory=dict)
    contributing_events: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class RiskEngine:
    """Computes multi-factor risk from event context.

    Configuration is injected via *weights* and *thresholds* so the
    engine can be tuned per-venue or per-competition without code
    changes.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        thresholds: dict[str, float] | None = None,
        calculator: RiskFactorCalculator | None = None,
    ) -> None:
        self._weights = weights or dict(DEFAULT_RISK_WEIGHTS)
        self._thresholds = thresholds or dict(DEFAULT_RISK_THRESHOLDS)
        self._calc = calculator or RiskFactorCalculator()
        self._assessments_count: int = 0
        self._last_assessment_time: float = 0.0
        logger.info(
            "RiskEngine initialised with %d factor weights", len(self._weights),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def assess_risk(self, context: dict) -> RiskAssessmentResult:
        """Compute multi-factor risk from event context."""
        factors: dict[str, float] = {}

        factors["density"] = self._calc.density(
            context.get("density", 0.0),
            context.get("capacity", 1.0),
        )
        factors["flow"] = self._calc.flow(
            context.get("flow_rate", 0.0),
            context.get("expected_flow", 1.0),
        )
        factors["weather"] = self._calc.weather(context.get("weather", {}))
        factors["medical"] = self._calc.medical(
            context.get("medical_events", []),
            context.get("medical_capacity", 1),
        )
        factors["security"] = self._calc.security(
            context.get("security_events", []),
        )
        factors["accessibility"] = self._calc.accessibility(
            context.get("blocked_paths", 0),
            context.get("total_paths", 1),
            context.get("wheelchair_users", 0),
        )
        factors["transport"] = self._calc.transport(
            context.get("transport_delays", []),
            context.get("expected_arrivals", 1),
        )
        factors["volunteer"] = self._calc.volunteer(
            context.get("volunteers_available", 0),
            context.get("volunteers_needed", 1),
        )
        factors["equipment"] = self._calc.equipment(
            context.get("offline_sensors", 0),
            context.get("total_sensors", 1),
        )
        factors["match_context"] = self._calc.match_context(
            context.get("match_phase", "pre_match"),
            context.get("score_diff", 0),
            context.get("minutes_remaining", 90),
        )

        composite_score = self._weighted_composite(factors)
        risk_level = self._score_to_level(composite_score)

        venue_risk = self._domain_aggregate(
            factors, {"density", "flow", "match_context"},
        )
        zone_risk = self._domain_aggregate(
            factors, {"density", "flow", "equipment"},
        )

        self._assessments_count += 1
        self._last_assessment_time = time.time()

        contributing = context.get("contributing_event_ids", [])

        logger.info(
            "Risk assessed: level=%s score=%.3f venue=%s zone=%s",
            risk_level.value,
            composite_score,
            context.get("venue_id", "?"),
            context.get("zone_id", "venue-level"),
        )

        return RiskAssessmentResult(
            risk_level=risk_level,
            risk_score=round(composite_score, 4),
            venue_risk=round(venue_risk, 4),
            zone_risk=round(zone_risk, 4),
            medical_risk=factors["medical"],
            security_risk=factors["security"],
            accessibility_risk=factors["accessibility"],
            transport_risk=factors["transport"],
            weather_risk=factors["weather"],
            risk_factors={k: round(v, 4) for k, v in factors.items()},
            contributing_events=contributing,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _weighted_composite(self, factors: dict[str, float]) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        for key, weight in self._weights.items():
            if key in factors:
                weighted_sum += weight * factors[key]
                total_weight += weight
        if total_weight <= 0.0:
            return 0.0
        return max(0.0, min(1.0, weighted_sum / total_weight))

    def _domain_aggregate(self, factors: dict[str, float], keys: set[str]) -> float:
        vals = [factors[k] for k in keys if k in factors]
        return max(vals) if vals else 0.0

    def _score_to_level(self, score: float) -> RiskLevel:
        """Map continuous score to discrete risk level."""
        result = RiskLevel.GREEN
        for level_name, threshold in sorted(
            self._thresholds.items(), key=lambda item: item[1],
        ):
            if score >= threshold:
                result = LEVEL_MAP.get(level_name, RiskLevel.GREEN)
        return result

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    @property
    def stats(self) -> dict:
        return {
            "assessments_count": self._assessments_count,
            "last_assessment_time": self._last_assessment_time,
            "weight_count": len(self._weights),
            "threshold_count": len(self._thresholds),
        }
