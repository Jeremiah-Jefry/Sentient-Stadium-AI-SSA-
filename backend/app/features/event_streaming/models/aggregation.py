"""Event aggregation model — windowed aggregations for real-time dashboards."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EventAggregation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Pre-computed windowed aggregations for efficient dashboard queries.

    Aggregations are computed over configurable time windows (1min, 5min, 15min, 1h)
    per venue and optionally per zone. Stored incrementally for O(1) reads.
    """

    __tablename__ = "es_aggregations"
    __table_args__ = (
        Index("ix_es_agg_venue_id", "venue_id"),
        Index("ix_es_agg_zone_id", "zone_id"),
        Index("ix_es_agg_window", "window_type"),
        Index("ix_es_agg_venue_window_time", "venue_id", "window_type", "window_start"),
    )

    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    window_type: Mapped[str] = mapped_column(String(10), nullable=False)
    window_start: Mapped[str] = mapped_column(String(30), nullable=False)
    window_end: Mapped[str] = mapped_column(String(30), nullable=False)

    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    events_by_category: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    events_by_severity: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    peak_crowd_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_crowd_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    anomalies_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alerts_triggered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
