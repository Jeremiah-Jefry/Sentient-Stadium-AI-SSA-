"""RBAC service - role-based access control and permission resolution."""

from __future__ import annotations

import uuid

from app.features.auth.models.user import User
from app.features.auth.repositories.role_repository import RoleRepository
from app.shared.exceptions import AuthorizationError
from app.shared.result import Result, Success


class RBACService:
    """Resolves user permissions from their assigned roles.

    Responsibilities:
    - Collect all permissions from a user's roles
    - Check if a user has a specific permission
    - Check if a user has any of a set of permissions
    - Assign and revoke roles
    """

    def __init__(self, role_repository: RoleRepository) -> None:
        self._role_repo = role_repository

    async def get_user_permissions(self, user_id: uuid.UUID) -> Result[list[str]]:
        """Collect all unique permission names from a user's roles."""
        roles_result = await self._role_repo.get_user_roles(user_id)
        if isinstance(roles_result, type(None)):
            return Success([])

        permission_names: set[str] = set()
        for user_role in roles_result:
            perms_result = await self._role_repo.get_role_permissions(user_role.role_id)
            if perms_result:
                for perm in perms_result:
                    permission_names.add(perm.name)

        return Success(sorted(permission_names))

    async def get_user_role_names(self, user_id: uuid.UUID) -> Result[list[str]]:
        """Collect all unique role names for a user."""
        roles_result = await self._role_repo.get_user_roles(user_id)
        if not roles_result:
            return Success([])

        role_names = {ur.role.name for ur in roles_result if ur.role}
        return Success(sorted(role_names))

    async def has_permission(self, user_id: uuid.UUID, permission: str) -> Result[bool]:
        """Check if a user has a specific permission via any role."""
        return await self._role_repo.user_has_permission(user_id, permission)

    async def require_permission(self, user_id: uuid.UUID, permission: str) -> Result[None]:
        """Require a user to have a specific permission.

        Returns Success(None) if the user has the permission.
        Returns Failure if the user lacks the permission.
        """
        result = await self._role_repo.user_has_permission(user_id, permission)
        if isinstance(result, Success) and result.value:
            return Success(None)

        return Failure(
            error_code="AUTHORIZATION_FAILED",
            message=f"Missing required permission: {permission}",
            details={"required_permission": permission, "user_id": str(user_id)},
        )

    async def enforce_permission(self, user_id: uuid.UUID, permission: str) -> None:
        """Enforce a permission check, raising AuthorizationError if denied.

        Unlike require_permission, this raises instead of returning Result
        for use in middleware and dependency injection.
        """
        result = await self.require_permission(user_id, permission)
        if isinstance(result, Failure):
            raise AuthorizationError(
                message=result.message,
                details=result.details,
            )

    async def has_any_permission(
        self, user_id: uuid.UUID, permissions: list[str]
    ) -> Result[bool]:
        """Check if a user has at least one of the given permissions."""
        for perm in permissions:
            result = await self.has_permission(user_id, perm)
            if isinstance(result, Success) and result.value:
                return Success(True)
        return Success(False)

    async def assign_role(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID | None = None,
        venue_id: uuid.UUID | None = None,
        event_id: uuid.UUID | None = None,
    ) -> Result[None]:
        """Assign a role to a user with optional scope and expiration."""
        from app.features.auth.models.user_role import UserRole

        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
            venue_id=venue_id,
            event_id=event_id,
        )
        await self._role_repo.assign_role_to_user(user_role)
        return Success(None)

    async def revoke_role(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        venue_id: uuid.UUID | None = None,
        event_id: uuid.UUID | None = None,
    ) -> Result[int]:
        """Revoke a role from a user."""
        return await self._role_repo.revoke_role_from_user(
            user_id, role_id, venue_id, event_id
        )
