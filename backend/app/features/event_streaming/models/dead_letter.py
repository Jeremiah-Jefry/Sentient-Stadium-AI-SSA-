"""Dead letter event model — stores events that failed processing after exhausting retries."""

from __future__ import annotations

from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DeadLetterEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Events that failed processing after exhausting all retry attempts.

    Enables manual inspection, reprocessing, and root cause analysis.
    Once reprocessed, the event is marked resolved.
    """

    __tablename__ = "es_dead_letter_events"
    __table_args__ = (
        Index("ix_es_dlq_original_event_id", "original_event_id"),
        Index("ix_es_dlq_error_type", "error_type"),
        Index("ix_es_dlq_is_resolved", "is_resolved"),
        Index("ix_es_dlq_failed_at", "created_at"),
    )

    original_event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    original_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_retry_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    processing_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_resolved: Mapped[bool] = mapped_column(nullable=False, default=False)
    resolved_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
