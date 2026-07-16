"""Initial database schema for IAM module.

Revision ID: 001_initial
Revises: None
Create Date: 2026-07-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum types
    auth_provider_enum = postgresql.ENUM(
        "email_password", "google", "firebase", name="authprovider", create_type=False
    )
    user_status_enum = postgresql.ENUM(
        "active", "inactive", "suspended", "pending_verification", "locked",
        name="userstatus", create_type=False,
    )
    role_scope_enum = postgresql.ENUM(
        "system", "venue", "event", name="rolescope", create_type=False,
    )
    audit_event_enum = postgresql.ENUM(
        "login_success", "login_failure", "logout", "password_change",
        "password_reset_request", "password_reset_complete", "email_verified",
        "account_created", "account_updated", "account_suspended",
        "account_reactivated", "role_assigned", "role_revoked",
        "permission_changed", "session_created", "session_revoked",
        "all_sessions_revoked", "token_refreshed", "unauthorized_access_attempt",
        "rate_limit_triggered", "suspicious_activity", "account_locked",
        "account_unlocked",
        name="auditeventtype", create_type=False,
    )

    auth_provider_enum.create(op.get_bind(), checkfirst=True)
    user_status_enum.create(op.get_bind(), checkfirst=True)
    role_scope_enum.create(op.get_bind(), checkfirst=True)
    audit_event_enum.create(op.get_bind(), checkfirst=True)

    # Users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("firebase_uid", sa.String(128), nullable=False, unique=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("photo_url", sa.Text, nullable=True),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("auth_provider", auth_provider_enum, nullable=False, server_default="email_password"),
        sa.Column("email_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", user_status_enum, nullable=False, server_default="pending_verification"),
        sa.Column("failed_login_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_hash", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True, postgresql_where="deleted_at IS NULL")
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"], unique=True, postgresql_where="deleted_at IS NULL")
    op.create_index("ix_users_status", "users", ["status"])

    # Roles table
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("scope", role_scope_enum, nullable=False, server_default="system"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True, postgresql_where="deleted_at IS NULL")
    op.create_index("ix_roles_scope", "roles", ["scope"])

    # Permissions table
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("resource", sa.String(50), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_permissions_name", "permissions", ["name"], unique=True, postgresql_where="deleted_at IS NULL")
    op.create_index("ix_permissions_resource", "permissions", ["resource"])

    # User-Role junction table
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_index("ix_user_roles_user_role", "user_roles", ["user_id", "role_id"], unique=True)

    # Role-Permission junction table
    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])
    op.create_index("ix_role_permissions_role_permission", "role_permissions", ["role_id", "permission_id"], unique=True)

    # User Sessions table
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("refresh_token_hash", sa.String(256), nullable=False, unique=True),
        sa.Column("fingerprint", sa.String(256), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("device_info", postgresql.JSONB, nullable=True),
        sa.Column("is_revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("revoke_reason", sa.String(50), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_refresh_token_hash", "user_sessions", ["refresh_token_hash"], unique=True)
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    # Audit Logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", audit_event_enum, nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("risk_score", sa.Integer, nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_user_event", "audit_logs", ["user_id", "event_type"])

    # Seed default roles
    op.execute("""
        INSERT INTO roles (id, name, display_name, description, scope, is_default, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'volunteer', 'Volunteer', 'Standard volunteer access', 'system', true, NOW(), NOW()),
            (gen_random_uuid(), 'admin', 'Administrator', 'Full system access', 'system', false, NOW(), NOW()),
            (gen_random_uuid(), 'security_officer', 'Security Officer', 'Security and incident management', 'system', false, NOW(), NOW()),
            (gen_random_uuid(), 'operations_manager', 'Operations Manager', 'Venue operations management', 'system', false, NOW(), NOW())
        ON CONFLICT (name) DO NOTHING;
    """)

    # Seed default permissions
    op.execute("""
        INSERT INTO permissions (id, name, resource, action, description, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'user:read', 'user', 'read', 'View user profiles', NOW(), NOW()),
            (gen_random_uuid(), 'user:write', 'user', 'write', 'Update user profiles', NOW(), NOW()),
            (gen_random_uuid(), 'user:delete', 'user', 'delete', 'Delete user accounts', NOW(), NOW()),
            (gen_random_uuid(), 'role:read', 'role', 'read', 'View roles', NOW(), NOW()),
            (gen_random_uuid(), 'role:assign', 'role', 'assign', 'Assign roles to users', NOW(), NOW()),
            (gen_random_uuid(), 'venue:read', 'venue', 'read', 'View venue information', NOW(), NOW()),
            (gen_random_uuid(), 'venue:write', 'venue', 'write', 'Update venue information', NOW(), NOW()),
            (gen_random_uuid(), 'event:read', 'event', 'read', 'View event information', NOW(), NOW()),
            (gen_random_uuid(), 'event:write', 'event', 'write', 'Update event information', NOW(), NOW()),
            (gen_random_uuid(), 'agent:invoke', 'agent', 'invoke', 'Invoke AI agents', NOW(), NOW()),
            (gen_random_uuid(), 'audit:read', 'audit', 'read', 'View audit logs', NOW(), NOW()),
            (gen_random_uuid(), 'session:read', 'session', 'read', 'View active sessions', NOW(), NOW()),
            (gen_random_uuid(), 'session:revoke', 'session', 'revoke', 'Revoke user sessions', NOW(), NOW())
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("user_sessions")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")

    postgresql.ENUM(name="auditeventtype").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="rolescope").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="userstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="authprovider").drop(op.get_bind(), checkfirst=True)
