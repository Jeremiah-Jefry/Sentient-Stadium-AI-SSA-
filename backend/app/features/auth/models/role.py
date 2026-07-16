"""Role domain model for Role-Based Access Control."""

import enum
import uuid

from sqlalchemy import Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class RoleScope(str, enum.Enum):
    """Defines the scope at which a role operates."""

    SYSTEM = "system"
    VENUE = "venue"
    EVENT = "event"


class Role(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Role entity for RBAC. Each role groups a set of permissions.

    Roles are assignable to users. A user inherits all permissions
    from all their assigned roles.
    """

    __tablename__ = "roles"
    __table_args__ = (
        Index("ix_roles_name", "name", unique=True, postgresql_where="deleted_at IS NULL"),
        Index("ix_roles_scope", "scope"),
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[RoleScope] = mapped_column(
        Enum(RoleScope, native_enum=False),
        nullable=False,
        default=RoleScope.SYSTEM,
    )
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    permissions: Mapped[list["RolePermission"]] = relationship(  # noqa: F821
        "RolePermission",
        back_populates="role",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(  # noqa: F821
        "UserRole",
        back_populates="role",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
