"""Admin API routes - user management, role assignment, and system oversight."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.features.auth.api.deps import (
    AuthenticatedUser,
    get_current_user,
    require_role,
)
from app.features.auth.dto.user_requests import (
    AdminUpdateUserRequest,
    AssignRoleRequest,
    RevokeRoleRequest,
)
from app.features.auth.dto.user_responses import (
    AdminUserResponse,
    AuditLogResponse,
    PaginatedResponse,
    PermissionDetailResponse,
)
from app.features.auth.models.user import UserStatus
from app.features.auth.repositories.audit_repository import AuditRepository
from app.features.auth.repositories.role_repository import RoleRepository
from app.features.auth.repositories.user_repository import UserRepository
from app.features.auth.services.rbac_service import RBACService
from app.shared.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["Administration"])

# All admin routes require the "admin" role
_admin_only = require_role("admin")


@router.get(
    "/users",
    response_model=PaginatedResponse,
    summary="List all users with filtering and pagination",
)
async def list_users(
    _admin: Annotated[AuthenticatedUser, Depends(_admin_only)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=100),
    status: UserStatus | None = Query(default=None),
) -> PaginatedResponse:
    repo = UserRepository(session)
    users, total = (await repo.list_users(page, page_size, search, status)).value
    items = [AdminUserResponse.model_validate(u) for u in users]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Get detailed user information",
)
async def get_user(
    user_id: uuid.UUID,
    _admin: Annotated[AuthenticatedUser, Depends(_admin_only)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminUserResponse:
    repo = UserRepository(session)
    result = await repo.get_by_id(user_id)
    return AdminUserResponse.model_validate(result.value)


@router.put(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update a user's profile or status",
)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUpdateUserRequest,
    _admin: Annotated[AuthenticatedUser, Depends(_admin_only)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminUserResponse:
    repo = UserRepository(session)
    result = await repo.get_by_id(user_id)
    user = result.value
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await repo.update(user)
    return AdminUserResponse.model_validate(user)


@router.post(
    "/users/{user_id}/roles",
    status_code=201,
    summary="Assign a role to a user",
)
async def assign_role(
    user_id: uuid.UUID,
    body: AssignRoleRequest,
    admin: Annotated[AuthenticatedUser, Depends(_admin_only)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    role_repo = RoleRepository(session)
    rbac = RBACService(role_repo)
    await rbac.assign_role(
        user_id=user_id,
        role_id=body.role_id,
        assigned_by=admin.user_id,
        venue_id=body.venue_id,
        event_id=body.event_id,
    )
    return {"message": "Role assigned successfully"}


@router.delete(
    "/users/{user_id}/roles",
    status_code=200,
    summary="Revoke a role from a user",
)
async def revoke_role(
    user_id: uuid.UUID,
    body: RevokeRoleRequest,
    _admin: Annotated[AuthenticatedUser, Depends(_admin_only)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    role_repo = RoleRepository(session)
    rbac = RBACService(role_repo)
    await rbac.revoke_role(
        user_id=user_id,
        role_id=body.role_id,
        venue_id=body.venue_id,
        event_id=body.event_id,
    )
    return {"message": "Role revoked successfully"}


@router.get(
    "/users/{user_id}/permissions",
    response_model=PermissionDetailResponse,
    summary="Get all permissions for a user's roles",
)
async def get_user_permissions(
    user_id: uuid.UUID,
    _admin: Annotated[AuthenticatedUser, Depends(_admin_only)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PermissionDetailResponse:
    role_repo = RoleRepository(session)
    rbac = RBACService(role_repo)
    roles = await rbac.get_user_role_names(user_id)
    permissions = await rbac.get_user_permissions(user_id)
    return PermissionDetailResponse(
        role_id=uuid.uuid4(),
        role_name=", ".join(roles.value) if roles.value else "",
    )


@router.get(
    "/audit-logs",
    response_model=PaginatedResponse,
    summary="View system-wide audit logs",
)
async def list_audit_logs(
    _admin: Annotated[AuthenticatedUser, Depends(_admin_only)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    repo = AuditRepository(session)
    logs, total = (await repo.list_for_user(None, page, page_size)).value
    items = [AuditLogResponse.model_validate(log) for log in logs]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
