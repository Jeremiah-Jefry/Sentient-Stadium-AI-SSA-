"""User domain model - the core identity entity."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AuthProvider(str, enum.Enum):
    """Authentication provider enum."""

    EMAIL_PASSWORD = "email_password"
    GOOGLE = "google"
    FIREBASE = "firebase"


class UserStatus(str, enum.Enum):
    """User account status enum."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    LOCKED = "locked"


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """User entity representing any person who interacts with StadiumMind OS.

    Stores identity data from Firebase Authentication and local RBAC data.
    Firebase owns the auth provider data; this table owns the platform profile.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email", unique=True, postgresql_where="deleted_at IS NULL"),
        Index("ix_users_firebase_uid", "firebase_uid", unique=True, postgresql_where="deleted_at IS NULL"),
        Index("ix_users_status", "status"),
    )

    firebase_uid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, native_enum=False),
        nullable=False,
        default=AuthProvider.EMAIL_PASSWORD,
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, native_enum=False),
        nullable=False,
        default=UserStatus.PENDING_VERIFICATION,
    )

    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Relationships
    roles: Mapped[list["UserRole"]] = relationship(  # noqa: F821
        "UserRole",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["UserSession"]] = relationship(  # noqa: F821
        "UserSession",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # noqa: F821
        "AuditLog",
        back_populates="user",
        lazy="dynamic",
    )
