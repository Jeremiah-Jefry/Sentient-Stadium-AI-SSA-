"""Operational and health status enums for entities."""

from __future__ import annotations

import enum


class OperationalStatus(str, enum.Enum):
    """Real-time operational status of any stadium entity."""

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    EMERGENCY = "emergency"
    CLOSED = "closed"
    TEMPORARY_CLOSURE = "temporary_closure"


class EntityHealth(str, enum.Enum):
    """Health assessment of an entity based on sensor data and reports."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AccessibilityLevel(str, enum.Enum):
    """Accessibility rating for routes and entities."""

    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class ZoneType(str, enum.Enum):
    """Hierarchical zone classification."""

    STADIUM = "stadium"
    SECTOR = "sector"
    ZONE = "zone"
    SUB_ZONE = "sub_zone"
    GATE = "gate"
    CHECKPOINT = "checkpoint"
    NODE = "node"
    FLOOR = "floor"
    LEVEL = "level"
    SECTION = "section"
    AREA = "area"
