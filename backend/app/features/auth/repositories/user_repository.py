"""User repository - data access layer for user operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.auth.models.user import User, UserStatus
from app.features.auth.models.user_role import UserRole
from app.shared.result import Failure, Result, Success


class UserRepository:
    """Handles all database operations for the User entity.

    Follows the Repository Pattern to decouple domain logic from
    data access concerns.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> Result[User | None]:
        """Fetch a user by ID, excluding soft-deleted users."""
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id, User.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return Success(user)

    async def get_by_firebase_uid(self, firebase_uid: str) -> Result[User | None]:
        """Fetch a user by their Firebase UID."""
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.firebase_uid == firebase_uid, User.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return Success(user)

    async def get_by_email(self, email: str) -> Result[User | None]:
        """Fetch a user by email address (case-insensitive)."""
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(func.lower(User.email) == email.lower(), User.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        return Success(user)

    async def create(self, user: User) -> Result[User]:
        """Persist a new user to the database."""
        self._session.add(user)
        await self._session.flush()
        return Success(user)

    async def update(self, user: User) -> Result[User]:
        """Update an existing user. Flushes but does not commit."""
        await self._session.flush()
        return Success(user)

    async def update_last_login(self, user_id: uuid.UUID, login_at: datetime) -> Result[None]:
        """Update the last_login_at timestamp for a user."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=login_at)
        )
        await self._session.execute(stmt)
        return Success(None)

    async def increment_failed_attempts(self, user_id: uuid.UUID) -> Result[int]:
        """Atomically increment failed login attempts and return new count."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=User.failed_login_attempts + 1)
            .returning(User.failed_login_attempts)
        )
        result = await self._session.execute(stmt)
        new_count = result.scalar_one()
        return Success(new_count)

    async def reset_failed_attempts(self, user_id: uuid.UUID) -> Result[None]:
        """Reset failed login attempts to zero after successful login."""
        stmt = update(User).where(User.id == user_id).values(failed_login_attempts=0)
        await self._session.execute(stmt)
        return Success(None)

    async def lock_account(self, user_id: uuid.UUID, until: datetime) -> Result[None]:
        """Lock a user account until the specified datetime."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(status=UserStatus.LOCKED, locked_until=until)
        )
        await self._session.execute(stmt)
        return Success(None)

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: UserStatus | None = None,
    ) -> Result[tuple[list[User], int]]:
        """List users with pagination, search, and status filtering."""
        base_query = select(User).where(User.deleted_at.is_(None))

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.where(
                (User.email.ilike(search_pattern))
                | (User.display_name.ilike(search_pattern))
            )
        if status:
            base_query = base_query.where(User.status == status)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        paginated = base_query.options(
            selectinload(User.roles)
        ).order_by(
            User.created_at.desc()
        ).offset(
            (page - 1) * page_size
        ).limit(page_size)

        result = await self._session.execute(paginated)
        users = list(result.scalars().all())
        return Success((users, total))

    async def exists_by_email(self, email: str) -> Result[bool]:
        """Check if a user with the given email already exists."""
        stmt = select(func.count()).where(
            func.lower(User.email) == email.lower(),
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        count = result.scalar_one()
        return Success(count > 0)

    async def exists_by_firebase_uid(self, firebase_uid: str) -> Result[bool]:
        """Check if a user with the given Firebase UID already exists."""
        stmt = select(func.count()).where(
            User.firebase_uid == firebase_uid,
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        count = result.scalar_one()
        return Success(count > 0)
