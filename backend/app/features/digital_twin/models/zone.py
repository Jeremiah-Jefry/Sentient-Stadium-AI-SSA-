"""Zone model - hierarchical spatial subdivision of the stadium."""

from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.features.digital_twin.models.entity_state import ZoneType
from app.shared.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Zone(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Hierarchical zone supporting unlimited nesting depth.

    Stadium -> Sector -> Zone -> SubZone -> Gate -> Checkpoint -> Node.
    Self-referential parent_zone_id enables arbitrary tree depth.
    PostGIS polygon geometry defines spatial boundaries.
    """

    __tablename__ = "dt_zones"
    __table_args__ = (
        Index("ix_dt_zones_venue_id", "venue_id"),
        Index("ix_dt_zones_parent_zone_id", "parent_zone_id"),
        Index("ix_dt_zones_zone_type", "zone_type"),
        Index("ix_dt_zones_level", "level"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    zone_type: Mapped[ZoneType] = mapped_column(
        Enum(ZoneType, native_enum=False), nullable=False, default=ZoneType.ZONE,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_zones.id", ondelete="SET NULL"), nullable=True,
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_venues.id", ondelete="CASCADE"), nullable=False,
    )
    bounds_lat_min: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    bounds_lat_max: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    bounds_lon_min: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    bounds_lon_max: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    venue: Mapped["Venue"] = relationship("Venue", back_populates="zones", lazy="selectin")  # noqa: F821
    parent_zone: Mapped["Zone | None"] = relationship(
        "Zone", remote_side="Zone.id", lazy="selectin",
    )
    child_zones: Mapped[list["Zone"]] = relationship(
        "Zone", back_populates="parent_zone", lazy="selectin",
    )
    entities: Mapped[list["Entity"]] = relationship(  # noqa: F821
        "Entity", back_populates="zone", lazy="dynamic",
    )
