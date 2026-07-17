"""Model abstractions — base classes, statistical and graph prediction models."""

from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MODEL_VERSION: str = "1.0.0"

# ---------------------------------------------------------------------------
# Prediction result
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class PredictionResult:
    """Output of a single prediction model invocation."""

    prediction_type: str
    predicted_value: float
    confidence: float
    contributing_factors: list[dict] = field(default_factory=list)
    evidence_count: int = 0
    model_version: str = MODEL_VERSION


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------
class PredictionModel(ABC):
    """Abstract base for all prediction models."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the unique model identifier."""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the model version string."""

    @abstractmethod
    async def predict(
        self, features: dict, horizon_seconds: int,
    ) -> PredictionResult:
        """Run prediction given input features and time horizon."""


# ---------------------------------------------------------------------------
# Statistical model — exponential moving average + linear trend
# ---------------------------------------------------------------------------
ALPHA_DEFAULT: float = 0.3
TREND_WINDOW: int = 10
MIN_HISTORY: int = 3


class StatisticalModel(PredictionModel):
    """Time-series extrapolation using EMA and linear trend.

    Requires features["history"] to be a list of floats.
    """

    def __init__(self, alpha: float = ALPHA_DEFAULT) -> None:
        self._alpha = alpha

    @property
    def model_name(self) -> str:
        return "statistical_ema_trend"

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    async def predict(
        self, features: dict, horizon_seconds: int,
    ) -> PredictionResult:
        history: list[float] = features.get("history", [])
        pred_type = features.get("prediction_type", "unknown")
        if len(history) < MIN_HISTORY:
            return PredictionResult(
                prediction_type=pred_type,
                predicted_value=history[-1] if history else 0.0,
                confidence=0.1,
                contributing_factors=[{"reason": "insufficient_history"}],
                evidence_count=len(history),
                model_version=self.model_version,
            )

        ema = self._compute_ema(history)
        trend = self._compute_trend(history)
        horizon_factor = min(horizon_seconds / 600.0, 2.0)
        predicted = max(0.0, min(1.0, ema + trend * horizon_factor))
        confidence = self._estimate_confidence(history)
        factors = [
            {"name": "ema", "value": round(ema, 4)},
            {"name": "trend", "value": round(trend, 6)},
            {"name": "horizon_seconds", "value": horizon_seconds},
        ]
        return PredictionResult(
            prediction_type=pred_type,
            predicted_value=round(predicted, 4),
            confidence=round(confidence, 4),
            contributing_factors=factors,
            evidence_count=len(history),
            model_version=self.model_version,
        )

    def _compute_ema(self, data: list[float]) -> float:
        ema = data[0]
        for value in data[1:]:
            ema = self._alpha * value + (1.0 - self._alpha) * ema
        return ema

    def _compute_trend(self, data: list[float]) -> float:
        window = data[-TREND_WINDOW:]
        n = len(window)
        if n < 2:
            return 0.0
        mean_x = (n - 1) / 2.0
        mean_y = sum(window) / n
        num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(window))
        den = sum((i - mean_x) ** 2 for i in range(n))
        return num / den if den > 0.0 else 0.0

    def _estimate_confidence(self, history: list[float]) -> float:
        window = history[-TREND_WINDOW:]
        if len(window) < 2:
            return 0.2
        mean = sum(window) / len(window)
        if mean == 0.0:
            return 0.3
        variance = sum((v - mean) ** 2 for v in window) / len(window)
        cv = math.sqrt(variance) / abs(mean)
        return max(0.1, min(1.0, 1.0 - cv))


# ---------------------------------------------------------------------------
# Graph model — BFS propagation through zone topology
# ---------------------------------------------------------------------------
DECAY_PER_STEP: float = 0.7
MAX_STEPS: int = 10


class GraphModel(PredictionModel):
    """Graph-based propagation prediction for crowd flow.

    Requires:
      features["zone_graph"]: dict[str, dict] with "neighbors" list
      features["current_flows"]: dict[str, float]
      features["source_zone"]: str (optional)
    """

    @property
    def model_name(self) -> str:
        return "graph_propagation"

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    async def predict(
        self, features: dict, horizon_seconds: int,
    ) -> PredictionResult:
        zone_graph: dict = features.get("zone_graph", {})
        flows: dict[str, float] = features.get("current_flows", {})
        source = features.get("source_zone", "")
        pred_type = features.get("prediction_type", "unknown")

        if not zone_graph or not flows:
            return PredictionResult(
                prediction_type=pred_type,
                predicted_value=0.0,
                confidence=0.1,
                contributing_factors=[{"reason": "missing_graph_data"}],
                evidence_count=0,
                model_version=self.model_version,
            )

        if not source:
            source = max(flows, key=flows.get) if flows else ""

        steps = min(horizon_seconds // 60, MAX_STEPS)
        spread = self._bfs_spread(source, zone_graph, flows, steps)
        max_impact = max((s["impact"] for s in spread), default=0.0)
        affected_count = len(spread)

        confidence = 0.5
        if len(zone_graph) > 0:
            confidence += 0.2 * min(affected_count / len(zone_graph), 1.0)
        confidence += 0.1 * (1.0 if source in zone_graph else 0.0)
        confidence = max(0.1, min(1.0, confidence))

        factors = [
            {"name": "source_zone", "value": source},
            {"name": "steps", "value": steps},
            {"name": "affected_zones", "value": affected_count},
        ]
        return PredictionResult(
            prediction_type=pred_type,
            predicted_value=round(max_impact, 4),
            confidence=round(confidence, 4),
            contributing_factors=factors,
            evidence_count=affected_count,
            model_version=self.model_version,
        )

    def _bfs_spread(
        self, source: str, graph: dict, flows: dict[str, float], max_steps: int,
    ) -> list[dict]:
        visited: dict[str, float] = {source: flows.get(source, 0.0)}
        queue: list[tuple[str, int, float]] = [(source, 0, flows.get(source, 0.0))]
        results: list[dict] = []
        while queue:
            zone, depth, intensity = queue.pop(0)
            if depth > max_steps:
                continue
            for neighbor in graph.get(zone, {}).get("neighbors", []):
                if neighbor in visited:
                    continue
                propagated = intensity * DECAY_PER_STEP
                visited[neighbor] = propagated
                results.append({
                    "zone": neighbor,
                    "depth": depth + 1,
                    "impact": round(propagated, 4),
                })
                if propagated > 0.05:
                    queue.append((neighbor, depth + 1, propagated))
        return results
