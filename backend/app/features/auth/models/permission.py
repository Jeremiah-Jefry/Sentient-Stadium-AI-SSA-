"""Permission domain model for fine-grained access control."""

import uuid

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Permission entity representing a single atomic action.

    Permissions follow the format: resource:action
    Examples: user:read, venue:write, event:delete, agent:invoke

    Permissions are assigned to roles, never directly to users.
    """

    __tablename__ = "permissions"
    __table_args__ = (
        Index("ix_permissions_name", "name", unique=True, postgresql_where="deleted_at IS NULL"),
        Index("ix_permissions_resource", "resource"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    role_permissions: Mapped[list["RolePermission"]] = relationship(  # noqa: F821
        "RolePermission",
        back_populates="permission",
        lazy="dynamic",
    )
