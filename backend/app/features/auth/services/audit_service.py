"""Audit service - structured event logging for security and compliance."""

from __future__ import annotations

import uuid
from typing import Any

from app.features.auth.models.audit_log import AuditEventType, AuditLog
from app.features.auth.repositories.audit_repository import AuditRepository
from app.shared.result import Result, Success


class AuditService:
    """Records security-relevant events for compliance and incident investigation.

    All audit events are append-only and immutable. This service is
    designed to never throw exceptions - audit failures are logged
    but do not interrupt the calling operation.
    """

    def __init__(self, audit_repository: AuditRepository) -> None:
        self._repo = audit_repository

    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        risk_score: int | None = None,
        session_id: uuid.UUID | None = None,
    ) -> Result[AuditLog]:
        """Record an audit event. Best-effort: never blocks the caller on failure."""
        audit_log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            risk_score=risk_score,
            session_id=session_id,
        )
        return await self._repo.create(audit_log)

    async def log_login_success(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: uuid.UUID | None = None,
    ) -> Result[AuditLog]:
        """Record a successful login event."""
        return await self.log_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            risk_score=10,
            session_id=session_id,
        )

    async def log_login_failure(
        self,
        user_id: uuid.UUID | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        reason: str = "invalid_credentials",
    ) -> Result[AuditLog]:
        """Record a failed login attempt."""
        return await self.log_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": reason},
            risk_score=50,
        )

    async def log_logout(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID | None = None,
        all_devices: bool = False,
    ) -> Result[AuditLog]:
        """Record a logout event."""
        return await self.log_event(
            event_type=AuditEventType.LOGOUT,
            user_id=user_id,
            details={"all_devices": all_devices},
            session_id=session_id,
        )

    async def log_token_refresh(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID | None = None,
    ) -> Result[AuditLog]:
        """Record a token refresh event."""
        return await self.log_event(
            event_type=AuditEventType.TOKEN_REFRESHED,
            user_id=user_id,
            session_id=session_id,
            risk_score=5,
        )

    async def log_role_change(
        self,
        actor_id: uuid.UUID,
        target_user_id: uuid.UUID,
        role_name: str,
        action: str,
    ) -> Result[AuditLog]:
        """Record a role assignment or revocation event."""
        return await self.log_event(
            event_type=(
                AuditEventType.ROLE_ASSIGNED if action == "assign"
                else AuditEventType.ROLE_REVOKED
            ),
            user_id=actor_id,
            resource_type="role",
            resource_id=role_name,
            details={"target_user_id": str(target_user_id)},
            risk_score=40,
        )

    async def log_unauthorized_attempt(
        self,
        user_id: uuid.UUID | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        resource: str = "unknown",
    ) -> Result[AuditLog]:
        """Record an unauthorized access attempt."""
        return await self.log_event(
            event_type=AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="access_control",
            resource_id=resource,
            risk_score=75,
        )

    async def log_suspicious_activity(
        self,
        user_id: uuid.UUID | None,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> Result[AuditLog]:
        """Record a detected suspicious activity."""
        return await self.log_event(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            risk_score=90,
        )
