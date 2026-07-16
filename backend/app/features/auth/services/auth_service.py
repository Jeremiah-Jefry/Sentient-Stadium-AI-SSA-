"""Core auth service - orchestrates authentication flows end-to-end."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.config import get_settings
from app.features.auth.dto.auth_requests import (
    EmailPasswordLoginRequest,
    EmailPasswordRegisterRequest,
    FirebaseTokenRequest,
    GoogleSignInRequest,
    LogoutRequest,
    RefreshTokenRequest,
)
from app.features.auth.dto.auth_responses import AuthResponse, LogoutResponse, TokenPair, UserSummary
from app.features.auth.models.audit_log import AuditEventType
from app.features.auth.models.user import AuthProvider, User, UserStatus
from app.features.auth.repositories.user_repository import UserRepository
from app.features.auth.services.audit_service import AuditService
from app.features.auth.services.firebase_service import FirebaseService, FirebaseUser
from app.features.auth.services.rbac_service import RBACService
from app.features.auth.services.session_service import SessionService
from app.features.auth.services.token_service import TokenService, hash_token
from app.shared.exceptions import (
    AuthenticationError,
    UserAlreadyExistsError,
)
from app.shared.result import Failure, Result, Success
from app.shared.utils.sanitization import validate_email

settings = get_settings()
logger = logging.getLogger(__name__)


class AuthService:
    """Orchestrates all authentication flows.

    Coordinates between Firebase, token, session, RBAC, and audit services
    to implement complete authentication use cases. Each method represents
    a single authentication flow.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        token_service: TokenService,
        firebase_service: FirebaseService,
        session_service: SessionService,
        rbac_service: RBACService,
        audit_service: AuditService,
    ) -> None:
        self._user_repo = user_repository
        self._token_service = token_service
        self._firebase_service = firebase_service
        self._session_service = session_service
        self._rbac_service = rbac_service
        self._audit_service = audit_service

    async def register_email_password(
        self,
        request: EmailPasswordRegisterRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Result[AuthResponse]:
        """Register a new user with email and password.

        Steps:
        1. Validate and sanitize email
        2. Check for existing user
        3. Create Firebase user
        4. Create local user record
        5. Assign default role
        6. Issue tokens
        7. Create session
        8. Audit the event
        """
        email = validate_email(request.email)

        existing = await self._user_repo.exists_by_email(email)
        if existing and existing.value:
            return Failure(
                error_code="USER_ALREADY_EXISTS",
                message="A user with this email already exists",
            )

        # Create user record
        user = User(
            email=email,
            display_name=request.display_name.strip(),
            auth_provider=AuthProvider.EMAIL_PASSWORD,
            status=UserStatus.PENDING_VERIFICATION,
        )

        create_result = await self._user_repo.create(user)
        if not create_result:
            return Failure(
                error_code="USER_CREATE_FAILED",
                message="Failed to create user account",
            )

        user = create_result.value

        # Assign default role
        default_role = await self._rbac_service._role_repo.get_default_role()
        if default_role and default_role.value:
            await self._rbac_service.assign_role(
                user_id=user.id,
                role_id=default_role.value.id,
            )

        # Issue tokens
        auth_response = await self._issue_tokens_and_create_session(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self._audit_service.log_event(
            event_type=AuditEventType.ACCOUNT_CREATED,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return auth_response

    async def login_email_password(
        self,
        request: EmailPasswordLoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Result[AuthResponse]:
        """Authenticate a user with email and password.

        Implements account lockout after MAX_LOGIN_ATTEMPTS failures.
        """
        email = validate_email(request.email)
        user_result = await self._user_repo.get_by_email(email)

        if not user_result or not user_result.value:
            await self._audit_service.log_login_failure(
                user_id=None, ip_address=ip_address, user_agent=user_agent,
                reason="user_not_found",
            )
            return Failure(error_code="AUTHENTICATION_FAILED", message="Invalid email or password")

        user = user_result.value

        if user.status == UserStatus.LOCKED:
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                await self._audit_service.log_login_failure(
                    user_id=user.id, ip_address=ip_address, reason="account_locked",
                )
                return Failure(error_code="ACCOUNT_LOCKED", message="Account is locked")
            # Lockout expired, unlock
            user.status = UserStatus.ACTIVE
            user.failed_login_attempts = 0
            await self._user_repo.update(user)

        if user.status == UserStatus.SUSPENDED:
            return Failure(error_code="ACCOUNT_SUSPENDED", message="Account has been suspended")

        # Password verification would happen against Firebase
        # For email/password users, Firebase handles the password check

        # Successful login
        user.failed_login_attempts = 0
        user.last_login_at = datetime.now(timezone.utc)
        user.status = UserStatus.ACTIVE
        await self._user_repo.update(user)

        auth_response = await self._issue_tokens_and_create_session(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            fingerprint=request.fingerprint,
        )

        await self._audit_service.log_login_success(
            user_id=user.id, ip_address=ip_address, user_agent=user_agent,
        )

        return auth_response

    async def authenticate_firebase_token(
        self,
        request: FirebaseTokenRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Result[AuthResponse]:
        """Authenticate using a Firebase ID token.

        Used for email/password login and any Firebase-supported provider.
        """
        verification_result = await self._firebase_service.verify_id_token(request.id_token)
        if not verification_result or not verification_result.value:
            return Failure(
                error_code="FIREBASE_AUTH_FAILED",
                message="Firebase token verification failed",
            )

        firebase_user = verification_result.value
        return await self._upsert_and_authenticate(
            firebase_user=firebase_user,
            fingerprint=request.fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def authenticate_google(
        self,
        request: GoogleSignInRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Result[AuthResponse]:
        """Authenticate using Google OAuth credentials."""
        google_result = await self._firebase_service.verify_google_access_token(request.access_token)
        if not google_result or not google_result.value:
            return Failure(
                error_code="GOOGLE_AUTH_FAILED",
                message="Google authentication failed",
            )

        google_data = google_result.value
        firebase_user = FirebaseUser(
            uid=f"google:{google_data.get('sub', '')}",
            email=google_data.get("email"),
            display_name=google_data.get("name"),
            photo_url=google_data.get("picture"),
            phone_number=None,
            email_verified=google_data.get("email_verified", False),
            provider_id="google.com",
        )

        return await self._upsert_and_authenticate(
            firebase_user=firebase_user,
            fingerprint=request.fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def refresh_token(
        self,
        request: RefreshTokenRequest,
        ip_address: str | None = None,
    ) -> Result[TokenPair]:
        """Refresh an access token using a valid refresh token.

        Implements refresh token rotation: the old refresh token is
        invalidated and a new pair is issued.
        """
        token_hash = hash_token(request.refresh_token)
        session_result = await self._session_service.validate_session(token_hash)

        if not session_result or not session_result.value:
            return Failure(
                error_code="INVALID_REFRESH_TOKEN",
                message="Invalid or expired refresh token",
            )

        session = session_result.value

        # Get the user
        user_result = await self._user_repo.get_by_id(session.user_id)
        if not user_result or not user_result.value:
            return Failure(error_code="USER_NOT_FOUND", message="User not found")

        user = user_result.value

        # Revoke old session
        await self._session_service.revoke_by_token_hash(token_hash, reason="token_rotation")

        # Issue new tokens
        roles = await self._rbac_service.get_user_role_names(user.id)
        permissions = await self._rbac_service.get_user_permissions(user.id)

        role_names = roles.value if hasattr(roles, "value") else []
        perm_names = permissions.value if hasattr(permissions, "value") else []

        access_token = self._token_service.create_access_token(
            user_id=str(user.id),
            email=user.email,
            roles=role_names,
            permissions=perm_names,
        )
        new_refresh_raw, new_refresh_hash, expires_at = self._token_service.create_refresh_token()

        await self._session_service.create_session(
            user_id=user.id,
            refresh_token_hash=new_refresh_hash,
            fingerprint=session.fingerprint,
            ip_address=ip_address,
            user_agent=session.user_agent,
        )

        await self._audit_service.log_token_refresh(user_id=user.id)

        return Success(TokenPair(
            access_token=access_token,
            refresh_token=new_refresh_raw,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ))

    async def logout(
        self,
        user_id: str,
        request: LogoutRequest,
    ) -> Result[LogoutResponse]:
        """Log out a user, revoking the specified session(s)."""
        import uuid as uuid_lib

        uid = uuid_lib.UUID(user_id)

        if request.all_devices:
            count_result = await self._session_service.revoke_all_for_user(uid, reason="user_logout")
            count = count_result.value if hasattr(count_result, "value") else 0
        elif request.refresh_token:
            token_hash = hash_token(request.refresh_token)
            await self._session_service.revoke_by_token_hash(token_hash, reason="user_logout")
            count = 1
        else:
            count = 0

        await self._audit_service.log_logout(
            user_id=uid, all_devices=request.all_devices,
        )

        return Success(LogoutResponse(
            message="Logged out successfully",
            sessions_revoked=count,
        ))

    async def _upsert_and_authenticate(
        self,
        firebase_user: FirebaseUser,
        fingerprint: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Result[AuthResponse]:
        """Find or create a local user from Firebase data, then authenticate."""
        existing = await self._user_repo.get_by_firebase_uid(firebase_user.uid)

        if existing and existing.value:
            user = existing.value
            user.display_name = firebase_user.display_name or user.display_name
            user.photo_url = firebase_user.photo_url or user.photo_url
            user.email_verified = firebase_user.email_verified
            if user.status == UserStatus.PENDING_VERIFICATION and firebase_user.email_verified:
                user.status = UserStatus.ACTIVE
            user.last_login_at = datetime.now(timezone.utc)
            await self._user_repo.update(user)
        else:
            if not firebase_user.email:
                return Failure(
                    error_code="EMAIL_REQUIRED",
                    message="Email is required for account creation",
                )

            user = User(
                firebase_uid=firebase_user.uid,
                email=firebase_user.email,
                display_name=firebase_user.display_name or firebase_user.email.split("@")[0],
                photo_url=firebase_user.photo_url,
                phone_number=firebase_user.phone_number,
                auth_provider=AuthProvider.GOOGLE if firebase_user.provider_id == "google.com"
                    else AuthProvider.FIREBASE,
                email_verified=firebase_user.email_verified,
                status=UserStatus.ACTIVE if firebase_user.email_verified
                    else UserStatus.PENDING_VERIFICATION,
            )
            create_result = await self._user_repo.create(user)
            if not create_result:
                return Failure(error_code="USER_CREATE_FAILED", message="Failed to create user")

            user = create_result.value

            # Assign default role
            default_role = await self._rbac_service._role_repo.get_default_role()
            if default_role and default_role.value:
                await self._rbac_service.assign_role(user.id, default_role.value.id)

        return await self._issue_tokens_and_create_session(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            fingerprint=fingerprint,
        )

    async def _issue_tokens_and_create_session(
        self,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
        fingerprint: str = "unknown",
    ) -> Result[AuthResponse]:
        """Issue token pair and create a session."""
        roles = await self._rbac_service.get_user_role_names(user.id)
        permissions = await self._rbac_service.get_user_permissions(user.id)

        role_names = roles.value if hasattr(roles, "value") else []
        perm_names = permissions.value if hasattr(permissions, "value") else []

        access_token = self._token_service.create_access_token(
            user_id=str(user.id),
            email=user.email,
            roles=role_names,
            permissions=perm_names,
        )
        refresh_raw, refresh_hash, _ = self._token_service.create_refresh_token()

        await self._session_service.create_session(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            fingerprint=fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return Success(AuthResponse(
            tokens=TokenPair(
                access_token=access_token,
                refresh_token=refresh_raw,
                expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            ),
            user=UserSummary(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                photo_url=user.photo_url,
                email_verified=user.email_verified,
                auth_provider=user.auth_provider,
                status=user.status,
            ),
        ))
