"""Authentication request DTOs for login, registration, and token operations."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.shared.utils.sanitization import MAX_NAME_LENGTH, MAX_EMAIL_LENGTH


class EmailPasswordRegisterRequest(BaseModel):
    """Request to register a new user with email and password."""

    email: EmailStr = Field(..., max_length=MAX_EMAIL_LENGTH)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)


class EmailPasswordLoginRequest(BaseModel):
    """Request to authenticate with email and password."""

    email: EmailStr = Field(..., max_length=MAX_EMAIL_LENGTH)
    password: str = Field(..., min_length=1, max_length=128)
    fingerprint: str = Field(..., min_length=1, max_length=256)


class FirebaseTokenRequest(BaseModel):
    """Request to authenticate using a Firebase ID token."""

    id_token: str = Field(..., min_length=10, max_length=2048)
    fingerprint: str = Field(..., min_length=1, max_length=256)


class GoogleSignInRequest(BaseModel):
    """Request to authenticate using Google OAuth credentials."""

    access_token: str = Field(..., min_length=10, max_length=2048)
    id_token: str | None = Field(None, max_length=2048)
    fingerprint: str = Field(..., min_length=1, max_length=256)


class RefreshTokenRequest(BaseModel):
    """Request to exchange a refresh token for a new access token."""

    refresh_token: str = Field(..., min_length=10, max_length=2048)


class LogoutRequest(BaseModel):
    """Request to log out. If refresh_token is provided, revoke only that session."""

    refresh_token: str | None = Field(None, max_length=2048)
    all_devices: bool = Field(default=False)


class PasswordResetRequest(BaseModel):
    """Request to initiate a password reset email."""

    email: EmailStr = Field(..., max_length=MAX_EMAIL_LENGTH)


class PasswordResetConfirmRequest(BaseModel):
    """Request to confirm a password reset with a valid token."""

    token: str = Field(..., min_length=1, max_length=2048)
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    """Request to change password for an authenticated user."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    """Request to verify an email address using a verification token."""

    token: str = Field(..., min_length=1, max_length=2048)
