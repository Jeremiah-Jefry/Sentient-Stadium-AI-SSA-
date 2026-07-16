"""Typed Result type for explicit error handling without exceptions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Success(Generic[T]):
    """Represents a successful operation result."""

    value: T
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Failure(Generic[T]):
    """Represents a failed operation result with structured error information."""

    error_code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


Result = Success[T] | Failure[T]


def is_success(result: Result[T]) -> bool:
    return isinstance(result, Success)


def is_failure(result: Result[T]) -> bool:
    return isinstance(result, Failure)


def unwrap(result: Result[T]) -> T:
    """Return the value if Success, raise if Failure."""
    if isinstance(result, Success):
        return result.value
    raise RuntimeError(f"Unwrap called on Failure: {result.error_code} - {result.message}")
