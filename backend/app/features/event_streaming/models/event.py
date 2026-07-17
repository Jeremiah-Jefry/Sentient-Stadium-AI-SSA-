"""Core event store model — the append-only event log for the entire platform."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.features.event_streaming.models.event_type import (
    EventCategory,
    EventPriority,
    EventSeverity,
    ProcessingStatus,
)
from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StoredEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable event record stored in the append-only event store.

    Every sensor reading, AI decision, and system action produces a StoredEvent.
    Events are never updated or deleted — integrity depends on immutability.
    """

    __tablename__ = "es_events"
    __table_args__ = (
        Index("ix_es_events_producer", "producer"),
        Index("ix_es_events_category", "category"),
        Index("ix_es_events_priority", "priority"),
        Index("ix_es_events_severity", "severity"),
        Index("ix_es_events_status", "processing_status"),
        Index("ix_es_events_entity_id", "entity_id"),
        Index("ix_es_events_venue_id", "venue_id"),
        Index("ix_es_events_correlation_id", "correlation_id"),
        Index("ix_es_events_captured_at", "captured_at"),
        Index("ix_es_events_category_venue", "category", "venue_id"),
        Index("ix_es_events_entity_captured", "entity_id", "captured_at"),
    )

    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parent_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[EventCategory] = mapped_column(String(50), nullable=False)
    priority: Mapped[EventPriority] = mapped_column(
        String(20), nullable=False, default=EventPriority.NORMAL,
    )
    severity: Mapped[EventSeverity] = mapped_column(
        String(20), nullable=False, default=EventSeverity.INFO,
    )

    source: Mapped[str] = mapped_column(String(200), nullable=False)
    producer: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    venue_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    captured_at: Mapped[str] = mapped_column(String(30), nullable=False)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        String(30), nullable=False, default=ProcessingStatus.RECEIVED,
    )

    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    ttl_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    processing_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
