"""Authentication response DTOs for tokens and session data."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.features.auth.models.user import AuthProvider, UserStatus


class TokenPair(BaseModel):
    """Access token and refresh token pair returned after authentication."""

    access_token: str = Field(..., description="Short-lived JWT access token")
    refresh_token: str = Field(..., description="Long-lived refresh token for rotation")
    token_type: str = Field(default="Bearer")
    expires_in: int = Field(..., description="Access token TTL in seconds")


class AuthResponse(BaseModel):
    """Successful authentication response with tokens and user summary."""

    tokens: TokenPair
    user: "UserSummary"


class UserSummary(BaseModel):
    """Minimal user information returned in auth responses."""

    id: UUID
    email: str
    display_name: str
    photo_url: str | None = None
    email_verified: bool
    auth_provider: AuthProvider
    status: UserStatus

    model_config = {"from_attributes": True}


class TokenRefreshResponse(BaseModel):
    """Response after a successful token refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class LogoutResponse(BaseModel):
    """Confirmation of successful logout."""

    message: str = "Logged out successfully"
    sessions_revoked: int = 0


class PasswordResetResponse(BaseModel):
    """Confirmation that a password reset email was sent."""

    message: str = "If the email exists, a reset link has been sent"


class EmailVerificationResponse(BaseModel):
    """Confirmation that email verification was successful."""

    message: str = "Email verified successfully"
