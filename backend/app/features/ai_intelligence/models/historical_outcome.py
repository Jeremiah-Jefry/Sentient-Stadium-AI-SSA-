"""Historical outcome model — post-intervention results for learning and calibration."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class HistoricalOutcome(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Records the observed outcome of an intervention for continuous improvement.

    Stores before/after risk levels, effectiveness flag, and optional
    lessons-learned notes so the reasoning engine can calibrate future
    decisions based on real-world results.
    """

    __tablename__ = "ai_historical_outcomes"
    __table_args__ = (
        Index("ix_ai_historical_outcomes_venue_id", "venue_id"),
        Index("ix_ai_historical_outcomes_outcome_type", "outcome_type"),
        Index("ix_ai_historical_outcomes_recorded_at", "recorded_at"),
    )

    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_decisions.id"),
        nullable=True,
    )

    outcome_type: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_level_before: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level_after: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_score_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    intervention_effective: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    affected_zone_count: Mapped[int] = mapped_column(Integer, nullable=False)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
