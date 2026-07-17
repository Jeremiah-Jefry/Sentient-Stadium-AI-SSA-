"""Monitoring service — tracks prediction accuracy, latency, and model drift metrics."""

from __future__ import annotations

import logging
from collections import deque

logger = logging.getLogger(__name__)

DEFAULT_MAX_LATENCY_WINDOW: int = 1000


class MonitoringService:
    """Tracks prediction accuracy, false positives/negatives, latency, and model drift."""

    def __init__(self) -> None:
        self._latencies: deque[float] = deque(maxlen=DEFAULT_MAX_LATENCY_WINDOW)
        self._predictions_made = 0
        self._predictions_evaluated = 0
        self._correct_predictions = 0
        self._false_positives = 0
        self._false_negatives = 0
        self._recommendations_published = 0
        self._recommendations_acted_on = 0
        self._max_latency_window = DEFAULT_MAX_LATENCY_WINDOW

    def record_latency(self, latency_ms: float) -> None:
        """Record pipeline processing latency in milliseconds."""
        self._latencies.append(latency_ms)
        logger.debug("Latency recorded: %.2f ms", latency_ms)

    def record_prediction(
        self, prediction_id: str, was_correct: bool | None = None,
    ) -> None:
        """Record a prediction and optionally its evaluation result."""
        self._predictions_made += 1
        if was_correct is not None:
            self._predictions_evaluated += 1
            if was_correct:
                self._correct_predictions += 1
            else:
                self._false_positives += 1
        logger.debug(
            "Prediction recorded: id=%s correct=%s total=%d",
            prediction_id, was_correct, self._predictions_made,
        )

    def record_recommendation(
        self, decision_id: str, was_acted_on: bool | None = None,
    ) -> None:
        """Record a recommendation and optionally whether it was acted on."""
        self._recommendations_published += 1
        if was_acted_on is not None and was_acted_on:
            self._recommendations_acted_on += 1
        logger.debug(
            "Recommendation recorded: id=%s acted_on=%s",
            decision_id, was_acted_on,
        )

    def compute_accuracy(self) -> float:
        """Compute current prediction accuracy (0.0 to 1.0)."""
        if self._predictions_evaluated == 0:
            return 0.0
        return self._correct_predictions / self._predictions_evaluated

    def compute_false_positive_rate(self) -> float:
        """Compute false positive rate among evaluated predictions."""
        total_negative = self._predictions_evaluated - self._correct_predictions
        if total_negative <= 0:
            return 0.0
        return self._false_positives / total_negative

    def compute_false_negative_rate(self) -> float:
        """Compute false negative rate (missed true positives)."""
        if self._predictions_evaluated == 0:
            return 0.0
        total_fn = self._predictions_evaluated - self._correct_predictions - self._false_positives
        if total_fn <= 0:
            return 0.0
        return max(0.0, total_fn / self._predictions_evaluated)

    @property
    def stats(self) -> dict:
        """All monitoring statistics."""
        latencies = list(self._latencies)
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        p95_latency = (
            sorted(latencies)[int(len(latencies) * 0.95)]
            if len(latencies) > 1
            else avg_latency
        )
        p99_latency = (
            sorted(latencies)[int(len(latencies) * 0.99)]
            if len(latencies) > 1
            else avg_latency
        )

        return {
            "predictions_made": self._predictions_made,
            "predictions_evaluated": self._predictions_evaluated,
            "correct_predictions": self._correct_predictions,
            "false_positives": self._false_positives,
            "false_negatives": self._false_negatives,
            "accuracy_rate": round(self.compute_accuracy(), 4),
            "false_positive_rate": round(self.compute_false_positive_rate(), 4),
            "false_negative_rate": round(self.compute_false_negative_rate(), 4),
            "recommendations_published": self._recommendations_published,
            "recommendations_acted_on": self._recommendations_acted_on,
            "adoption_rate": round(
                self._recommendations_acted_on / self._recommendations_published
                if self._recommendations_published > 0 else 0.0, 4,
            ),
            "latency_avg_ms": round(avg_latency, 2),
            "latency_p95_ms": round(p95_latency, 2),
            "latency_p99_ms": round(p99_latency, 2),
            "latency_samples": len(latencies),
        }
