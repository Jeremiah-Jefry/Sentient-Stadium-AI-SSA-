"""Confidence scoring engine — weighted geometric mean across evidence dimensions."""

from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
SENSOR_AGREEMENT_WEIGHT: float = 0.25
HISTORICAL_SIMILARITY_WEIGHT: float = 0.20
MODEL_AGREEMENT_WEIGHT: float = 0.25
DATA_FRESHNESS_WEIGHT: float = 0.15
EVIDENCE_COUNT_WEIGHT: float = 0.15

MIN_EVIDENCE_FOR_HIGH_CONFIDENCE: int = 5
FRESHNESS_HALF_LIFE_SECONDS: float = 60.0


@dataclass(slots=True)
class ConfidenceBreakdown:
    """Detailed breakdown of confidence computation."""

    overall: float
    sensor_agreement: float
    historical_similarity: float
    model_agreement: float
    data_freshness: float
    evidence_count: int
    reasoning: dict[str, str] = field(default_factory=dict)


class ConfidenceEngine:
    """Computes overall confidence from component scores.

    Uses a weighted geometric mean so a low score in any dimension
    significantly reduces overall confidence — never hiding uncertainty.
    """

    def compute_confidence(
        self,
        sensor_agreement: float,
        historical_similarity: float,
        model_agreement: float,
        data_freshness: float,
        evidence_count: int,
    ) -> ConfidenceBreakdown:
        """Compute overall confidence from component scores."""
        components = {
            "sensor_agreement": max(sensor_agreement, 1e-9),
            "historical_similarity": max(historical_similarity, 1e-9),
            "model_agreement": max(model_agreement, 1e-9),
            "data_freshness": max(data_freshness, 1e-9),
            "evidence_count": max(
                self._evidence_score(evidence_count), 1e-9,
            ),
        }

        weights = {
            "sensor_agreement": SENSOR_AGREEMENT_WEIGHT,
            "historical_similarity": HISTORICAL_SIMILARITY_WEIGHT,
            "model_agreement": MODEL_AGREEMENT_WEIGHT,
            "data_freshness": DATA_FRESHNESS_WEIGHT,
            "evidence_count": EVIDENCE_COUNT_WEIGHT,
        }

        total_weight = sum(weights.values())
        log_sum = sum(
            weights[key] * math.log(components[key]) for key in components
        )
        overall = math.exp(log_sum / total_weight) if total_weight > 0 else 0.0
        overall = max(0.0, min(1.0, overall))

        reasoning = self._build_reasoning(
            sensor_agreement, historical_similarity,
            model_agreement, data_freshness, evidence_count,
        )

        breakdown = ConfidenceBreakdown(
            overall=round(overall, 4),
            sensor_agreement=round(sensor_agreement, 4),
            historical_similarity=round(historical_similarity, 4),
            model_agreement=round(model_agreement, 4),
            data_freshness=round(data_freshness, 4),
            evidence_count=evidence_count,
            reasoning=reasoning,
        )

        logger.debug(
            "Confidence computed: overall=%.3f evidence=%d",
            overall, evidence_count,
        )
        return breakdown

    def compute_sensor_agreement(self, readings: list[dict]) -> float:
        """Compute agreement between sensor readings using coefficient of variation.

        Each reading dict should contain a numeric ``value`` field.
        Lower CV means higher agreement.
        """
        values = [float(r.get("value", 0)) for r in readings]
        if len(values) < 2:
            return 0.5

        mean_val = statistics.mean(values)
        if mean_val == 0.0:
            return 1.0 if all(v == 0 for v in values) else 0.0

        stdev = statistics.pstdev(values)
        cv = stdev / abs(mean_val)
        agreement = max(0.0, min(1.0, 1.0 - cv))
        return agreement

    def compute_historical_similarity(
        self, current: dict, historical_patterns: list[dict],
    ) -> float:
        """Compare current state to known historical patterns.

        Uses normalised dot-product similarity on shared numeric keys.
        """
        if not historical_patterns:
            return 0.3

        current_numeric = self._extract_numeric(current)
        if not current_numeric:
            return 0.2

        similarities: list[float] = []
        for pattern in historical_patterns:
            pattern_numeric = self._extract_numeric(pattern)
            sim = self._cosine_similarity(current_numeric, pattern_numeric)
            similarities.append(sim)

        return max(similarities) if similarities else 0.0

    def compute_data_freshness(
        self, data_timestamps: list[float], current_time: float,
    ) -> float:
        """Score data freshness based on age of most recent data points.

        Uses exponential decay — data older than 2× the half-life
        contributes almost nothing.
        """
        if not data_timestamps:
            return 0.0

        ages = [current_time - ts for ts in data_timestamps if ts <= current_time]
        if not ages:
            return 0.0

        avg_age = sum(ages) / len(ages)
        freshness = math.exp(-0.693 * avg_age / FRESHNESS_HALF_LIFE_SECONDS)
        return max(0.0, min(1.0, freshness))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _evidence_score(self, count: int) -> float:
        """Map evidence count to 0-1 score with diminishing returns."""
        if count <= 0:
            return 0.0
        return 1.0 - math.exp(-count / MIN_EVIDENCE_FOR_HIGH_CONFIDENCE)

    def _build_reasoning(
        self,
        sensor: float,
        historical: float,
        model: float,
        freshness: float,
        evidence: int,
    ) -> dict[str, str]:
        reasoning: dict[str, str] = {}
        if sensor < 0.3:
            reasoning["sensor_agreement"] = "Low sensor agreement — readings diverge significantly"
        elif sensor > 0.8:
            reasoning["sensor_agreement"] = "Strong sensor agreement across all readings"

        if historical < 0.3:
            reasoning["historical_similarity"] = (
                "Current pattern does not match known historical cases"
            )
        elif historical > 0.8:
            reasoning["historical_similarity"] = (
                "Current pattern closely matches a known historical case"
            )

        if model < 0.3:
            reasoning["model_agreement"] = "Models disagree — prediction is uncertain"
        elif model > 0.8:
            reasoning["model_agreement"] = "Strong consensus across prediction models"

        if freshness < 0.3:
            reasoning["data_freshness"] = "Data is stale — reduced confidence"
        elif freshness > 0.8:
            reasoning["data_freshness"] = "Data is fresh and up-to-date"

        if evidence < MIN_EVIDENCE_FOR_HIGH_CONFIDENCE:
            reasoning["evidence_count"] = f"Limited evidence ({evidence} data points)"
        elif evidence >= MIN_EVIDENCE_FOR_HIGH_CONFIDENCE:
            reasoning["evidence_count"] = f"Adequate evidence ({evidence} data points)"

        return reasoning

    @staticmethod
    def _extract_numeric(d: dict) -> dict[str, float]:
        numeric: dict[str, float] = {}
        for key, value in d.items():
            try:
                numeric[key] = float(value)
            except (TypeError, ValueError):
                continue
        return numeric

    @staticmethod
    def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
        common_keys = set(a.keys()) & set(b.keys())
        if not common_keys:
            return 0.0
        dot = sum(a[k] * b[k] for k in common_keys)
        norm_a = math.sqrt(sum(a[k] ** 2 for k in common_keys))
        norm_b = math.sqrt(sum(b[k] ** 2 for k in common_keys))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))
