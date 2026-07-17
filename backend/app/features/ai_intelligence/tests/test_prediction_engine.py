"""Tests for prediction models and the prediction engine."""
from __future__ import annotations

import pytest

from app.features.ai_intelligence.prediction.prediction_backends import (
    RuleEngineModel,
)
from app.features.ai_intelligence.prediction.prediction_engine import (
    PREDICTION_WINDOWS,
    PredictionEngine,
)
from app.features.ai_intelligence.prediction.prediction_models import (
    GraphModel,
    PredictionResult,
    StatisticalModel,
)


class TestStatisticalModel:
    """Tests for the StatisticalModel (EMA + linear trend)."""

    @pytest.mark.asyncio
    async def test_predict_with_history(self) -> None:
        """Should predict trend direction from historical data."""
        model = StatisticalModel()
        increasing = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        result = await model.predict(
            {"history": increasing, "prediction_type": "queue_growth"},
            horizon_seconds=300,
        )
        assert result.predicted_value > 0.5, (
            f"Increasing history should yield high prediction, got {result.predicted_value}"
        )
        assert result.confidence > 0.0

    @pytest.mark.asyncio
    async def test_predict_no_history(self) -> None:
        """Should handle missing history gracefully."""
        model = StatisticalModel()
        result = await model.predict(
            {"prediction_type": "queue_growth"},
            horizon_seconds=300,
        )
        assert result.predicted_value == 0.0
        assert result.confidence == 0.1
        assert result.evidence_count == 0

    @pytest.mark.asyncio
    async def test_predict_insufficient_history(self) -> None:
        """Fewer than MIN_HISTORY points should return low confidence."""
        model = StatisticalModel()
        result = await model.predict(
            {"history": [0.5], "prediction_type": "queue_growth"},
            horizon_seconds=300,
        )
        assert result.confidence == 0.1
        assert result.predicted_value == 0.5

    @pytest.mark.asyncio
    async def test_confidence_increases_with_data(self) -> None:
        """More data points should yield evidence_count proportional to data length."""
        model = StatisticalModel()
        short = [0.5 + i * 0.01 for i in range(5)]
        long = [0.5 + i * 0.01 for i in range(50)]
        result_short = await model.predict(
            {"history": short, "prediction_type": "queue_growth"},
            horizon_seconds=300,
        )
        result_long = await model.predict(
            {"history": long, "prediction_type": "queue_growth"},
            horizon_seconds=300,
        )
        assert result_long.evidence_count > result_short.evidence_count
        assert result_long.evidence_count == 50
        assert result_short.evidence_count == 5

    @pytest.mark.asyncio
    async def test_prediction_result_structure(self) -> None:
        """Result should have all required fields."""
        model = StatisticalModel()
        result = await model.predict(
            {"history": [0.1, 0.2, 0.3], "prediction_type": "queue_growth"},
            horizon_seconds=300,
        )
        assert isinstance(result, PredictionResult)
        assert hasattr(result, "prediction_type")
        assert hasattr(result, "predicted_value")
        assert hasattr(result, "confidence")
        assert hasattr(result, "contributing_factors")
        assert hasattr(result, "evidence_count")
        assert hasattr(result, "model_version")
        assert 0.0 <= result.predicted_value <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_prediction_bounded(self) -> None:
        """Predicted value should be clamped to [0, 1]."""
        model = StatisticalModel()
        result = await model.predict(
            {"history": [0.9, 0.95, 0.99, 1.0, 1.0, 1.0], "prediction_type": "queue_growth"},
            horizon_seconds=900,
        )
        assert 0.0 <= result.predicted_value <= 1.0

    @pytest.mark.asyncio
    async def test_declining_history(self) -> None:
        """Declining history should produce a low prediction."""
        model = StatisticalModel()
        declining = [0.9 - i * 0.1 for i in range(10)]
        result = await model.predict(
            {"history": declining, "prediction_type": "queue_growth"},
            horizon_seconds=300,
        )
        assert result.predicted_value < 0.5


