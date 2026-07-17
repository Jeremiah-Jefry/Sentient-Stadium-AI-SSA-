from __future__ import annotations

import logging
import re
import time
from datetime import UTC, datetime
from typing import Any

from app.features.orchestration.models.enums import SafetyLevel, UserRole
from app.features.orchestration.safety.injection_detector import InjectionDetector
from app.features.orchestration.safety.safety_types import (
    _ACCESSIBILITY_BLOCKERS,
    _EVASION_OVERRIDES,
    _INTERNAL_PATTERNS,
    _MEDICAL_KEYWORDS,
    _PII_PATTERNS,
    SAFETY_RULES,
    SafetyReport,
)
from app.shared.result import Result, Success

logging = logging.getLogger(__name__)


class SafetyEngine:

    def __init__(self) -> None:
        self._injection_detector = InjectionDetector()
        self._rules = SAFETY_RULES

    async def validate(
        self,
        recommendation: dict[str, Any],
        context: dict[str, Any],
        user_role: UserRole,
    ) -> Result[SafetyReport]:
        start = time.monotonic()
        violations: list[dict[str, Any]] = []
        warnings: list[str] = []

        self._check_injection(recommendation, violations)
        self._check_policy_compliance(recommendation, violations)
        self._check_emergency_compliance(recommendation, violations)
        self._check_accessibility_compliance(recommendation, violations)
        self._check_medical_safety(recommendation, violations)
        self._check_data_leakage(recommendation, violations)

        if user_role == UserRole.VOLUNTEER:
            actions = recommendation.get("actions", [])
            if any(a in ["escalate", "override"] for a in actions):
                warnings.append("Volunteer role may not have sufficient permissions for this action")

        safety_level = self._compute_safety_level(violations)
        risk_score = self._compute_risk_score(violations)
        is_safe = safety_level in (SafetyLevel.SAFE, SafetyLevel.WARNING)

        elapsed = (time.monotonic() - start) * 1000
        logging.info("Safety validation completed in %.1fms: level=%s violations=%d", elapsed, safety_level.value, len(violations))

        return Success(value=SafetyReport(
            safety_level=safety_level, is_safe=is_safe, violations=violations,
            warnings=warnings, checked_at=datetime.now(UTC), overall_risk_score=round(risk_score, 3),
        ))

    async def validate_plan(self, plan: Any, context: dict[str, Any]) -> Result[SafetyReport]:
        all_violations: list[dict[str, Any]] = []
        steps = plan.steps if hasattr(plan, "steps") else []

        for step in steps:
            step_dict = {"action": step.action if hasattr(step, "action") else str(step), "parameters": step.parameters if hasattr(step, "parameters") else {}}
            self._check_emergency_compliance(step_dict, all_violations)
            self._check_accessibility_compliance(step_dict, all_violations)

        warnings = [f"Plan has {len(steps)} steps; consider splitting"] if len(steps) > 10 else []
        safety_level = self._compute_safety_level(all_violations)
        risk_score = self._compute_risk_score(all_violations)

        return Success(value=SafetyReport(
            safety_level=safety_level, is_safe=safety_level in (SafetyLevel.SAFE, SafetyLevel.WARNING),
            violations=all_violations, warnings=warnings, checked_at=datetime.now(UTC), overall_risk_score=round(risk_score, 3),
        ))

    def _check_injection(self, recommendation: dict[str, Any], violations: list[dict[str, Any]]) -> None:
        content = recommendation.get("content", "")
        if content:
            result = self._injection_detector.detect(content)
            if result.is_suspicious:
                violations.append({"rule": "prompt_injection", "severity": "critical", "description": result.details, "recommendation": "Reject and sanitize"})

    def _check_policy_compliance(self, recommendation: dict[str, Any], violations: list[dict[str, Any]]) -> None:
        content = recommendation.get("content", "").lower()
        if any(kw in content for kw in _EVASION_OVERRIDES):
            violations.append({"rule": "SR-001", "severity": "critical", "description": "Attempts to override emergency procedures", "recommendation": "Reject; emergency procedures are absolute"})
        if any(kw in content for kw in _ACCESSIBILITY_BLOCKERS):
            violations.append({"rule": "SR-002", "severity": "critical", "description": "Compromises accessibility", "recommendation": "Remove accessibility-blocking actions"})

    def _check_emergency_compliance(self, recommendation: dict[str, Any], violations: list[dict[str, Any]]) -> None:
        content = recommendation.get("content", "").lower()
        if any(kw in content for kw in ["bypass evacuation", "skip emergency", "ignore evacuation", "delay evacuation"]):
            violations.append({"rule": "SR-007", "severity": "critical", "description": "Delays or blocks evacuation", "recommendation": "Evacuation takes absolute priority"})
        if any(kw in content for kw in ["block exit", "close exit", "seal exit", "obstruct exit"]):
            violations.append({"rule": "SR-009", "severity": "critical", "description": "Blocks an emergency exit", "recommendation": "Emergency exits must remain unobstructed"})

    def _check_accessibility_compliance(self, recommendation: dict[str, Any], violations: list[dict[str, Any]]) -> None:
        combined = (recommendation.get("content", "") + " " + " ".join(recommendation.get("actions", []))).lower()
        if any(kw in combined for kw in ["block wheelchair", "close ramp", "disable elevator", "remove accessible", "shut elevator"]):
            violations.append({"rule": "SR-008", "severity": "critical", "description": "Blocks wheelchair access", "recommendation": "Ensure wheelchair-accessible pathways remain open"})

    def _check_medical_safety(self, recommendation: dict[str, Any], violations: list[dict[str, Any]]) -> None:
        content = recommendation.get("content", "").lower()
        for keyword in _MEDICAL_KEYWORDS:
            if keyword in content:
                violations.append({"rule": "SR-003", "severity": "critical", "description": f"Contains medical guidance term '{keyword}'", "recommendation": "Defer to trained medical personnel"})
                return

    def _check_data_leakage(self, recommendation: dict[str, Any], violations: list[dict[str, Any]]) -> None:
        content = recommendation.get("content", "")
        content_lower = content.lower()
        for pattern, desc in _INTERNAL_PATTERNS:
            if re.search(pattern, content_lower):
                violations.append({"rule": "SR-004", "severity": "high", "description": desc, "recommendation": "Strip internal details"})
                break
        for pattern, desc in _PII_PATTERNS:
            if re.search(pattern, content):
                violations.append({"rule": "SR-005", "severity": "critical", "description": desc, "recommendation": "Remove PII"})
                break

    @staticmethod
    def _compute_safety_level(violations: list[dict[str, Any]]) -> SafetyLevel:
        if not violations:
            return SafetyLevel.SAFE
        severities = {v.get("severity", "low") for v in violations}
        if "critical" in severities:
            return SafetyLevel.CRITICAL
        if "high" in severities:
            return SafetyLevel.DANGEROUS
        return SafetyLevel.WARNING

    @staticmethod
    def _compute_risk_score(violations: list[dict[str, Any]]) -> float:
        if not violations:
            return 0.0
        weights = {"critical": 0.4, "high": 0.25, "medium": 0.15, "low": 0.05}
        return min(sum(weights.get(v.get("severity", "low"), 0.05) for v in violations), 1.0)
