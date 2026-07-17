"""Stage 3 — Short-Term Prediction: runs multi-window predictions across relevant types."""

from __future__ import annotations

import logging

from app.features.ai_intelligence.engine.context import (
    IntelligenceContext,
    PredictionBundle,
)
from app.features.ai_intelligence.models.enums import PredictionType
from app.features.ai_intelligence.prediction.prediction_engine import PredictionEngine

logger = logging.getLogger(__name__)

PREDICTION_WINDOWS: list[int] = [30, 60, 180, 300, 600, 900]
CONFIDENCE_AGGREGATION_WEIGHT: float = 0.7
MODEL_DIVERSITY_BONUS: float = 0.1

_RISK_PATTERN_TO_TYPES: dict[str, list[str]] = {
    "normal": [
        PredictionType.CONGESTION.value,
        PredictionType.QUEUE_GROWTH.value,
    ],
    "surge": [
        PredictionType.DANGEROUS_DENSITY.value,
        PredictionType.BOTTLENECK.value,
        PredictionType.CONGESTION.value,
        PredictionType.EXIT_SATURATION.value,
    ],
    "stagnation": [
        PredictionType.BOTTLENECK.value,
        PredictionType.CONGESTION.value,
        PredictionType.VOLUNTEER_SHORTAGE.value,
    ],
    "reverse": [
        PredictionType.DANGEROUS_DENSITY.value,
        PredictionType.SECURITY_PRESSURE.value,
        PredictionType.MEDICAL_OVERLOAD.value,
    ],
    "panic": [
        PredictionType.DANGEROUS_DENSITY.value,
        PredictionType.MEDICAL_OVERLOAD.value,
        PredictionType.SECURITY_PRESSURE.value,
        PredictionType.EXIT_SATURATION.value,
    ],
}

_ALWAYS_PREDICT: list[str] = [
    PredictionType.CONGESTION.value,
    PredictionType.DANGEROUS_DENSITY.value,
]


class Stage3Prediction:
    """Runs PredictionEngine for multiple time windows and prediction types."""

    def __init__(self, prediction_engine: PredictionEngine) -> None:
        self._engine = prediction_engine

    async def execute(self, ctx: IntelligenceContext) -> None:
        sit = ctx.situation
        behav = ctx.behaviour
        if sit is None:
            ctx.predictions = PredictionBundle(
                predictions=[], overall_confidence=0.0,
                time_horizons=PREDICTION_WINDOWS, model_versions={},
            )
            return

        features = self._build_features(sit, behav)
        prediction_types = self._select_types(behav)

        results = await self._engine.predict_all(
            features=features,
            prediction_types=prediction_types,
            windows=PREDICTION_WINDOWS,
        )

        predictions = [self._serialise_result(r) for r in results]
        overall_conf = self._aggregate_confidence(results)
        model_versions = self._collect_model_versions(results)

        ctx.predictions = PredictionBundle(
            predictions=predictions,
            overall_confidence=round(overall_conf, 4),
            time_horizons=PREDICTION_WINDOWS,
            model_versions=model_versions,
        )
        logger.debug(
            "Stage 3 complete: %d predictions, confidence=%.3f",
            len(predictions), overall_conf,
        )

    @staticmethod
    def _build_features(sit, behav) -> dict:
        features: dict = {
            "density": sit.current_density,
            "flow_rate": sit.flow_rate,
            "occupancy_percent": sit.occupancy_percent,
            "active_sensors": sit.active_sensors,
            "match_phase": sit.match_phase,
            "behavior_modifiers": sit.behavior_modifiers,
            "movement_pattern": behav.movement_pattern if behav else "unknown",
            "flow_health": behav.flow_health if behav else 0.0,
            "bottleneck_risk": behav.bottleneck_risk if behav else 0.0,
            "history": [],
        }
        for event in sit.recent_events:
            val = event.get("density", event.get("value"))
            if isinstance(val, (int, float)):
                features["history"].append(float(val))
        return features

    @staticmethod
    def _select_types(behav) -> list[str]:
        pattern = behav.movement_pattern if behav else "normal"
        pattern_types = _RISK_PATTERN_TO_TYPES.get(pattern, _RISK_PATTERN_TO_TYPES["normal"])
        combined = list(dict.fromkeys(_ALWAYS_PREDICT + pattern_types))
        return combined

    @staticmethod
    def _serialise_result(result) -> dict:
        return {
            "prediction_type": result.prediction_type,
            "predicted_value": result.predicted_value,
            "confidence": result.confidence,
            "contributing_factors": result.contributing_factors,
            "evidence_count": result.evidence_count,
            "model_version": result.model_version,
        }

    @staticmethod
    def _aggregate_confidence(results) -> float:
        if not results:
            return 0.0
        confidences = [r.confidence for r in results]
        mean_conf = sum(confidences) / len(confidences)
        models_used = {r.model_version for r in results}
        diversity_bonus = min(len(models_used) * MODEL_DIVERSITY_BONUS, 0.3)
        high_conf_ratio = sum(1 for c in confidences if c > 0.6) / max(len(confidences), 1)
        aggregate = (
            CONFIDENCE_AGGREGATION_WEIGHT * mean_conf
            + (1.0 - CONFIDENCE_AGGREGATION_WEIGHT) * high_conf_ratio
            + diversity_bonus
        )
        return max(0.0, min(1.0, aggregate))

    @staticmethod
    def _collect_model_versions(results) -> dict[str, str]:
        versions: dict[str, str] = {}
        for r in results:
            versions[r.prediction_type] = r.model_version
        return versions
