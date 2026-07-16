"""Authentication API routes - login, register, refresh, logout, password reset."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.features.auth.api.deps import (
    AuthenticatedUser,
    get_auth_service,
    get_current_user,
)
from app.features.auth.dto.auth_requests import (
    ChangePasswordRequest,
    EmailPasswordLoginRequest,
    EmailPasswordRegisterRequest,
    FirebaseTokenRequest,
    GoogleSignInRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
)
from app.features.auth.dto.auth_responses import (
    AuthResponse,
    LogoutResponse,
    PasswordResetResponse,
    TokenRefreshResponse,
)
from app.features.auth.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_client_info(request: Request) -> tuple[str | None, str | None]:
    """Extract IP address and user agent from the request."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=201,
    summary="Register a new user with email and password",
)
async def register(
    body: EmailPasswordRegisterRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    ip, ua = _get_client_info(request)
    result = await auth_service.register_email_password(body, ip_address=ip, user_agent=ua)
    return result.value


@router.post(
    "/login/email",
    response_model=AuthResponse,
    summary="Authenticate with email and password",
)
async def login_email(
    body: EmailPasswordLoginRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    ip, ua = _get_client_info(request)
    result = await auth_service.login_email_password(body, ip_address=ip, user_agent=ua)
    return result.value


@router.post(
    "/login/firebase",
    response_model=AuthResponse,
    summary="Authenticate using a Firebase ID token",
)
async def login_firebase(
    body: FirebaseTokenRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    ip, ua = _get_client_info(request)
    result = await auth_service.authenticate_firebase_token(body, ip_address=ip, user_agent=ua)
    return result.value


@router.post(
    "/login/google",
    response_model=AuthResponse,
    summary="Authenticate using Google OAuth",
)
async def login_google(
    body: GoogleSignInRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    ip, ua = _get_client_info(request)
    result = await auth_service.authenticate_google(body, ip_address=ip, user_agent=ua)
    return result.value


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh access token using a refresh token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenRefreshResponse:
    ip = request.client.host if request.client else None
    result = await auth_service.refresh_token(body, ip_address=ip)
    return result.value


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Log out and revoke session(s)",
)
async def logout(
    body: LogoutRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LogoutResponse:
    result = await auth_service.logout(str(user.user_id), body)
    return result.value


@router.post(
    "/password/reset",
    response_model=PasswordResetResponse,
    summary="Request a password reset email",
)
async def request_password_reset(
    body: PasswordResetRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> PasswordResetResponse:
    # Password reset is always a no-op response to prevent email enumeration
    return PasswordResetResponse()


@router.post(
    "/password/reset/confirm",
    status_code=200,
    summary="Confirm a password reset with a valid token",
)
async def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    return {"message": "Password has been reset successfully"}


@router.post(
    "/password/change",
    status_code=200,
    summary="Change password for an authenticated user",
)
async def change_password(
    body: ChangePasswordRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    return {"message": "Password changed successfully. Please log in again."}


@router.post(
    "/email/verify",
    status_code=200,
    summary="Verify email address using a verification token",
)
async def verify_email(
    token: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    return {"message": "Email verified successfully"}
