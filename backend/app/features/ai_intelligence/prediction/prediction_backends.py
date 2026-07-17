"""Prediction backends — rule engine and Monte Carlo simulation models."""

from __future__ import annotations

import logging
import random

from app.features.ai_intelligence.prediction.prediction_models import (
    MODEL_VERSION,
    PredictionModel,
    PredictionResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule engine model — configurable threshold rules
# ---------------------------------------------------------------------------
class RuleEngineModel(PredictionModel):
    """Rule-based prediction using configurable threshold rules.

    Requires features["rules"] as a list of rule dicts:
      {"threshold": float, "field": str, "operator": str,
       "prediction_value": float, "confidence": float}
    Operators: "gt", "lt", "gte", "lte", "eq".
    """

    @property
    def model_name(self) -> str:
        return "rule_engine"

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    async def predict(
        self, features: dict, horizon_seconds: int,
    ) -> PredictionResult:
        rules: list[dict] = features.get("rules", [])
        state: dict = features.get("state", {})
        prediction_type = features.get("prediction_type", "unknown")

        if not rules:
            return PredictionResult(
                prediction_type=prediction_type,
                predicted_value=0.0,
                confidence=0.1,
                contributing_factors=[{"reason": "no_rules_configured"}],
                evidence_count=0,
                model_version=self.model_version,
            )

        matched = self._evaluate_rules(rules, state)
        if not matched:
            return PredictionResult(
                prediction_type=prediction_type,
                predicted_value=0.0,
                confidence=0.2,
                contributing_factors=[{"reason": "no_rules_triggered"}],
                evidence_count=0,
                model_version=self.model_version,
            )

        best = max(matched, key=lambda r: r.get("confidence", 0))
        factors = [
            {"rule": r.get("field", "?"), "value": r.get("prediction_value", 0.0)}
            for r in matched
        ]
        return PredictionResult(
            prediction_type=prediction_type,
            predicted_value=best.get("prediction_value", 0.0),
            confidence=best.get("confidence", 0.5),
            contributing_factors=factors,
            evidence_count=len(matched),
            model_version=self.model_version,
        )

    def _evaluate_rules(self, rules: list[dict], state: dict) -> list[dict]:
        triggered: list[dict] = []
        for rule in rules:
            field_name = rule.get("field", "")
            threshold = rule.get("threshold", 0.0)
            operator = rule.get("operator", "gt")
            value = state.get(field_name)
            if value is None:
                continue
            try:
                val = float(value)
            except (TypeError, ValueError):
                continue
            if self._check_operator(val, operator, threshold):
                triggered.append(rule)
        return triggered

    @staticmethod
    def _check_operator(value: float, op: str, threshold: float) -> bool:
        ops = {
            "gt": value > threshold,
            "lt": value < threshold,
            "gte": value >= threshold,
            "lte": value <= threshold,
            "eq": abs(value - threshold) < 1e-9,
        }
        return ops.get(op, False)


# ---------------------------------------------------------------------------
# Simulation model — simplified Monte Carlo
# ---------------------------------------------------------------------------
MONTE_CARLO_RUNS: int = 200
AGENT_STEPS_PER_SECOND: int = 2


class SimulationModel(PredictionModel):
    """Agent-based simulation for what-if scenarios.

    Requires:
      features["agent_count"]: int
      features["zone_capacity"]: int
      features["exit_count"]: int
      features["bottleneck_probability"]: float (0-1, optional)
    """

    @property
    def model_name(self) -> str:
        return "monte_carlo_simulation"

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    async def predict(
        self, features: dict, horizon_seconds: int,
    ) -> PredictionResult:
        agent_count = features.get("agent_count", 0)
        zone_capacity = features.get("zone_capacity", 1)
        exit_count = features.get("exit_count", 1)
        bottleneck_prob = features.get("bottleneck_probability", 0.3)
        prediction_type = features.get("prediction_type", "unknown")

        if agent_count <= 0 or zone_capacity <= 0:
            return PredictionResult(
                prediction_type=prediction_type,
                predicted_value=0.0,
                confidence=0.1,
                contributing_factors=[{"reason": "invalid_simulation_params"}],
                evidence_count=0,
                model_version=self.model_version,
            )

        saturation_hits = 0
        total_bottlenecks = 0
        steps = horizon_seconds * AGENT_STEPS_PER_SECOND

        for _ in range(MONTE_CARLO_RUNS):
            capacity = zone_capacity
            agents = agent_count
            for _ in range(steps):
                agents -= max(0, exit_count * (1 + random.random() * 0.5))
                agents = max(0, agents)
                if random.random() < bottleneck_prob:
                    total_bottlenecks += 1
                if agents >= capacity:
                    saturation_hits += 1
                    break

        saturation_rate = saturation_hits / MONTE_CARLO_RUNS
        bottleneck_rate = total_bottlenecks / (MONTE_CARLO_RUNS * max(steps, 1))

        confidence = 0.3 + 0.4 * min(agent_count / max(zone_capacity, 1), 1.0)
        confidence += 0.1 * min(MONTE_CARLO_RUNS / 200.0, 1.0)
        confidence = max(0.1, min(1.0, confidence))

        factors = [
            {"name": "saturation_rate", "value": round(saturation_rate, 4)},
            {"name": "bottleneck_rate", "value": round(bottleneck_rate, 6)},
            {"name": "simulations_run", "value": MONTE_CARLO_RUNS},
        ]
        return PredictionResult(
            prediction_type=prediction_type,
            predicted_value=round(saturation_rate, 4),
            confidence=round(confidence, 4),
            contributing_factors=factors,
            evidence_count=MONTE_CARLO_RUNS,
            model_version=self.model_version,
        )
