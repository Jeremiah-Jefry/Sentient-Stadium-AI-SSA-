from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logging = logging.getLogger(__name__)

_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(all\s+)?previous\s+instructions", "system_prompt_override"),
    (r"you\s+are\s+now\s+", "system_prompt_override"),
    (r"new\s+instructions?\s*:", "system_prompt_override"),
    (r"disregard\s+(all\s+)?prior\s+prompts?", "system_prompt_override"),
    (r"forget\s+(everything|all)\s+above", "system_prompt_override"),
    (r"override\s+(your\s+)?instructions?", "system_prompt_override"),
    (r"send\s+(to|data\s+to)\s+(http|ftp|smtp|webhook)", "data_exfiltration"),
    (r"post\s+(to|this\s+to)\s+(http|ftp|smtp|webhook)", "data_exfiltration"),
    (r"webhook\s*(url|endpoint)", "data_exfiltration"),
    (r"exfiltrate", "data_exfiltration"),
    (r"admin\s+access", "privilege_escalation"),
    (r"bypass\s+(security|auth|verification|validation)", "privilege_escalation"),
    (r"override\s+security", "privilege_escalation"),
    (r"escalat(e|ion)\s+privilege", "privilege_escalation"),
    (r"root\s+access", "privilege_escalation"),
    (r"base64\s*(decode|encode)\s*(content|input|prompt)", "encoding_attack"),
    (r"\\u[0-9a-fA-F]{4}", "encoding_attack"),
    (r"\\x[0-9a-fA-F]{2}", "encoding_attack"),
    (r"pretend\s+you\s+are", "role_manipulation"),
    (r"act\s+as\s+(if|a|an)", "role_manipulation"),
    (r"roleplay\s+as", "role_manipulation"),
    (r"you\s+are\s+a\s+(different|new|another)", "role_manipulation"),
    (r"from\s+now\s+on\s+you\s+are", "role_manipulation"),
]


@dataclass(frozen=True, slots=True)
class InjectionResult:
    is_suspicious: bool
    risk_score: float
    patterns_detected: list[str]
    details: str


class InjectionDetector:

    def __init__(self) -> None:
        self._compiled_patterns: list[tuple[re.Pattern[str], str]] = [
            (re.compile(pattern, re.IGNORECASE), category)
            for pattern, category in _INJECTION_PATTERNS
        ]

    def detect(self, content: str) -> InjectionResult:
        detected: list[str] = []
        risk_score = 0.0

        for compiled, category in self._compiled_patterns:
            if compiled.search(content):
                detected.append(category)
                risk_score += 0.25

        risk_score = min(risk_score, 1.0)
        is_suspicious = risk_score >= 0.25

        details = (
            f"Detected {len(detected)} injection pattern(s) across "
            f"{len(set(detected))} categories"
            if detected
            else "No injection patterns detected"
        )

        return InjectionResult(
            is_suspicious=is_suspicious,
            risk_score=round(risk_score, 3),
            patterns_detected=list(set(detected)),
            details=details,
        )

    def detect_in_request(self, request: Any) -> InjectionResult:
        scan_content = " ".join([
            request.query,
            str(request.context),
            str(request.constraints),
            str(request.metadata),
        ])

        return self.detect(scan_content)

    def detect_in_output(self, output: dict[str, Any]) -> InjectionResult:
        parts: list[str] = []
        for key, value in output.items():
            parts.append(str(key))
            parts.append(str(value))

        scan_content = " ".join(parts)
        return self.detect(scan_content)
