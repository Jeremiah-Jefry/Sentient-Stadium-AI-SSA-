"""Prediction repository — data access for the AI prediction store."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.ai_intelligence.models.prediction import PredictionStore
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)


class PredictionRepository:
    """Handles all database operations for PredictionStore."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, prediction: PredictionStore) -> Result[PredictionStore]:
        """Persist a single prediction."""
        self._session.add(prediction)
        await self._session.flush()
        logger.debug("Prediction saved: %s", prediction.id)
        return Success(prediction)

    async def save_many(
        self, predictions: list[PredictionStore],
    ) -> Result[list[PredictionStore]]:
        """Batch-insert predictions atomically."""
        self._session.add_all(predictions)
        await self._session.flush()
        logger.debug("Batch saved %d predictions", len(predictions))
        return Success(predictions)

    async def get_by_id(
        self, prediction_id: uuid.UUID,
    ) -> Result[PredictionStore | None]:
        """Fetch a single prediction by UUID."""
        stmt = select(PredictionStore).where(PredictionStore.id == prediction_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_active_by_venue(
        self,
        venue_id: uuid.UUID,
        zone_id: uuid.UUID | None = None,
        min_confidence: float = 0.0,
        page: int = 1,
        page_size: int = 50,
    ) -> Result[tuple[list[PredictionStore], int]]:
        """Query active (non-expired) predictions with filters and pagination."""
        now = datetime.now(timezone.utc)
        base_query = (
            select(PredictionStore)
            .where(
                PredictionStore.venue_id == venue_id,
                PredictionStore.valid_until > now,
                PredictionStore.confidence >= min_confidence,
            )
        )
        if zone_id is not None:
            base_query = base_query.where(PredictionStore.zone_id == zone_id)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = (
            base_query
            .order_by(PredictionStore.confidence.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(paginated)
        predictions = list(result.scalars().all())
        return Success((predictions, total))

    async def get_expired(
        self, before: datetime,
    ) -> Result[list[PredictionStore]]:
        """Fetch predictions that expired before the given timestamp."""
        stmt = (
            select(PredictionStore)
            .where(PredictionStore.valid_until <= before)
            .order_by(PredictionStore.valid_until.desc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def evaluate_accuracy(
        self, prediction_id: uuid.UUID, actual_value: float,
    ) -> Result[PredictionStore]:
        """Mark a prediction as evaluated with ground truth."""
        stmt = select(PredictionStore).where(PredictionStore.id == prediction_id)
        result = await self._session.execute(stmt)
        prediction = result.scalar_one_or_none()

        if prediction is None:
            return Failure(
                error_code="PREDICTION_NOT_FOUND",
                message=f"Prediction {prediction_id} not found",
            )

        prediction.actual_value = actual_value
        threshold = prediction.predicted_value * 0.1
        prediction.is_accurate = abs(prediction.predicted_value - actual_value) <= abs(threshold)
        prediction.evaluated_at = datetime.now(timezone.utc)
        await self._session.flush()
        logger.debug(
            "Prediction %s evaluated: accurate=%s",
            prediction_id, prediction.is_accurate,
        )
        return Success(prediction)

    async def get_accuracy_stats(
        self, venue_id: uuid.UUID, prediction_type: str | None = None,
    ) -> Result[dict]:
        """Compute accuracy statistics for evaluated predictions."""
        base_query = (
            select(PredictionStore)
            .where(
                PredictionStore.venue_id == venue_id,
                PredictionStore.is_accurate.isnot(None),
            )
        )
        if prediction_type is not None:
            base_query = base_query.where(
                PredictionStore.prediction_type == prediction_type,
            )

        result = await self._session.execute(base_query)
        predictions = list(result.scalars().all())

        total = len(predictions)
        correct = sum(1 for p in predictions if p.is_accurate is True)
        false_positives = sum(
            1 for p in predictions
            if p.is_accurate is False and p.predicted_value > 0
        )
        false_negatives = sum(
            1 for p in predictions
            if p.is_accurate is False and p.predicted_value == 0
        )

        avg_confidence = (
            sum(p.confidence for p in predictions) / total if total > 0 else 0.0
        )
        avg_abs_error = (
            sum(
                abs((p.predicted_value or 0) - (p.actual_value or 0))
                for p in predictions
            )
            / total
            if total > 0
            else 0.0
        )

        return Success({
            "venue_id": str(venue_id),
            "prediction_type": prediction_type,
            "total_evaluated": total,
            "correct": correct,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "accuracy_rate": round(correct / total, 4) if total > 0 else 0.0,
            "false_positive_rate": round(false_positives / total, 4) if total > 0 else 0.0,
            "false_negative_rate": round(false_negatives / total, 4) if total > 0 else 0.0,
            "avg_confidence": round(avg_confidence, 4),
            "avg_absolute_error": round(avg_abs_error, 4),
        })
