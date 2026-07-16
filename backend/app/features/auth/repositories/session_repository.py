"""Session repository - data access layer for session tracking and invalidation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.session import UserSession
from app.shared.result import Result, Success


class SessionRepository:
    """Handles all database operations for user sessions.

    Sessions track refresh tokens for device management, session
    invalidation, and concurrent session limits.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_session: UserSession) -> Result[UserSession]:
        """Persist a new session."""
        self._session.add(user_session)
        await self._session.flush()
        return Success(user_session)

    async def get_by_refresh_token_hash(self, token_hash: str) -> Result[UserSession | None]:
        """Fetch an active session by its refresh token hash."""
        stmt = select(UserSession).where(
            UserSession.refresh_token_hash == token_hash,
            UserSession.is_revoked.is_(False),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_by_id(self, session_id: uuid.UUID) -> Result[UserSession | None]:
        """Fetch a session by its ID."""
        stmt = select(UserSession).where(UserSession.id == session_id)
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def revoke(self, session_id: uuid.UUID, reason: str = "user_logout") -> Result[None]:
        """Revoke a specific session."""
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(is_revoked=True, revoke_reason=reason)
        )
        await self._session.execute(stmt)
        return Success(None)

    async def revoke_by_token_hash(self, token_hash: str, reason: str = "user_logout") -> Result[None]:
        """Revoke a session identified by its token hash."""
        stmt = (
            update(UserSession)
            .where(UserSession.refresh_token_hash == token_hash)
            .values(is_revoked=True, revoke_reason=reason)
        )
        await self._session.execute(stmt)
        return Success(None)

    async def revoke_all_for_user(self, user_id: uuid.UUID, reason: str = "user_logout") -> Result[int]:
        """Revoke all active sessions for a user. Returns count of revoked sessions."""
        stmt = (
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoke_reason=reason)
        )
        result = await self._session.execute(stmt)
        return Success(result.rowcount)

    async def get_active_sessions_for_user(self, user_id: uuid.UUID) -> Result[list[UserSession]]:
        """Fetch all active (non-revoked, non-expired) sessions for a user."""
        stmt = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.is_revoked.is_(False),
                UserSession.expires_at > datetime.now(timezone.utc),
            )
            .order_by(UserSession.last_active_at.desc())
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def update_last_active(self, session_id: uuid.UUID) -> Result[None]:
        """Update the last_active_at timestamp for a session."""
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(last_active_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)
        return Success(None)

    async def increment_failures(self, session_id: uuid.UUID) -> Result[int]:
        """Increment consecutive failure count for brute-force detection."""
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(
                consecutive_failures=UserSession.consecutive_failures + 1,
            )
            .returning(UserSession.consecutive_failures)
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one())

    async def cleanup_expired(self) -> Result[int]:
        """Remove expired sessions. Returns count of deleted rows."""
        from sqlalchemy import delete

        stmt = delete(UserSession).where(
            UserSession.expires_at < datetime.now(timezone.utc),
        )
        result = await self._session.execute(stmt)
        return Success(result.rowcount)

    async def count_active_for_user(self, user_id: uuid.UUID) -> Result[int]:
        """Count active sessions for a user."""
        stmt = select(func.count()).where(
            UserSession.user_id == user_id,
            UserSession.is_revoked.is_(False),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one())
