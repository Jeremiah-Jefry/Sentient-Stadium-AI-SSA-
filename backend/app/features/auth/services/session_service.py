"""Session service - manages user sessions, device tracking, and concurrent limits."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.features.auth.models.session import UserSession
from app.features.auth.repositories.session_repository import SessionRepository
from app.shared.result import Result, Success

settings = get_settings()

# Concurrent session limit per user (prevents token sharing)
MAX_CONCURRENT_SESSIONS = 5


class SessionService:
    """Manages the full lifecycle of user sessions.

    Responsibilities:
    - Create sessions on login
    - Validate sessions during token refresh
    - Revoke sessions on logout
    - Enforce concurrent session limits
    - Cleanup expired sessions
    """

    def __init__(self, session_repository: SessionRepository) -> None:
        self._repo = session_repository

    async def create_session(
        self,
        user_id: uuid.UUID,
        refresh_token_hash: str,
        fingerprint: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_info: dict | None = None,
    ) -> Result[UserSession]:
        """Create a new session after successful authentication.

        Enforces concurrent session limits by revoking the oldest
        sessions when the limit is exceeded.
        """
        now = datetime.now(timezone.utc)
        expires_at = now.replace(
            hour=23, minute=59, second=59
        )  # Sessions expire at end of day

        session = UserSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            fingerprint=fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
            expires_at=expires_at,
            last_active_at=now,
        )

        result = await self._repo.create(session)
        if not result:
            return result

        await self._enforce_session_limit(user_id)
        return result

    async def validate_session(self, refresh_token_hash: str) -> Result[UserSession]:
        """Validate that a session exists, is not revoked, and has not expired."""
        result = await self._repo.get_by_refresh_token_hash(refresh_token_hash)
        if not result or not result.value:
            return Result(value=None, error_code="SESSION_NOT_FOUND")

        session = result.value
        now = datetime.now(timezone.utc)

        if session.is_revoked:
            return Result(value=None, error_code="SESSION_REVOKED")

        if session.expires_at < now:
            return Result(value=None, error_code="SESSION_EXPIRED")

        return Success(session)

    async def revoke_session(
        self,
        session_id: uuid.UUID,
        reason: str = "user_logout",
    ) -> Result[None]:
        """Revoke a single session."""
        return await self._repo.revoke(session_id, reason)

    async def revoke_by_token_hash(
        self,
        token_hash: str,
        reason: str = "token_refresh",
    ) -> Result[None]:
        """Revoke a session by its refresh token hash."""
        return await self._repo.revoke_by_token_hash(token_hash, reason)

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        reason: str = "user_logout",
    ) -> Result[int]:
        """Revoke all active sessions for a user (full session invalidation)."""
        return await self._repo.revoke_all_for_user(user_id, reason)

    async def get_active_sessions(self, user_id: uuid.UUID) -> Result[list[UserSession]]:
        """Get all active sessions for a user's device management view."""
        return await self._repo.get_active_sessions_for_user(user_id)

    async def update_last_active(self, session_id: uuid.UUID) -> Result[None]:
        """Update session activity timestamp (called on each authenticated request)."""
        return await self._repo.update_last_active(session_id)

    async def cleanup_expired(self) -> Result[int]:
        """Remove expired sessions from the database."""
        return await self._repo.cleanup_expired()

    async def _enforce_session_limit(self, user_id: uuid.UUID) -> None:
        """Revoke oldest sessions if the concurrent limit is exceeded."""
        sessions_result = await self._repo.get_active_sessions_for_user(user_id)
        if not sessions_result or not sessions_result.value:
            return

        active_sessions = sessions_result.value
        if len(active_sessions) <= MAX_CONCURRENT_SESSIONS:
            return

        # Sort by last_active_at ascending and revoke excess
        sorted_sessions = sorted(active_sessions, key=lambda s: s.last_active_at)
        excess = sorted_sessions[: len(sorted_sessions) - MAX_CONCURRENT_SESSIONS]

        for session in excess:
            await self._repo.revoke(session.id, reason="concurrent_session_limit")
