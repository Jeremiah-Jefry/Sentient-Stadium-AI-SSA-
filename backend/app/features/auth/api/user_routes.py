"""User profile API routes - profile management and session tracking."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.features.auth.api.deps import AuthenticatedUser, get_current_user
from app.features.auth.dto.user_responses import (
    AuditLogResponse,
    PaginatedResponse,
    SessionResponse,
    UserProfileResponse,
)
from app.features.auth.repositories.audit_repository import AuditRepository
from app.features.auth.repositories.session_repository import SessionRepository
from app.features.auth.repositories.user_repository import UserRepository
from app.shared.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get the authenticated user's profile",
)
async def get_my_profile(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserProfileResponse:
    repo = UserRepository(session)
    result = await repo.get_by_id(user.user_id)
    profile = result.value
    return UserProfileResponse.model_validate(profile)


@router.put(
    "/me",
    response_model=UserProfileResponse,
    summary="Update the authenticated user's profile",
)
async def update_my_profile(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserProfileResponse:
    repo = UserRepository(session)
    result = await repo.get_by_id(user.user_id)
    profile = result.value
    await repo.update(profile)
    return UserProfileResponse.model_validate(profile)


@router.get(
    "/me/sessions",
    response_model=list[SessionResponse],
    summary="List active sessions for the authenticated user",
)
async def get_my_sessions(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[SessionResponse]:
    repo = SessionRepository(session)
    result = await repo.get_active_sessions_for_user(user.user_id)
    sessions = result.value if result.value else []
    return [SessionResponse.model_validate(s) for s in sessions]


@router.delete(
    "/me/sessions/{session_id}",
    status_code=204,
    summary="Revoke a specific session",
)
async def revoke_my_session(
    session_id: uuid.UUID,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    repo = SessionRepository(db_session)
    await repo.revoke(session_id, reason="user_logout")


@router.get(
    "/me/audit-log",
    response_model=PaginatedResponse,
    summary="Get audit log for the authenticated user",
)
async def get_my_audit_log(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    repo = AuditRepository(session)
    logs, total = (await repo.list_for_user(user.user_id, page, page_size)).value
    items = [AuditLogResponse.model_validate(log) for log in logs]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
