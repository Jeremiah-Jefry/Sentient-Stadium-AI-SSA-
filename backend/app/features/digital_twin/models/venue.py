"""Venue model - top-level stadium container for all entities."""

from __future__ import annotations

import uuid

from sqlalchemy import Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Venue(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Top-level venue entity representing a physical stadium.

    All zones, entities, and edges belong to a venue.
    Supports PostGIS polygon geometry for the stadium boundary.
    """

    __tablename__ = "dt_venues"
    __table_args__ = (
        Index("ix_dt_venues_name", "name"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    coordinates_lat: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    coordinates_lon: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    zones: Mapped[list["Zone"]] = relationship(  # noqa: F821
        "Zone",
        back_populates="venue",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    entities: Mapped[list["Entity"]] = relationship(  # noqa: F821
        "Entity",
        back_populates="venue",
        lazy="dynamic",
    )
