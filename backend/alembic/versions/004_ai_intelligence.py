"""AI Intelligence Engine — core prediction, risk, and decision schema."""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "004_ai_intelligence"
down_revision: str | None = "003_event_streaming"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Predictions
    op.create_table(
        "ai_predictions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("venue_id", UUID(as_uuid=True), nullable=False),
        sa.Column("zone_id", UUID(as_uuid=True), nullable=True),
        sa.Column("prediction_type", sa.String(100), nullable=False),
        sa.Column("predicted_value", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("confidence_breakdown", JSONB, nullable=True),
        sa.Column("prediction_window_seconds", sa.Integer, nullable=False),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_events", JSONB, nullable=True, server_default="[]"),
        sa.Column("contributing_factors", JSONB, nullable=True, server_default="[]"),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("is_accurate", sa.Boolean, nullable=True),
        sa.Column("actual_value", sa.Float, nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_predictions_venue_id", "ai_predictions", ["venue_id"])
    op.create_index("ix_ai_predictions_zone_id", "ai_predictions", ["zone_id"])
    op.create_index("ix_ai_predictions_prediction_type", "ai_predictions", ["prediction_type"])
    op.create_index("ix_ai_predictions_predicted_at", "ai_predictions", ["predicted_at"])
    op.create_index("ix_ai_predictions_valid_until", "ai_predictions", ["valid_until"])
    op.create_index("ix_ai_predictions_deleted_at", "ai_predictions", ["deleted_at"])
    op.create_index(
        "ix_ai_predictions_venue_zone_type",
        "ai_predictions",
        ["venue_id", "zone_id", "prediction_type"],
    )
    op.create_index("ix_ai_predictions_predicted_at_desc", "ai_predictions", [sa.text("predicted_at DESC")])
    op.create_index(
        "ix_ai_predictions_valid_until_accurate",
        "ai_predictions",
        ["valid_until", "is_accurate"],
    )

    # Risk History
    op.create_table(
        "ai_risk_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("venue_id", UUID(as_uuid=True), nullable=False),
        sa.Column("zone_id", UUID(as_uuid=True), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("risk_factors", JSONB, nullable=True, server_default="{}"),
        sa.Column("contributing_events", JSONB, nullable=True, server_default="[]"),
        sa.Column("venue_risk", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("zone_risk", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("medical_risk", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("security_risk", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("accessibility_risk", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("transport_risk", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("weather_risk", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_risk_history_venue_id", "ai_risk_history", ["venue_id"])
    op.create_index("ix_ai_risk_history_zone_id", "ai_risk_history", ["zone_id"])
    op.create_index("ix_ai_risk_history_risk_level", "ai_risk_history", ["risk_level"])
    op.create_index("ix_ai_risk_history_assessed_at", "ai_risk_history", ["assessed_at"])
    op.create_index(
        "ix_ai_risk_history_venue_assessed_desc",
        "ai_risk_history",
        [sa.text("venue_id, assessed_at DESC")],
    )
    op.create_index(
        "ix_ai_risk_history_level_assessed_desc",
        "ai_risk_history",
        [sa.text("risk_level, assessed_at DESC")],
    )

    # Decisions
    op.create_table(
        "ai_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("venue_id", UUID(as_uuid=True), nullable=False),
        sa.Column("zone_id", UUID(as_uuid=True), nullable=True),
        sa.Column("decision_status", sa.String(30), nullable=False),
        sa.Column("intervention_type", sa.String(100), nullable=False),
        sa.Column("intervention_params", JSONB, nullable=True, server_default="{}"),
        sa.Column("risk_level_at_decision", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("reasoning", JSONB, nullable=True, server_default="{}"),
        sa.Column("alternative_decisions", JSONB, nullable=True, server_default="[]"),
        sa.Column("expected_outcome", JSONB, nullable=True, server_default="{}"),
        sa.Column("actual_outcome", JSONB, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_decisions_venue_id", "ai_decisions", ["venue_id"])
    op.create_index("ix_ai_decisions_decision_status", "ai_decisions", ["decision_status"])
    op.create_index("ix_ai_decisions_intervention_type", "ai_decisions", ["intervention_type"])
    op.create_index("ix_ai_decisions_published_at", "ai_decisions", ["published_at"])
    op.create_index(
        "ix_ai_decisions_venue_status_published_desc",
        "ai_decisions",
        [sa.text("venue_id, decision_status, published_at DESC")],
    )

    # Interventions
    op.create_table(
        "ai_interventions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("decision_id", UUID(as_uuid=True), sa.ForeignKey("ai_decisions.id"), nullable=False),
        sa.Column("venue_id", UUID(as_uuid=True), nullable=False),
        sa.Column("intervention_type", sa.String(100), nullable=False),
        sa.Column("strategy_params", JSONB, nullable=True, server_default="{}"),
        sa.Column("simulated_risk_reduction", sa.Float, nullable=False),
        sa.Column("simulated_confidence", sa.Float, nullable=False),
        sa.Column("actual_risk_reduction", sa.Float, nullable=True),
        sa.Column("actual_confidence", sa.Float, nullable=True),
        sa.Column("execution_latency_ms", sa.Float, nullable=True),
        sa.Column("is_effective", sa.Boolean, nullable=True),
        sa.Column("feedback_score", sa.Float, nullable=True),
        sa.Column("feedback_notes", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_interventions_decision_id", "ai_interventions", ["decision_id"])

    # Model Metadata
    op.create_table(
        "ai_model_metadata",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("parameters", JSONB, nullable=True, server_default="{}"),
        sa.Column("accuracy_score", sa.Float, nullable=True),
        sa.Column("last_trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_ai_model_metadata_name_version",
        "ai_model_metadata",
        ["model_name", "model_version"],
    )

    # Confidence Records
    op.create_table(
        "ai_confidence_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("prediction_id", UUID(as_uuid=True), sa.ForeignKey("ai_predictions.id"), nullable=False),
        sa.Column("overall_confidence", sa.Float, nullable=False),
        sa.Column("sensor_agreement", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("historical_similarity", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("model_agreement", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("data_freshness_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("evidence_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reasoning", JSONB, nullable=True, server_default="{}"),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_confidence_records_prediction_id", "ai_confidence_records", ["prediction_id"])

    # Historical Outcomes
    op.create_table(
        "ai_historical_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("venue_id", UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", UUID(as_uuid=True), sa.ForeignKey("ai_decisions.id"), nullable=True),
        sa.Column("outcome_type", sa.String(50), nullable=False),
        sa.Column("risk_level_before", sa.String(20), nullable=False),
        sa.Column("risk_level_after", sa.String(20), nullable=True),
        sa.Column("risk_score_change", sa.Float, nullable=True),
        sa.Column("intervention_effective", sa.Boolean, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("affected_zone_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lessons_learned", sa.Text, nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_historical_outcomes_venue_id", "ai_historical_outcomes", ["venue_id"])
    op.create_index("ix_ai_historical_outcomes_outcome_type", "ai_historical_outcomes", ["outcome_type"])
    op.create_index("ix_ai_historical_outcomes_recorded_at", "ai_historical_outcomes", ["recorded_at"])


def downgrade() -> None:
    op.drop_table("ai_historical_outcomes")
    op.drop_table("ai_confidence_records")
    op.drop_table("ai_model_metadata")
    op.drop_table("ai_interventions")
    op.drop_table("ai_decisions")
    op.drop_table("ai_risk_history")
    op.drop_table("ai_predictions")