class TestRuleEngineModel:
    """Tests for the RuleEngineModel (threshold rules)."""

    @pytest.mark.asyncio
    async def test_threshold_triggers(self) -> None:
        """Rules should trigger when thresholds are exceeded."""
        model = RuleEngineModel()
        features = {
            "prediction_type": "dangerous_density",
            "rules": [
                {"field": "density_ratio", "threshold": 0.8, "operator": "gt",
                 "prediction_value": 0.9, "confidence": 0.85},
            ],
            "state": {"density_ratio": 0.95},
        }
        result = await model.predict(features, horizon_seconds=300)
        assert result.predicted_value == 0.9
        assert result.confidence == 0.85
        assert result.evidence_count == 1

    @pytest.mark.asyncio
    async def test_no_rules_triggered(self) -> None:
        """Should return low prediction when no rules trigger."""
        model = RuleEngineModel()
        features = {
            "prediction_type": "dangerous_density",
            "rules": [
                {"field": "density_ratio", "threshold": 0.9, "operator": "gt",
                 "prediction_value": 0.9, "confidence": 0.85},
            ],
            "state": {"density_ratio": 0.5},
        }
        result = await model.predict(features, horizon_seconds=300)
        assert result.predicted_value == 0.0
        assert result.confidence == 0.2

    @pytest.mark.asyncio
    async def test_multiple_rules_compound(self) -> None:
        """Multiple triggered rules should compound prediction."""
        model = RuleEngineModel()
        features = {
            "prediction_type": "dangerous_density",
            "rules": [
                {"field": "density_ratio", "threshold": 0.7, "operator": "gt",
                 "prediction_value": 0.6, "confidence": 0.70},
                {"field": "flow_rate", "threshold": 50.0, "operator": "lt",
                 "prediction_value": 0.8, "confidence": 0.90},
            ],
            "state": {"density_ratio": 0.9, "flow_rate": 20.0},
        }
        result = await model.predict(features, horizon_seconds=300)
        assert result.evidence_count == 2
        assert result.confidence == 0.90
        assert result.predicted_value == 0.8

    @pytest.mark.asyncio
    async def test_no_rules_configured(self) -> None:
        """Empty rules list should return minimal prediction."""
        model = RuleEngineModel()
        result = await model.predict(
            {"prediction_type": "dangerous_density", "rules": [], "state": {}},
            horizon_seconds=300,
        )
        assert result.predicted_value == 0.0
        assert result.confidence == 0.1

    @pytest.mark.asyncio
    async def test_operators(self) -> None:
        """All operators should evaluate correctly."""
        model = RuleEngineModel()
        ops = {
            "gt": (6.0, 5.0, True),
            "lt": (4.0, 5.0, True),
            "gte": (5.0, 5.0, True),
            "lte": (5.0, 5.0, True),
            "eq": (5.0, 5.0, True),
        }
        for op, (val, thresh, expected) in ops.items():
            rules = [{"field": "x", "threshold": thresh, "operator": op,
                       "prediction_value": 0.5, "confidence": 0.5}]
            result = await model.predict(
                {"prediction_type": "test", "rules": rules, "state": {"x": val}},
                horizon_seconds=300,
            )
            triggered = result.evidence_count > 0
            assert triggered == expected, f"Operator {op}: expected {expected}, got {triggered}"

    @pytest.mark.asyncio
    async def test_missing_field_in_state(self) -> None:
        """Rule with missing state field should not trigger."""
        model = RuleEngineModel()
        features = {
            "prediction_type": "test",
            "rules": [{"field": "nonexistent", "threshold": 0.5, "operator": "gt",
                        "prediction_value": 0.5, "confidence": 0.5}],
            "state": {},
        }
        result = await model.predict(features, horizon_seconds=300)
        assert result.evidence_count == 0


