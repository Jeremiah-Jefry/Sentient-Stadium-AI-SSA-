"""Event snapshot model — periodic state snapshots for fast time-travel queries."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EventSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Periodic snapshots capturing aggregate event state at fixed intervals.

    Enables O(1) historical state lookups instead of replaying the full event log.
    Snapshots are created at configurable intervals (e.g., every 60 seconds).
    """

    __tablename__ = "es_snapshots"
    __table_args__ = (
        Index("ix_es_snapshots_venue_id", "venue_id"),
        Index("ix_es_snapshots_venue_captured", "venue_id", "captured_at"),
        Index("ix_es_snapshots_interval_type", "interval_type"),
    )

    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    captured_at: Mapped[str] = mapped_column(String(30), nullable=False)
    interval_type: Mapped[str] = mapped_column(String(30), nullable=False, default="60s")

    total_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    events_by_category: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    events_by_severity: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    avg_response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    fusion_confidence_avg: Mapped[float | None] = mapped_column(Float, nullable=True)

    active_sensors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_sensors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    state_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
