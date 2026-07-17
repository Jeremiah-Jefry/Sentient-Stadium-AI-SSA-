"""Entity Version model - immutable state snapshots for audit and rollback."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EntityVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Versioned snapshot of an entity's complete state at a point in time.

    Supports audit trail, rollback, timeline visualization, and diff tracking.
    Each version stores the full state snapshot as JSONB.
    """

    __tablename__ = "dt_entity_versions"
    __table_args__ = (
        Index("ix_dt_entity_versions_entity_id", "entity_id"),
        Index(
            "ix_dt_entity_versions_entity_version",
            "entity_id", "version",
            unique=True,
        ),
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_entities.id", ondelete="CASCADE"), nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    state_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
