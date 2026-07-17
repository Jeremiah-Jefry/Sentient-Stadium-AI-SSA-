"""Alembic migration: Navigation module tables.

Revision ID: 005
Revises: 004
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005_navigation"
down_revision = "004_ai_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nav_route_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("origin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile", sa.String(50), nullable=False),
        sa.Column("route_type", sa.String(50), nullable=False),
        sa.Column("route_data", postgresql.JSONB, nullable=False),
        sa.Column("quality_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("hit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("graph_version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_at", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_nav_route_cache_origin_dest", "nav_route_cache", ["origin_id", "destination_id"])
    op.create_index("ix_nav_route_cache_venue_id", "nav_route_cache", ["venue_id"])
    op.create_index("ix_nav_route_cache_expires_at", "nav_route_cache", ["expires_at"])

    op.create_table(
        "nav_route_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("origin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile", sa.String(50), nullable=False),
        sa.Column("route_type", sa.String(50), nullable=False),
        sa.Column("route_data", postgresql.JSONB, nullable=False),
        sa.Column("total_distance_meters", sa.Float, nullable=False),
        sa.Column("total_time_seconds", sa.Float, nullable=False),
        sa.Column("quality_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("grade", sa.String(5), nullable=False, server_default="C"),
        sa.Column("algorithm_used", sa.String(50), nullable=False, server_default=""),
        sa.Column("computation_ms", sa.Float, nullable=False, server_default="0"),
        sa.Column("was_replanned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_nav_route_history_user_id", "nav_route_history", ["user_id"])
    op.create_index("ix_nav_route_history_venue_id", "nav_route_history", ["venue_id"])
    op.create_index("ix_nav_route_history_created_at", "nav_route_history", ["created_at"])
    op.create_index("ix_nav_route_history_profile", "nav_route_history", ["profile"])

    op.create_table(
        "nav_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nav_route_history.id", ondelete="SET NULL"), nullable=True),
        sa.Column("origin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("profile", sa.String(50), nullable=False),
        sa.Column("progress_percent", sa.Float, nullable=False, server_default="0"),
        sa.Column("replan_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_nav_sessions_user_id", "nav_sessions", ["user_id"])
    op.create_index("ix_nav_sessions_venue_id", "nav_sessions", ["venue_id"])
    op.create_index("ix_nav_sessions_status", "nav_sessions", ["status"])

    op.create_table(
        "nav_route_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nav_route_history.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("deviated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("actual_duration_seconds", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_nav_route_feedback_route_id", "nav_route_feedback", ["route_id"])
    op.create_index("ix_nav_route_feedback_user_id", "nav_route_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_table("nav_route_feedback")
    op.drop_table("nav_sessions")
    op.drop_table("nav_route_history")
    op.drop_table("nav_route_cache")
