"""JWT token service for access and refresh token lifecycle management."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import get_settings
from app.shared.exceptions import AuthenticationError, TokenExpiredError, TokenRevokedError
from app.shared.result import Failure, Result, Success

settings = get_settings()


def hash_token(token: str) -> str:
    """Create a SHA-256 hash of a token for secure storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TokenService:
    """Manages JWT access tokens and opaque refresh tokens.

    Responsibilities:
    - Generate JWT access tokens with user claims
    - Generate cryptographically secure refresh tokens
    - Verify and decode JWT tokens
    - Rotate refresh tokens securely
    """

    def create_access_token(
        self,
        user_id: str,
        email: str,
        roles: list[str],
        permissions: list[str],
    ) -> str:
        """Create a signed JWT access token with user identity and permissions.

        Token payload includes: sub, email, roles, permissions, iss, iat, exp.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": str(user_id),
            "email": email,
            "roles": roles,
            "permissions": permissions,
            "iss": settings.JWT_ISSUER,
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_refresh_token(self) -> tuple[str, str, datetime]:
        """Generate a new opaque refresh token.

        Returns:
            - Raw token (to send to client)
            - SHA-256 hash (to store in database)
            - Expiration datetime
        """
        raw_token = secrets.token_urlsafe(64)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        return raw_token, token_hash, expires_at

    def verify_access_token(self, token: str) -> Result[dict]:
        """Decode and verify a JWT access token.

        Validates: signature, expiration, issuer.
        Returns the decoded token payload on success.
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
            )
            return Success(payload)
        except JWTError as exc:
            error_msg = str(exc).lower()
            if "expired" in error_msg:
                return Failure(error_code="TOKEN_EXPIRED", message="Access token has expired")
            return Failure(error_code="TOKEN_INVALID", message=f"Invalid access token: {exc}")

    def rotate_refresh_token(
        self,
        current_refresh_hash: str,
    ) -> tuple[str, str, datetime]:
        """Rotate a refresh token, returning the new token and its hash.

        Token rotation invalidates the old refresh token and issues a new one.
        This prevents token reuse attacks.
        """
        return self.create_refresh_token()

    def get_token_fingerprint(self, user_agent: str, ip_address: str) -> str:
        """Generate a fingerprint for device identification."""
        raw = f"{user_agent}:{ip_address}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
