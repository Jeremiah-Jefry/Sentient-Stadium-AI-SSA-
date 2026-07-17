"""Model metadata model — registry of all AI/ML models used by the intelligence engine."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ModelMetadata(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Registry entry for every model deployed in the intelligence engine.

    Tracks version, type, accuracy, and parameters so the pipeline can
    select the correct model for each prediction or decision task.
    """

    __tablename__ = "ai_model_metadata"
    __table_args__ = (
        UniqueConstraint("model_name", "model_version", name="uq_ai_model_name_version"),
        Index("ix_ai_model_metadata_model_name", "model_name"),
        Index("ix_ai_model_metadata_is_active", "is_active"),
    )

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    last_trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
