"""Sensor registry model — tracks all deployed sensors and their metadata."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.features.event_streaming.models.event_type import SensorType
from app.shared.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SensorRegistry(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Registry of all physical sensors deployed across stadiums.

    Each sensor is registered once and emits readings that flow through
    the event streaming pipeline. Tracks location, type, health, and
    calibration metadata.
    """

    __tablename__ = "es_sensors"
    __table_args__ = (
        Index("ix_es_sensors_venue_id", "venue_id"),
        Index("ix_es_sensors_entity_id", "entity_id"),
        Index("ix_es_sensors_zone_id", "zone_id"),
        Index("ix_es_sensors_sensor_type", "sensor_type"),
        Index("ix_es_sensors_is_active", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensor_type: Mapped[SensorType] = mapped_column(String(50), nullable=False)

    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    coordinates_lat: Mapped[float] = mapped_column(Float, nullable=False)
    coordinates_lon: Mapped[float] = mapped_column(Float, nullable=False)
    indoor_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    indoor_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    floor_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_calibrated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_calibration_at: Mapped[str | None] = mapped_column(String(30), nullable=True)

    reading_interval_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    range_meters: Mapped[float | None] = mapped_column(Float, nullable=True)

    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
