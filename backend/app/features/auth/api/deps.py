"""FastAPI dependency injection for the IAM module.

Provides service instances, authenticated user context,
and permission enforcement dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.features.auth.repositories.audit_repository import AuditRepository
from app.features.auth.repositories.role_repository import RoleRepository
from app.features.auth.repositories.session_repository import SessionRepository
from app.features.auth.repositories.user_repository import UserRepository
from app.features.auth.services.audit_service import AuditService
from app.features.auth.services.firebase_service import FirebaseService
from app.features.auth.services.rbac_service import RBACService
from app.features.auth.services.session_service import SessionService
from app.features.auth.services.token_service import TokenService
from app.features.auth.services.auth_service import AuthService
from app.shared.database import get_db_session

settings = get_settings()


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Verified user context extracted from a validated JWT."""

    user_id: uuid.UUID
    email: str
    roles: list[str]
    permissions: list[str]


def get_token_service() -> TokenService:
    return TokenService()


def get_firebase_service() -> FirebaseService:
    return FirebaseService()


def get_user_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> UserRepository:
    return UserRepository(session)


def get_role_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> RoleRepository:
    return RoleRepository(session)


def get_session_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> SessionRepository:
    return SessionRepository(session)


def get_audit_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> AuditRepository:
    return AuditRepository(session)


def get_audit_service(
    repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> AuditService:
    return AuditService(repo)


def get_session_service(
    repo: Annotated[SessionRepository, Depends(get_session_repository)],
) -> SessionService:
    return SessionService(repo)


def get_rbac_service(
    repo: Annotated[RoleRepository, Depends(get_role_repository)],
) -> RBACService:
    return RBACService(repo)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    token_svc: Annotated[TokenService, Depends(get_token_service)],
    firebase_svc: Annotated[FirebaseService, Depends(get_firebase_service)],
    session_svc: Annotated[SessionService, Depends(get_session_service)],
    rbac_svc: Annotated[RBACService, Depends(get_rbac_service)],
    audit_svc: Annotated[AuditService, Depends(get_audit_service)],
) -> AuthService:
    return AuthService(
        user_repository=user_repo,
        token_service=token_svc,
        firebase_service=firebase_svc,
        session_service=session_svc,
        rbac_service=rbac_svc,
        audit_service=audit_svc,
    )


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    token_service: Annotated[TokenService, Depends(get_token_service)] = None,
) -> AuthenticatedUser:
    """Extract and verify the current user from the Authorization header.

    This dependency protects all authenticated endpoints.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer " prefix
    svc = TokenService()
    result = svc.verify_access_token(token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = result.value
    try:
        return AuthenticatedUser(
            user_id=uuid.UUID(payload["sub"]),
            email=payload.get("email", ""),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
        )
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(permission: str):
    """Factory that creates a dependency requiring a specific permission."""
    async def _check(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return user
    return _check


def require_role(role: str):
    """Factory that creates a dependency requiring a specific role."""
    async def _check(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {role}",
            )
        return user
    return _check
