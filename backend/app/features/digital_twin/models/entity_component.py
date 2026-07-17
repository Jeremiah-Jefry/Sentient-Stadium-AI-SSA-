"""Entity Component model - ECS architecture for extensible entity data."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EntityComponent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Component attached to an entity, following Entity Component System design.

    Each component stores a typed JSONB payload. Components include:
    - position: indoor coordinates, rotation
    - capacity: current/max, thresholds
    - accessibility: ramps, elevators, width requirements
    - security: camera coverage, checkpoint type
    - realtime_state: live sensor readings
    - sensor_data: IoT readings
    - medical: AED location, first aid capability
    - crowd: density readings, flow direction
    """

    __tablename__ = "dt_entity_components"
    __table_args__ = (
        Index("ix_dt_entity_components_entity_id", "entity_id"),
        Index(
            "ix_dt_entity_components_type",
            "entity_id", "component_type",
            unique=True,
        ),
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_entities.id", ondelete="CASCADE"), nullable=False,
    )
    component_type: Mapped[str] = mapped_column(String(50), nullable=False)
    component_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    entity: Mapped["Entity"] = relationship("Entity", back_populates="components")  # noqa: F821
