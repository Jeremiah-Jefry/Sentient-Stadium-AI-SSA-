"""Junction table linking Roles to Permissions."""

import uuid

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base, TimestampMixin


class RolePermission(TimestampMixin, Base):
    """Many-to-many relationship between roles and permissions.

    Each row grants a specific permission to a specific role.
    Users inherit all permissions from their assigned roles.
    """

    __tablename__ = "role_permissions"
    __table_args__ = (
        Index("ix_role_permissions_role_id", "role_id"),
        Index("ix_role_permissions_permission_id", "permission_id"),
        Index(
            "ix_role_permissions_role_permission",
            "role_id",
            "permission_id",
            unique=True,
        ),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )

    # Relationships
    role: Mapped["Role"] = relationship(  # noqa: F821
        "Role",
        back_populates="permissions",
        lazy="selectin",
    )
    permission: Mapped["Permission"] = relationship(  # noqa: F821
        "Permission",
        back_populates="role_permissions",
        lazy="selectin",
    )
