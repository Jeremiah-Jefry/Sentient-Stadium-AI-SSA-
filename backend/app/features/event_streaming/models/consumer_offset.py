"""Consumer offset model — tracks event processing progress for each consumer."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.features.event_streaming.models.event_type import ConsumerStatus
from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConsumerOffset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks the last processed event offset for each consumer.

    Enables at-least-once delivery semantics: consumers acknowledge
    processing via offset commits. Supports replay by resetting offsets.
    """

    __tablename__ = "es_consumer_offsets"
    __table_args__ = (
        Index("ix_es_consumer_offsets_consumer_id", "consumer_id", unique=True),
        Index("ix_es_consumer_offsets_status", "status"),
    )

    consumer_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    last_processed_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_processed_at: Mapped[str | None] = mapped_column(String(30), nullable=True)

    events_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    events_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_processing_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    status: Mapped[ConsumerStatus] = mapped_column(
        String(20), nullable=False, default=ConsumerStatus.HEALTHY,
    )
    is_replaying: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
