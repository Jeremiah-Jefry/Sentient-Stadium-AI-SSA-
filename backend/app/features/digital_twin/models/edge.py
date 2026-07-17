"""Edge model - weighted graph connections between entities for pathfinding."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.features.digital_twin.models.entity_state import AccessibilityLevel
from app.shared.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class EdgeType(str, enum.Enum):
    """Traversal type for a graph edge connecting two entities."""

    WALKING = "walking"
    WHEELCHAIR = "wheelchair"
    EMERGENCY = "emergency"
    STAFF_ONLY = "staff_only"
    RESTRICTED = "restricted"
    MAINTENANCE = "maintenance"


class Edge(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Directed or bidirectional graph edge between two entities.

    Forms the spatial graph that powers pathfinding, shortest-route,
    and accessibility-route queries. Weight represents distance in meters.
    """

    __tablename__ = "dt_edges"
    __table_args__ = (
        Index("ix_dt_edges_from_entity_id", "from_entity_id"),
        Index("ix_dt_edges_to_entity_id", "to_entity_id"),
        Index("ix_dt_edges_edge_type", "edge_type"),
        Index("ix_dt_edges_venue_id", "venue_id"),
    )

    from_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_entities.id", ondelete="CASCADE"), nullable=False,
    )
    to_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_entities.id", ondelete="CASCADE"), nullable=False,
    )
    edge_type: Mapped[EdgeType] = mapped_column(
        Enum(EdgeType, native_enum=False), nullable=False, default=EdgeType.WALKING,
    )
    weight: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=1.0)
    is_bidirectional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    accessibility_level: Mapped[AccessibilityLevel] = mapped_column(
        Enum(AccessibilityLevel, native_enum=False),
        nullable=False, default=AccessibilityLevel.FULL,
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dt_venues.id", ondelete="CASCADE"), nullable=False,
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    from_entity: Mapped["Entity"] = relationship(  # noqa: F821
        "Entity", foreign_keys=[from_entity_id], lazy="selectin",
    )
    to_entity: Mapped["Entity"] = relationship(  # noqa: F821
        "Entity", foreign_keys=[to_entity_id], lazy="selectin",
    )
