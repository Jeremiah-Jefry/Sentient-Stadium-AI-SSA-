"""Junction table linking Users to Roles with optional venue/event scope."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base, TimestampMixin


class UserRole(TimestampMixin, Base):
    """Many-to-many relationship between users and roles.

    Optionally scoped to a specific venue or event to support
    context-specific role assignments (e.g., a volunteer is a
    steward at Venue A but an usher at Venue B).
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        Index("ix_user_roles_user_id", "user_id"),
        Index("ix_user_roles_role_id", "role_id"),
        Index(
            "ix_user_roles_user_role",
            "user_id",
            "role_id",
            unique=True,
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    venue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Optional venue scope for the role assignment",
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Optional event scope for the role assignment",
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Optional expiration for temporary role assignments",
    )

    # Relationships
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="roles",
        lazy="selectin",
    )
    role: Mapped["Role"] = relationship(  # noqa: F821
        "Role",
        back_populates="user_roles",
        lazy="selectin",
    )
