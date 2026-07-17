"""Prediction store model — persists AI-generated predictions for analysis and feedback."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PredictionStore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores every prediction produced by the intelligence engine.

    Predictions carry a confidence breakdown, evidence references, and
    optional ground-truth fields so they can be evaluated for accuracy
    after the prediction window expires.
    """

    __tablename__ = "ai_predictions"
    __table_args__ = (
        Index("ix_ai_predictions_venue_id", "venue_id"),
        Index("ix_ai_predictions_zone_id", "zone_id"),
        Index("ix_ai_predictions_prediction_type", "prediction_type"),
        Index("ix_ai_predictions_predicted_at", "predicted_at"),
        Index("ix_ai_predictions_valid_until", "valid_until"),
        Index("ix_ai_predictions_venue_type", "venue_id", "prediction_type"),
    )

    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    prediction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    prediction_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    evidence_events: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    contributing_factors: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    model_version: Mapped[str] = mapped_column(String(100), nullable=False)

    is_accurate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
