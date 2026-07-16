"""Role repository - data access layer for RBAC role operations."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.auth.models.permission import Permission
from app.features.auth.models.role import Role
from app.features.auth.models.role_permission import RolePermission
from app.features.auth.models.user_role import UserRole
from app.shared.result import Failure, Result, Success


class RoleRepository:
    """Handles all database operations for Role and Permission entities.

    Manages role-permission assignments and user-role assignments.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, role_id: uuid.UUID) -> Result[Role | None]:
        """Fetch a role by ID with its permissions, excluding soft-deleted."""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id, Role.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_by_name(self, name: str) -> Result[Role | None]:
        """Fetch a role by its unique name."""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == name, Role.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def list_all(self) -> Result[list[Role]]:
        """List all active roles with their permissions."""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.deleted_at.is_(None))
            .order_by(Role.name)
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_permission_by_name(self, name: str) -> Result[Permission | None]:
        """Fetch a permission by its unique name (resource:action format)."""
        stmt = select(Permission).where(
            Permission.name == name,
            Permission.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def get_user_roles(self, user_id: uuid.UUID) -> Result[list[UserRole]]:
        """Fetch all role assignments for a user."""
        stmt = (
            select(UserRole)
            .options(selectinload(UserRole.role))
            .where(UserRole.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_role_permissions(self, role_id: uuid.UUID) -> Result[list[Permission]]:
        """Fetch all permissions assigned to a role."""
        stmt = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(
                RolePermission.role_id == role_id,
                Permission.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def assign_role_to_user(self, user_role: UserRole) -> Result[UserRole]:
        """Assign a role to a user."""
        self._session.add(user_role)
        await self._session.flush()
        return Success(user_role)

    async def revoke_role_from_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        venue_id: uuid.UUID | None = None,
        event_id: uuid.UUID | None = None,
    ) -> Result[int]:
        """Remove a role assignment. Returns the number of rows affected."""
        from sqlalchemy import delete

        stmt = delete(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
        if venue_id:
            stmt = stmt.where(UserRole.venue_id == venue_id)
        if event_id:
            stmt = stmt.where(UserRole.event_id == event_id)

        result = await self._session.execute(stmt)
        return Success(result.rowcount)

    async def user_has_permission(
        self,
        user_id: uuid.UUID,
        permission_name: str,
    ) -> Result[bool]:
        """Check if a user has a specific permission via any of their roles."""
        stmt = (
            select(func.count())
            .select_from(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(
                UserRole.user_id == user_id,
                Permission.name == permission_name,
                Permission.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        count = result.scalar_one()
        return Success(count > 0)

    async def get_default_role(self) -> Result[Role | None]:
        """Fetch the default role assigned to new users."""
        stmt = (
            select(Role)
            .where(Role.is_default.is_(True), Role.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())
