"""Decision history model — full lifecycle of autonomous intervention decisions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DecisionHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Records every intervention decision from proposal through execution.

    Stores the full reasoning chain, alternative decisions considered,
    and expected vs actual outcomes for post-match analysis.
    """

    __tablename__ = "ai_decisions"
    __table_args__ = (
        Index("ix_ai_decisions_venue_id", "venue_id"),
        Index("ix_ai_decisions_decision_status", "decision_status"),
        Index("ix_ai_decisions_intervention_type", "intervention_type"),
        Index("ix_ai_decisions_published_at", "published_at"),
    )

    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    decision_status: Mapped[str] = mapped_column(String(30), nullable=False)
    intervention_type: Mapped[str] = mapped_column(String(50), nullable=False)
    intervention_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    risk_level_at_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    reasoning: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    alternative_decisions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    expected_outcome: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    actual_outcome: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
