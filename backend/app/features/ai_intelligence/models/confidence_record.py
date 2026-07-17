"""Confidence record model — detailed breakdown of prediction confidence scores."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConfidenceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores the full confidence breakdown for a single prediction.

    Each record decomposes overall confidence into contributing factors
    so the system can explain why a prediction is trusted or not.
    """

    __tablename__ = "ai_confidence_records"
    __table_args__ = (
        Index("ix_ai_confidence_records_prediction_id", "prediction_id"),
    )

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_predictions.id"),
        nullable=False,
    )
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    sensor_agreement: Mapped[float] = mapped_column(Float, nullable=False)
    historical_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    model_agreement: Mapped[float] = mapped_column(Float, nullable=False)
    data_freshness_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)

    reasoning: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
