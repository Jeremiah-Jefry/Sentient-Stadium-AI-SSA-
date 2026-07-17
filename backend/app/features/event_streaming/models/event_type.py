"""Domain enums for the Event Streaming Platform."""

from __future__ import annotations

import enum


class EventCategory(str, enum.Enum):
    """Top-level classification of stadium events."""

    CROWD = "crowd"
    SECURITY = "security"
    MEDICAL = "medical"
    TRANSPORT = "transport"
    WEATHER = "weather"
    INFRASTRUCTURE = "infrastructure"
    OPERATIONS = "operations"
    EMERGENCY = "emergency"
    SENSOR = "sensor"
    SYSTEM = "system"


class SensorType(str, enum.Enum):
    """Physical sensor types deployed across the venue."""

    DENSITY_CAMERA = "density_camera"
    THERMAL_CAMERA = "thermal_camera"
    LIDAR = "lidar"
    BLUETOOTH_BEACON = "bluetooth_beacon"
    WIFI_ACCESS_POINT = "wifi_access_point"
    PRESSURE_MAT = "pressure_mat"
    GATE_COUNTER = "gate_counter"
    AIR_QUALITY = "air_quality"
    NOISE_LEVEL = "noise_level"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"
    RAIN_GAUGE = "rain_gauge"
    VIBRATION = "vibration"
    SMOKE_DETECTOR = "smoke_detector"
    GAS_DETECTOR = "gas_detector"
    RADAR = "radar"


class EventPriority(str, enum.Enum):
    """Processing priority controlling queue ordering and resource allocation."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EventSeverity(str, enum.Enum):
    """Impact severity of an event for escalation and alerting."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ProcessingStatus(str, enum.Enum):
    """Lifecycle state of an event through the processing pipeline."""

    RECEIVED = "received"
    VALIDATING = "validating"
    DEDUPLICATING = "deduplicating"
    NORMALIZING = "normalizing"
    ENRICHING = "enriching"
    FUSING = "fusing"
    PROCESSED = "processed"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class ConsumerStatus(str, enum.Enum):
    """Health state of a downstream event consumer."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    FAILED = "failed"
