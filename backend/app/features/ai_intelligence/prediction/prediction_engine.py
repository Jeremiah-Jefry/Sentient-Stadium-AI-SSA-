"""Multi-window prediction engine — orchestrates model selection and execution."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from app.features.ai_intelligence.prediction.prediction_backends import (
    RuleEngineModel,
    SimulationModel,
)
from app.features.ai_intelligence.prediction.prediction_models import (
    GraphModel,
    PredictionModel,
    PredictionResult,
    StatisticalModel,
)

logger = logging.getLogger(__name__)

PREDICTION_WINDOWS: list[int] = [30, 60, 180, 300, 600, 900]

# Which model families are preferred for each prediction category
_MODEL_PREFERENCE: dict[str, list[str]] = {
    "threshold": ["rule_engine"],
    "propagation": ["graph_propagation"],
    "trend": ["statistical_ema_trend"],
    "congestion": ["graph_propagation", "statistical_ema_trend"],
    "bottleneck": ["graph_propagation", "monte_carlo_simulation"],
    "simulation": ["monte_carlo_simulation"],
}

# Prediction types mapped to their preferred category
_TYPE_CATEGORY: dict[str, str] = {
    "bottleneck": "bottleneck",
    "congestion": "congestion",
    "queue_growth": "trend",
    "dangerous_density": "threshold",
    "medical_overload": "threshold",
    "volunteer_shortage": "threshold",
    "exit_saturation": "propagation",
    "transport_congestion": "trend",
    "wheelchair_blockage": "threshold",
    "lost_child": "simulation",
    "cleaning_overload": "trend",
    "security_pressure": "threshold",
}


@dataclass(slots=True)
class PredictionBatch:
    """Aggregated prediction output for a single type across all windows."""

    prediction_type: str
    results: list[PredictionResult] = field(default_factory=list)


class PredictionEngine:
    """Multi-window prediction engine.

    Selects the most appropriate model for each (type, window) pair
    and returns results ranked by confidence.
    """

    def __init__(
        self, models: list[PredictionModel] | None = None,
    ) -> None:
        self._models = models or [
            StatisticalModel(),
            GraphModel(),
            RuleEngineModel(),
            SimulationModel(),
        ]
        self._model_registry: dict[str, PredictionModel] = {
            m.model_name: m for m in self._models
        }
        self._prediction_count: int = 0
        self._last_prediction_time: float = 0.0
        logger.info(
            "PredictionEngine initialised with %d models: %s",
            len(self._models),
            [m.model_name for m in self._models],
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def predict_all(
        self,
        features: dict,
        prediction_types: list[str],
        windows: list[int] | None = None,
    ) -> list[PredictionResult]:
        """Run predictions for all types across all windows."""
        windows = windows or PREDICTION_WINDOWS
        results: list[PredictionResult] = []

        for pred_type in prediction_types:
            enhanced = {**features, "prediction_type": pred_type}
            for window in windows:
                model = self.select_model(pred_type, enhanced)
                try:
                    result = await model.predict(enhanced, window)
                    results.append(result)
                except Exception:
                    logger.exception(
                        "Prediction failed for type=%s window=%d model=%s",
                        pred_type, window, model.model_name,
                    )

        self._prediction_count += len(results)
        self._last_prediction_time = time.time()

        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def select_model(
        self, prediction_type: str, available_data: dict,
    ) -> PredictionModel:
        """Select best model based on prediction type and available data."""
        category = _TYPE_CATEGORY.get(prediction_type, "trend")
        preferences = _MODEL_PREFERENCE.get(category, ["statistical_ema_trend"])

        for model_name in preferences:
            model = self._model_registry.get(model_name)
            if model and self._model_has_required_data(model_name, available_data):
                return model

        fallback = self._model_registry.get("statistical_ema_trend")
        if fallback:
            return fallback

        return self._models[0] if self._models else _NullModel()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    @property
    def stats(self) -> dict:
        return {
            "prediction_count": self._prediction_count,
            "last_prediction_time": self._last_prediction_time,
            "model_count": len(self._models),
            "model_names": [m.model_name for m in self._models],
            "supported_windows": PREDICTION_WINDOWS,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    @staticmethod
    def _model_has_required_data(model_name: str, data: dict) -> bool:
        required_keys: dict[str, list[str]] = {
            "statistical_ema_trend": ["history"],
            "graph_propagation": ["zone_graph", "current_flows"],
            "rule_engine": ["rules", "state"],
            "monte_carlo_simulation": [
                "agent_count", "zone_capacity", "exit_count",
            ],
        }
        keys = required_keys.get(model_name, [])
        return all(k in data for k in keys)


class _NullModel(PredictionModel):
    """Fallback model when no suitable model is available."""

    @property
    def model_name(self) -> str:
        return "null_model"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    async def predict(
        self, features: dict, horizon_seconds: int,
    ) -> PredictionResult:
        return PredictionResult(
            prediction_type=features.get("prediction_type", "unknown"),
            predicted_value=0.0,
            confidence=0.0,
            contributing_factors=[{"reason": "no_model_available"}],
            evidence_count=0,
            model_version=self.model_version,
        )
