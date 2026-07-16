"""Export all auth domain models for Alembic discovery and imports."""

from app.features.auth.models.audit_log import AuditEventType, AuditLog
from app.features.auth.models.permission import Permission
from app.features.auth.models.role import Role, RoleScope
from app.features.auth.models.role_permission import RolePermission
from app.features.auth.models.session import UserSession
from app.features.auth.models.user import AuthProvider, User, UserStatus
from app.features.auth.models.user_role import UserRole

__all__ = [
    "AuditEventType",
    "AuditLog",
    "AuthProvider",
    "Permission",
    "Role",
    "RolePermission",
    "RoleScope",
    "User",
    "UserRole",
    "UserSession",
    "UserStatus",
]
