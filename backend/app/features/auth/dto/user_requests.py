"""User management request DTOs for profile updates and admin operations."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.features.auth.models.user import UserStatus
from app.shared.utils.sanitization import MAX_NAME_LENGTH, MAX_EMAIL_LENGTH


class UpdateProfileRequest(BaseModel):
    """Request to update the authenticated user's profile."""

    display_name: str | None = Field(None, min_length=1, max_length=MAX_NAME_LENGTH)
    photo_url: str | None = Field(None, max_length=2048)
    phone_number: str | None = Field(None, max_length=20)


class AdminUpdateUserRequest(BaseModel):
    """Admin request to update any user's profile or status."""

    display_name: str | None = Field(None, min_length=1, max_length=MAX_NAME_LENGTH)
    email: EmailStr | None = Field(None, max_length=MAX_EMAIL_LENGTH)
    phone_number: str | None = Field(None, max_length=20)
    status: UserStatus | None = None
    photo_url: str | None = Field(None, max_length=2048)


class AssignRoleRequest(BaseModel):
    """Request to assign a role to a user."""

    role_id: UUID
    venue_id: UUID | None = None
    event_id: UUID | None = None
    expires_at: str | None = Field(
        None,
        description="ISO 8601 datetime for temporary role assignment",
    )


class RevokeRoleRequest(BaseModel):
    """Request to revoke a role from a user."""

    role_id: UUID
    venue_id: UUID | None = None
    event_id: UUID | None = None


class UserQueryParams(BaseModel):
    """Query parameters for user listing and search."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(None, max_length=100)
    status: UserStatus | None = None
    role: str | None = None
    sort_by: str = Field(default="created_at", pattern=r"^(created_at|email|display_name|last_login_at)$")
    sort_order: str = Field(default="desc", pattern=r"^(asc|desc)$")