class TestGraphModel:
    """Tests for the GraphModel (BFS propagation)."""

    @pytest.mark.asyncio
    async def test_propagation_from_source(self) -> None:
        """Should propagate risk from source zone to neighbors."""
        model = GraphModel()
        features = {
            "prediction_type": "bottleneck",
            "zone_graph": {
                "A": {"neighbors": ["B", "C"]},
                "B": {"neighbors": ["D"]},
                "C": {"neighbors": []},
                "D": {"neighbors": []},
            },
            "current_flows": {"A": 1.0, "B": 0.5, "C": 0.3, "D": 0.1},
            "source_zone": "A",
        }
        result = await model.predict(features, horizon_seconds=300)
        assert result.predicted_value > 0.0
        assert result.evidence_count > 0

    @pytest.mark.asyncio
    async def test_missing_graph_data(self) -> None:
        """Missing graph should return minimal prediction."""
        model = GraphModel()
        result = await model.predict(
            {"prediction_type": "bottleneck"},
            horizon_seconds=300,
        )
        assert result.predicted_value == 0.0
        assert result.confidence == 0.1

    @pytest.mark.asyncio
    async def test_auto_select_source(self) -> None:
        """Without source_zone, should pick highest-flow zone."""
        model = GraphModel()
        features = {
            "prediction_type": "bottleneck",
            "zone_graph": {
                "A": {"neighbors": ["B"]},
                "B": {"neighbors": []},
            },
            "current_flows": {"A": 0.2, "B": 0.9},
        }
        result = await model.predict(features, horizon_seconds=300)
        assert result.contributing_factors[0]["value"] == "B"


class TestPredictionEngine:
    """Tests for the PredictionEngine orchestrator."""

    @pytest.mark.asyncio
    async def test_predict_all_returns_results(self) -> None:
        """predict_all should return results for each (type, window)."""
        engine = PredictionEngine()
        features = {
            "history": [0.1, 0.2, 0.3, 0.4, 0.5],
            "prediction_type": "queue_growth",
        }
        results = await engine.predict_all(
            features,
            prediction_types=["queue_growth"],
            windows=[60, 300],
        )
        assert len(results) == 2
        assert all(isinstance(r, PredictionResult) for r in results)

    @pytest.mark.asyncio
    async def test_select_model_graph_for_bottleneck(self) -> None:
        """Bottleneck predictions should use GraphModel."""
        engine = PredictionEngine()
        data = {
            "zone_graph": {"A": {"neighbors": []}},
            "current_flows": {"A": 1.0},
        }
        model = engine.select_model("bottleneck", data)
        assert model.model_name == "graph_propagation"

    @pytest.mark.asyncio
    async def test_select_model_statistical_for_trend(self) -> None:
        """Queue growth should use StatisticalModel."""
        engine = PredictionEngine()
        data = {"history": [0.1, 0.2, 0.3]}
        model = engine.select_model("queue_growth", data)
        assert model.model_name == "statistical_ema_trend"

    @pytest.mark.asyncio
    async def test_select_model_rule_engine_for_threshold(self) -> None:
        """Threshold predictions should use RuleEngineModel."""
        engine = PredictionEngine()
        data = {"rules": [], "state": {}}
        model = engine.select_model("dangerous_density", data)
        assert model.model_name == "rule_engine"

    @pytest.mark.asyncio
    async def test_windows_default(self) -> None:
        """Default windows should be [30, 60, 180, 300, 600, 900]."""
        assert PREDICTION_WINDOWS == [30, 60, 180, 300, 600, 900]

    @pytest.mark.asyncio
    async def test_predict_all_sorted_by_confidence(self) -> None:
        """Results should be sorted by confidence descending."""
        engine = PredictionEngine()
        features = {"history": [0.1, 0.2, 0.3, 0.4, 0.5]}
        results = await engine.predict_all(
            features,
            prediction_types=["queue_growth"],
            windows=[30, 60, 180, 300],
        )
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.asyncio
    async def test_stats_tracking(self) -> None:
        """Stats should track prediction count."""
        engine = PredictionEngine()
        assert engine.stats["prediction_count"] == 0
        await engine.predict_all(
            {"history": [0.1, 0.2, 0.3]},
            prediction_types=["queue_growth"],
            windows=[60],
        )
        assert engine.stats["prediction_count"] > 0

    @pytest.mark.asyncio
    async def test_fallback_to_statistical(self) -> None:
        """Unknown prediction type should fall back to statistical model."""
        engine = PredictionEngine()
        data = {"history": [0.1, 0.2, 0.3]}
        model = engine.select_model("unknown_type", data)
        assert model.model_name == "statistical_ema_trend"
