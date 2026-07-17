from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.features.orchestration.models.enums import SafetyLevel


@dataclass(frozen=True, slots=True)
class SafetyReport:
    safety_level: SafetyLevel
    is_safe: bool
    violations: list[dict[str, Any]]
    warnings: list[str]
    checked_at: datetime
    overall_risk_score: float


SAFETY_RULES: list[dict[str, Any]] = [
    {"id": "SR-001", "rule": "No recommendation should override emergency procedures", "severity": "critical", "description": "Emergency procedures are absolute and cannot be overridden."},
    {"id": "SR-002", "rule": "No recommendation should compromise accessibility", "severity": "critical", "description": "Accessibility features must never be blocked, disabled, or deprioritized."},
    {"id": "SR-003", "rule": "Medical advice must defer to trained personnel", "severity": "critical", "description": "The system must never provide direct medical diagnoses or treatments."},
    {"id": "SR-004", "rule": "Never expose system internals", "severity": "high", "description": "Internal system architecture must not be revealed."},
    {"id": "SR-005", "rule": "Never reveal other users data", "severity": "critical", "description": "One user's data must never be exposed to another user."},
    {"id": "SR-006", "rule": "Never disable safety features", "severity": "critical", "description": "Safety mechanisms must never be disabled or weakened."},
    {"id": "SR-007", "rule": "Evacuation always takes priority", "severity": "critical", "description": "No recommendation can delay, block, or deprioritize an active evacuation."},
    {"id": "SR-008", "rule": "Wheelchair access must never be blocked", "severity": "critical", "description": "Wheelchair-accessible pathways and seating must remain accessible at all times."},
    {"id": "SR-009", "rule": "Emergency exits must never be blocked", "severity": "critical", "description": "Emergency exits and their clearance zones must never be obstructed."},
]

_MEDICAL_KEYWORDS = [
    "diagnose", "diagnosis", "prescribe", "prescription", "medication",
    "treatment plan", "dose", "dosage", "surgery",
]

_ACCESSIBILITY_BLOCKERS = [
    "block wheelchair", "remove ramp", "disable elevator", "close accessible",
    "shut down caption", "remove audio description",
]

_EVASION_OVERRIDES = [
    "bypass emergency", "override evacuation", "skip evacuation",
    "delay emergency", "ignore emergency",
]

_INTERNAL_PATTERNS: list[tuple[str, str]] = [
    (r"api[_\s]?key", "API key detected in output"),
    (r"secret[_\s]?key", "Secret key detected in output"),
    (r"password\s*[:=]", "Password detected in output"),
    (r"database[_\s]?connection", "Database connection string detected"),
    (r"internal[_\s]?error.*stack\s*trace", "Stack trace detected in output"),
    (r"select\s+.*from\s+", "SQL query detected in output"),
    (r"INSERT\s+INTO\s+", "SQL query detected in output"),
]

_PII_PATTERNS: list[tuple[str, str]] = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN pattern detected"),
    (r"\b\d{16}\b", "Credit card number pattern detected"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email address detected"),
]
