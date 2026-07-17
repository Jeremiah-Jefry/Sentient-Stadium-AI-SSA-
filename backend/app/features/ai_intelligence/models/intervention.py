"""Intervention result model — tracks simulated and actual intervention outcomes."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InterventionResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Captures the result of executing or simulating an intervention.

    Compares simulated vs actual risk reduction and confidence to
    continuously improve the decision engine's accuracy.
    """

    __tablename__ = "ai_interventions"
    __table_args__ = (
        Index("ix_ai_interventions_decision_id", "decision_id"),
    )

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_decisions.id"),
        nullable=False,
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    intervention_type: Mapped[str] = mapped_column(String(50), nullable=False)
    strategy_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    simulated_risk_reduction: Mapped[float] = mapped_column(Float, nullable=False)
    simulated_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    actual_risk_reduction: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    execution_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_effective: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
