"""User management response DTOs for profile data and admin views."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.features.auth.models.user import AuthProvider, UserStatus


class RoleSummary(BaseModel):
    """Minimal role information included in user responses."""

    id: UUID
    name: str
    display_name: str
    scope: str

    model_config = {"from_attributes": True}


class PermissionSummary(BaseModel):
    """Minimal permission information included in role details."""

    id: UUID
    name: str
    resource: str
    action: str

    model_config = {"from_attributes": True}


class UserProfileResponse(BaseModel):
    """Full user profile returned to the authenticated user."""

    id: UUID
    email: str
    display_name: str
    photo_url: str | None = None
    phone_number: str | None = None
    auth_provider: AuthProvider
    email_verified: bool
    status: UserStatus
    roles: list[RoleSummary] = []
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminUserResponse(BaseModel):
    """Extended user information for admin views including security details."""

    id: UUID
    email: str
    display_name: str
    photo_url: str | None = None
    phone_number: str | None = None
    firebase_uid: str
    auth_provider: AuthProvider
    email_verified: bool
    status: UserStatus
    roles: list[RoleSummary] = []
    failed_login_attempts: int
    locked_until: datetime | None = None
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: list = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class SessionResponse(BaseModel):
    """Active session information for device management."""

    id: UUID
    device_info: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    last_active_at: datetime
    is_current: bool = False

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    """Audit log entry for security event review."""

    id: UUID
    event_type: str
    ip_address: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict | None = None
    risk_score: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PermissionDetailResponse(BaseModel):
    """Full permission details for a role."""

    role_id: UUID
    role_name: str
    permissions: list[PermissionSummary] = []
