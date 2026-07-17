"""Navigation database models — route cache, history, sessions, feedback."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class RouteCache(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Cached route computation results for fast repeated queries."""

    __tablename__ = "nav_route_cache"
    __table_args__ = (
        Index("ix_nav_route_cache_origin_dest", "origin_id", "destination_id"),
        Index("ix_nav_route_cache_venue_id", "venue_id"),
        Index("ix_nav_route_cache_expires_at", "expires_at"),
    )

    origin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    profile: Mapped[str] = mapped_column(String(50), nullable=False)
    route_type: Mapped[str] = mapped_column(String(50), nullable=False)
    route_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    graph_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )


class RouteHistory(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Record of all computed routes for analytics and optimization."""

    __tablename__ = "nav_route_history"
    __table_args__ = (
        Index("ix_nav_route_history_user_id", "user_id"),
        Index("ix_nav_route_history_venue_id", "venue_id"),
        Index("ix_nav_route_history_created_at", "created_at"),
        Index("ix_nav_route_history_profile", "profile"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    origin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    profile: Mapped[str] = mapped_column(String(50), nullable=False)
    route_type: Mapped[str] = mapped_column(String(50), nullable=False)
    route_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    total_distance_meters: Mapped[float] = mapped_column(Float, nullable=False)
    total_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grade: Mapped[str] = mapped_column(String(5), nullable=False, default="C")
    algorithm_used: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    computation_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    was_replanned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class NavigationSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Active navigation session tracking user progress along a route."""

    __tablename__ = "nav_sessions"
    __table_args__ = (
        Index("ix_nav_sessions_user_id", "user_id"),
        Index("ix_nav_sessions_venue_id", "venue_id"),
        Index("ix_nav_sessions_status", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nav_route_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    origin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    current_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
    )
    profile: Mapped[str] = mapped_column(String(50), nullable=False)
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    replan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RouteFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User feedback on computed routes for quality improvement."""

    __tablename__ = "nav_route_feedback"
    __table_args__ = (
        Index("ix_nav_route_feedback_route_id", "route_id"),
        Index("ix_nav_route_feedback_user_id", "user_id"),
    )

    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nav_route_history.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    deviated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    actual_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
