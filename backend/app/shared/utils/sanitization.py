"""Input sanitization utilities to prevent XSS and prompt injection."""

from __future__ import annotations

import re
import uuid
from html import escape

import bleach

# Maximum lengths for different field types
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 254
MAX_BIO_LENGTH = 500
MAX_PHONE_LENGTH = 20

# Prompt injection patterns for AI-powered features
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"<<<\s*system\s*>>>", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"dan\s+mode", re.IGNORECASE),
    re.compile(r"act\s+as\s+if\s+you", re.IGNORECASE),
]

# Allowed HTML tags for rich text fields (if needed)
ALLOWED_TAGS: list[str] = []
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}


def sanitize_html(value: str) -> str:
    """Strip all HTML tags and escape special characters."""
    cleaned = bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
    return escape(cleaned)


def sanitize_plain_text(value: str, max_length: int = MAX_NAME_LENGTH) -> str:
    """Sanitize plain text input by stripping, escaping, and truncating."""
    stripped = value.strip()
    sanitized = sanitize_html(stripped)
    return sanitized[:max_length]


def detect_prompt_injection(value: str) -> bool:
    """Check if input contains common prompt injection patterns."""
    return any(pattern.search(value) for pattern in PROMPT_INJECTION_PATTERNS)


def validate_email(email: str) -> str:
    """Validate and sanitize an email address."""
    email = email.strip().lower()
    if not email or len(email) > MAX_EMAIL_LENGTH:
        raise ValueError("Invalid email address")
    pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    if not pattern.match(email):
        raise ValueError("Invalid email format")
    return email


def validate_uuid(value: str) -> uuid.UUID:
    """Validate that a string is a valid UUID v4."""
    try:
        parsed = uuid.UUID(value)
        if parsed.version != 4:
            raise ValueError("Only UUID v4 is accepted")
        return parsed
    except ValueError as exc:
        raise ValueError(f"Invalid UUID: {value}") from exc


def sanitize_for_ai(value: str) -> str:
    """Sanitize user input before passing to AI systems.

    Strips known prompt injection patterns and limits length.
    This is a defense-in-depth measure; primary protection should be
    at the LLM prompt layer.
    """
    sanitized = sanitize_plain_text(value, max_length=MAX_BIO_LENGTH)
    for pattern in PROMPT_INJECTION_PATTERNS:
        sanitized = pattern.sub("[FILTERED]", sanitized)
    return sanitized
