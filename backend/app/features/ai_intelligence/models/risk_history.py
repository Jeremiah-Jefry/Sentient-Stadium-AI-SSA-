"""Risk history model — time-series record of venue and zone risk assessments."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RiskHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Chronological record of every risk assessment produced by the engine.

    Captures both the aggregate risk level and per-domain risk scores so
    that trends can be analysed and anomaly thresholds tuned over time.
    """

    __tablename__ = "ai_risk_history"
    __table_args__ = (
        Index("ix_ai_risk_history_venue_id", "venue_id"),
        Index("ix_ai_risk_history_zone_id", "zone_id"),
        Index("ix_ai_risk_history_risk_level", "risk_level"),
        Index("ix_ai_risk_history_assessed_at", "assessed_at"),
        Index("ix_ai_risk_history_venue_level", "venue_id", "risk_level"),
    )

    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_factors: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    contributing_events: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    venue_risk: Mapped[float] = mapped_column(Float, nullable=False)
    zone_risk: Mapped[float] = mapped_column(Float, nullable=False)
    medical_risk: Mapped[float] = mapped_column(Float, nullable=False)
    security_risk: Mapped[float] = mapped_column(Float, nullable=False)
    accessibility_risk: Mapped[float] = mapped_column(Float, nullable=False)
    transport_risk: Mapped[float] = mapped_column(Float, nullable=False)
    weather_risk: Mapped[float] = mapped_column(Float, nullable=False)

    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
