"""Domain-specific exception hierarchy for the IAM module."""

from __future__ import annotations


class IAMError(Exception):
    """Base exception for all IAM-related errors."""

    def __init__(self, message: str, error_code: str, details: dict | None = None) -> None:
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(IAMError):
    """Raised when authentication fails (invalid credentials, expired token, etc.)."""

    def __init__(self, message: str = "Authentication failed", details: dict | None = None) -> None:
        super().__init__(message=message, error_code="AUTHENTICATION_FAILED", details=details)


class AuthorizationError(IAMError):
    """Raised when a user lacks required permissions."""

    def __init__(self, message: str = "Access denied", details: dict | None = None) -> None:
        super().__init__(message=message, error_code="AUTHORIZATION_FAILED", details=details)


class TokenExpiredError(IAMError):
    """Raised when a JWT or session token has expired."""

    def __init__(self, message: str = "Token has expired", details: dict | None = None) -> None:
        super().__init__(message=message, error_code="TOKEN_EXPIRED", details=details)


class TokenRevokedError(IAMError):
    """Raised when a token has been revoked."""

    def __init__(self, message: str = "Token has been revoked", details: dict | None = None) -> None:
        super().__init__(message=message, error_code="TOKEN_REVOKED", details=details)


class UserNotFoundError(IAMError):
    """Raised when a user cannot be found."""

    def __init__(self, identifier: str = "user", details: dict | None = None) -> None:
        super().__init__(
            message=f"{identifier} not found",
            error_code="USER_NOT_FOUND",
            details=details,
        )


class UserAlreadyExistsError(IAMError):
    """Raised when attempting to create a user that already exists."""

    def __init__(self, field: str = "email", details: dict | None = None) -> None:
        super().__init__(
            message=f"User with this {field} already exists",
            error_code="USER_ALREADY_EXISTS",
            details=details,
        )


class AccountLockedError(IAMError):
    """Raised when an account is locked due to too many failed attempts."""

    def __init__(self, message: str = "Account is locked", details: dict | None = None) -> None:
        super().__init__(message=message, error_code="ACCOUNT_LOCKED", details=details)


class EmailNotVerifiedError(IAMError):
    """Raised when an operation requires a verified email."""

    def __init__(self, details: dict | None = None) -> None:
        super().__init__(
            message="Email address has not been verified",
            error_code="EMAIL_NOT_VERIFIED",
            details=details,
        )


class RateLimitExceededError(IAMError):
    """Raised when a rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", details: dict | None = None) -> None:
        super().__init__(message=message, error_code="RATE_LIMIT_EXCEEDED", details=details)


class ValidationError(IAMError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed", details: dict | None = None) -> None:
        super().__init__(message=message, error_code="VALIDATION_FAILED", details=details)
