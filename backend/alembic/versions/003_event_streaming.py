"""Event Streaming & Sensor Fusion Platform — core database schema."""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "003_event_streaming"
down_revision: str | None = "002_digital_twin"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Events table — the append-only event store
    op.create_table(
        "es_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("event_id", sa.String(64), nullable=False, unique=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("parent_event_id", sa.String(64), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("producer", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("venue_id", UUID(as_uuid=True), nullable=True),
        sa.Column("zone_id", UUID(as_uuid=True), nullable=True),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("metadata_json", JSONB, nullable=True, server_default="{}"),
        sa.Column("captured_at", sa.String(30), nullable=False),
        sa.Column("processing_status", sa.String(30), nullable=False, server_default="received"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("ttl_seconds", sa.Integer, nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("processing_duration_ms", sa.Float, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    # Note: event_id has unique=True which creates an implicit index — no separate index needed
    op.create_index("ix_es_events_producer", "es_events", ["producer"])
    op.create_index("ix_es_events_category", "es_events", ["category"])
    op.create_index("ix_es_events_event_type", "es_events", ["event_type"])
    op.create_index("ix_es_events_priority", "es_events", ["priority"])
    op.create_index("ix_es_events_severity", "es_events", ["severity"])
    op.create_index("ix_es_events_status", "es_events", ["processing_status"])
    op.create_index("ix_es_events_entity_id", "es_events", ["entity_id"])
    op.create_index("ix_es_events_venue_id", "es_events", ["venue_id"])
    op.create_index("ix_es_events_correlation_id", "es_events", ["correlation_id"])
    op.create_index("ix_es_events_captured_at", "es_events", ["captured_at"])
    op.create_index("ix_es_events_category_venue", "es_events", ["category", "venue_id"])
    op.create_index("ix_es_events_entity_captured", "es_events", ["entity_id", "captured_at"])

    # Sensor registry
    op.create_table(
        "es_sensors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sensor_type", sa.String(50), nullable=False),
        sa.Column("venue_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("zone_id", UUID(as_uuid=True), nullable=True),
        sa.Column("coordinates_lat", sa.Float, nullable=False),
        sa.Column("coordinates_lon", sa.Float, nullable=False),
        sa.Column("indoor_x", sa.Float, nullable=True),
        sa.Column("indoor_y", sa.Float, nullable=True),
        sa.Column("floor_number", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_calibrated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_calibration_at", sa.String(30), nullable=True),
        sa.Column("reading_interval_ms", sa.Integer, nullable=False, server_default="1000"),
        sa.Column("accuracy", sa.Float, nullable=True),
        sa.Column("range_meters", sa.Float, nullable=True),
        sa.Column("firmware_version", sa.String(50), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True, server_default="{}"),
    )
    op.create_index("ix_es_sensors_venue_id", "es_sensors", ["venue_id"])
    op.create_index("ix_es_sensors_entity_id", "es_sensors", ["entity_id"])
    op.create_index("ix_es_sensors_zone_id", "es_sensors", ["zone_id"])
    op.create_index("ix_es_sensors_sensor_type", "es_sensors", ["sensor_type"])
    op.create_index("ix_es_sensors_is_active", "es_sensors", ["is_active"])

    # Dead letter queue
    op.create_table(
        "es_dead_letter_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("original_event_id", sa.String(64), nullable=False),
        sa.Column("original_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("error_type", sa.String(100), nullable=False),
        sa.Column("error_message", sa.Text, nullable=False),
        sa.Column("stack_trace", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_retry_at", sa.String(30), nullable=True),
        sa.Column("processing_duration_ms", sa.Float, nullable=True),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.String(30), nullable=True),
        sa.Column("resolved_by", sa.String(100), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
    )
    op.create_index("ix_es_dlq_original_event_id", "es_dead_letter_events", ["original_event_id"])
    op.create_index("ix_es_dlq_error_type", "es_dead_letter_events", ["error_type"])
    op.create_index("ix_es_dlq_is_resolved", "es_dead_letter_events", ["is_resolved", "created_at"])

    # Consumer offsets
    op.create_table(
        "es_consumer_offsets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("consumer_id", sa.String(200), nullable=False, unique=True),
        sa.Column("last_processed_event_id", sa.String(64), nullable=True),
        sa.Column("last_processed_at", sa.String(30), nullable=True),
        sa.Column("events_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("events_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_processing_ms", sa.Float, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="healthy"),
        sa.Column("is_replaying", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("metadata_json", JSONB, nullable=True, server_default="{}"),
    )
    # Note: consumer_id has unique=True — no separate index needed
    op.create_index("ix_es_consumer_offsets_status", "es_consumer_offsets", ["status"])

    # Snapshots
    op.create_table(
        "es_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("venue_id", UUID(as_uuid=True), nullable=False),
        sa.Column("captured_at", sa.String(30), nullable=False),
        sa.Column("interval_type", sa.String(30), nullable=False, server_default="60s"),
        sa.Column("total_events", sa.Integer, nullable=False, server_default="0"),
        sa.Column("events_by_category", JSONB, nullable=False, server_default="{}"),
        sa.Column("events_by_severity", JSONB, nullable=False, server_default="{}"),
        sa.Column("avg_response_time_ms", sa.Float, nullable=True),
        sa.Column("max_response_time_ms", sa.Float, nullable=True),
        sa.Column("fusion_confidence_avg", sa.Float, nullable=True),
        sa.Column("active_sensors", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_sensors", sa.Integer, nullable=False, server_default="0"),
        sa.Column("state_summary", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_es_snapshots_venue_id", "es_snapshots", ["venue_id"])
    op.create_index("ix_es_snapshots_venue_captured", "es_snapshots", ["venue_id", "captured_at"])
    op.create_index("ix_es_snapshots_interval_type", "es_snapshots", ["interval_type"])

    # Aggregations
    op.create_table(
        "es_aggregations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("venue_id", UUID(as_uuid=True), nullable=False),
        sa.Column("zone_id", UUID(as_uuid=True), nullable=True),
        sa.Column("window_type", sa.String(10), nullable=False),
        sa.Column("window_start", sa.String(30), nullable=False),
        sa.Column("window_end", sa.String(30), nullable=False),
        sa.Column("event_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("events_by_category", JSONB, nullable=False, server_default="{}"),
        sa.Column("events_by_severity", JSONB, nullable=False, server_default="{}"),
        sa.Column("peak_crowd_density", sa.Float, nullable=True),
        sa.Column("avg_crowd_density", sa.Float, nullable=True),
        sa.Column("avg_response_time_ms", sa.Float, nullable=True),
        sa.Column("max_response_time_ms", sa.Float, nullable=True),
        sa.Column("anomalies_detected", sa.Integer, nullable=False, server_default="0"),
        sa.Column("alerts_triggered", sa.Integer, nullable=False, server_default="0"),
        sa.Column("summary", JSONB, nullable=True, server_default="{}"),
    )
    op.create_index("ix_es_agg_venue_id", "es_aggregations", ["venue_id"])
    op.create_index("ix_es_agg_zone_id", "es_aggregations", ["zone_id"])
    op.create_index("ix_es_agg_window", "es_aggregations", ["window_type"])
    op.create_index("ix_es_agg_venue_window_time", "es_aggregations", ["venue_id", "window_type", "window_start"])


def downgrade() -> None:
    op.drop_table("es_aggregations")
    op.drop_table("es_snapshots")
    op.drop_table("es_consumer_offsets")
    op.drop_table("es_dead_letter_events")
    op.drop_table("es_sensors")
    op.drop_table("es_events")
