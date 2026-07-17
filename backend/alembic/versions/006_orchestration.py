"""Add orchestration engine tables.

Revision ID: 006_orchestration
Revises: 005_navigation
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "006_orchestration"
down_revision = "005_navigation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orch_execution_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("execution_plan_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("strategy", sa.String(30), nullable=True),
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("reasoning", JSONB, nullable=True),
        sa.Column("evidence", JSONB, nullable=True),
        sa.Column("agents_used", JSONB, nullable=True),
        sa.Column("alternatives", JSONB, nullable=True),
        sa.Column("explanation", JSONB, nullable=True),
        sa.Column("total_duration_ms", sa.Float, nullable=True),
        sa.Column("steps_completed", sa.Integer, server_default="0"),
        sa.Column("steps_failed", sa.Integer, server_default="0"),
        sa.Column("metadata", "jsonb", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
    )

    op.create_table(
        "orch_execution_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("strategy", sa.String(30), nullable=False),
        sa.Column("steps", JSONB, nullable=False),
        sa.Column("dependencies", JSONB, nullable=True),
        sa.Column("timeout_seconds", sa.Float, nullable=False),
        sa.Column("fallback_plan_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
    )

    op.create_table(
        "orch_execution_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", UUID(as_uuid=True), sa.ForeignKey("orch_execution_history.id"), nullable=False, index=True),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("orch_execution_plans.id"), nullable=True),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float, nullable=True),
        sa.Column("input_data", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "orch_decision_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", UUID(as_uuid=True), sa.ForeignKey("orch_execution_history.id"), nullable=False, index=True),
        sa.Column("request_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("decision", sa.Text, nullable=False),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("agents_involved", JSONB, nullable=True),
        sa.Column("evidence", JSONB, nullable=True),
        sa.Column("alternatives", JSONB, nullable=True),
        sa.Column("safety_level", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "orch_agent_health",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("health_score", sa.Float, nullable=False),
        sa.Column("current_load", sa.Integer, server_default="0"),
        sa.Column("total_invocations", sa.Integer, server_default="0"),
        sa.Column("error_rate", sa.Float, server_default="0.0"),
        sa.Column("avg_latency_ms", sa.Float, server_default="0.0"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_details", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "orch_tool_calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", UUID(as_uuid=True), sa.ForeignKey("orch_execution_history.id"), nullable=False, index=True),
        sa.Column("tool_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("parameters", JSONB, nullable=True),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("duration_ms", sa.Float, nullable=False),
        sa.Column("cache_hit", sa.Boolean, server_default="false"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "orch_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", UUID(as_uuid=True), sa.ForeignKey("orch_execution_history.id"), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("risk_score", sa.Float, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("orch_audit_logs")
    op.drop_table("orch_tool_calls")
    op.drop_table("orch_agent_health")
    op.drop_table("orch_decision_ledger")
    op.drop_table("orch_execution_steps")
    op.drop_table("orch_execution_plans")
    op.drop_table("orch_execution_history")
