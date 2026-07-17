"""Entity Event model - append-only event log for entity state changes."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EntityEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable event record published when any entity state changes.

    Enables event-driven architecture: AI agents, dashboards, and
    downstream systems subscribe to these events.
    """

    __tablename__ = "dt_entity_events"
    __table_args__ = (
        Index("ix_dt_entity_events_entity_id", "entity_id"),
        Index("ix_dt_entity_events_event_type", "event_type"),
        Index("ix_dt_entity_events_created_at", "created_at"),
        Index("ix_dt_entity_events_entity_type", "entity_id", "event_type"),
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_entities.id", ondelete="CASCADE"), nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    source: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system",
    )
