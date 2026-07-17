"""Core Entity model - every physical object in the stadium becomes an Entity."""

from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.features.digital_twin.models.entity_state import (
    AccessibilityLevel,
    EntityHealth,
    OperationalStatus,
)
from app.features.digital_twin.models.entity_type import EntityType
from app.shared.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Entity(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Universal entity representing any physical or logical stadium object.

    Uses Entity Component System (ECS) architecture: core properties live
    on this table; specialized data lives in EntityComponent rows (JSONB).
    PostGIS geometry columns enable spatial queries.
    """

    __tablename__ = "dt_entities"
    __table_args__ = (
        Index("ix_dt_entities_venue_id", "venue_id"),
        Index("ix_dt_entities_zone_id", "zone_id"),
        Index("ix_dt_entities_type", "entity_type"),
        Index("ix_dt_entities_operational_status", "operational_status"),
        Index("ix_dt_entities_parent_id", "parent_id"),
        Index(
            "ix_dt_entities_coords",
            "coordinates_lat", "coordinates_lon",
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, native_enum=False), nullable=False,
    )

    # Real-time state
    current_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    operational_status: Mapped[OperationalStatus] = mapped_column(
        Enum(OperationalStatus, native_enum=False),
        nullable=False, default=OperationalStatus.OPERATIONAL,
    )
    current_health: Mapped[EntityHealth] = mapped_column(
        Enum(EntityHealth, native_enum=False),
        nullable=False, default=EntityHealth.HEALTHY,
    )

    # Capacity
    current_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Outdoor coordinates (WGS84)
    coordinates_lat: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    coordinates_lon: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)

    # Indoor coordinates (optional)
    indoor_x: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    indoor_y: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    floor_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    building_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Accessibility
    accessibility_level: Mapped[AccessibilityLevel] = mapped_column(
        Enum(AccessibilityLevel, native_enum=False),
        nullable=False, default=AccessibilityLevel.FULL,
    )
    accessibility_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Flexible metadata
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Hierarchical relationships
    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_venues.id", ondelete="CASCADE"), nullable=False,
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_zones.id", ondelete="SET NULL"), nullable=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_entities.id", ondelete="SET NULL"), nullable=True,
    )

    # Relationships
    venue: Mapped["Venue"] = relationship("Venue", back_populates="entities", lazy="selectin")  # noqa: F821
    zone: Mapped["Zone | None"] = relationship("Zone", back_populates="entities", lazy="selectin")  # noqa: F821
    parent: Mapped["Entity | None"] = relationship(
        "Entity", remote_side="Entity.id", lazy="selectin",
    )
    children: Mapped[list["Entity"]] = relationship(
        "Entity", back_populates="parent", lazy="dynamic",
    )
    components: Mapped[list["EntityComponent"]] = relationship(  # noqa: F821
        "EntityComponent", back_populates="entity", lazy="selectin",
        cascade="all, delete-orphan",
    )
