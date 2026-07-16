"""Firebase Authentication service for token verification and user management."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.config import get_settings
from app.shared.exceptions import AuthenticationError
from app.shared.result import Failure, Result, Success

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FirebaseUser:
    """Verified Firebase user data extracted from ID tokens."""

    uid: str
    email: str | None
    display_name: str | None
    photo_url: str | None
    phone_number: str | None
    email_verified: bool
    provider_id: str


class FirebaseService:
    """Handles all interactions with Firebase Authentication.

    Responsibilities:
    - Verify Firebase ID tokens issued by Firebase Auth
    - Extract user claims from verified tokens
    - Initialize and manage the Firebase Admin SDK
    """

    _initialized: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize Firebase Admin SDK. Called once at application startup."""
        if cls._initialized:
            return

        settings = get_settings()
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred, {
                "projectId": settings.FIREBASE_PROJECT_ID,
            })
            cls._initialized = True
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception:
            logger.exception("Failed to initialize Firebase Admin SDK")
            raise

    async def verify_id_token(self, id_token: str) -> Result[FirebaseUser]:
        """Verify a Firebase ID token and return the authenticated user.

        Validates token signature, expiration, audience, and issuer.
        This is the primary entry point for Firebase-based authentication.
        """
        try:
            decoded_token = firebase_auth.verify_id_token(
                id_token,
                check_revoked=True,
            )
            user = FirebaseUser(
                uid=decoded_token["uid"],
                email=decoded_token.get("email"),
                display_name=decoded_token.get("name"),
                photo_url=decoded_token.get("picture"),
                phone_number=decoded_token.get("phone_number"),
                email_verified=decoded_token.get("email_verified", False),
                provider_id=decoded_token.get("firebase", {}).get("sign_in_provider", "unknown"),
            )
            return Success(user)
        except firebase_auth.ExpiredIdTokenError:
            return Failure(error_code="FIREBASE_TOKEN_EXPIRED", message="Firebase ID token has expired")
        except firebase_auth.InvalidIdTokenError as exc:
            return Failure(
                error_code="FIREBASE_TOKEN_INVALID",
                message=f"Invalid Firebase ID token: {exc}",
            )
        except firebase_auth.RevokedIdTokenError:
            return Failure(
                error_code="FIREBASE_TOKEN_REVOKED",
                message="Firebase ID token has been revoked",
            )
        except Exception:
            logger.exception("Unexpected error verifying Firebase token")
            return Failure(
                error_code="FIREBASE_VERIFICATION_FAILED",
                message="Failed to verify Firebase token",
            )

    async def verify_google_access_token(self, access_token: str) -> Result[dict[str, Any]]:
        """Verify a Google OAuth access token and return user info.

        Used for Google Sign-In flow where the client provides
        an access token from the Google Identity Services SDK.
        """
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return Success(response.json())
                return Failure(
                    error_code="GOOGLE_TOKEN_INVALID",
                    message=f"Google token verification failed: HTTP {response.status_code}",
                )
        except httpx.TimeoutException:
            return Failure(
                error_code="GOOGLE_TIMEOUT",
                message="Google token verification timed out",
            )
        except Exception:
            logger.exception("Unexpected error verifying Google token")
            return Failure(
                error_code="GOOGLE_VERIFICATION_FAILED",
                message="Failed to verify Google token",
            )

    async def create_custom_token(self, uid: str, claims: dict[str, Any] | None = None) -> Result[str]:
        """Create a Firebase custom token for server-side authentication."""
        try:
            custom_token = firebase_auth.create_custom_token(uid, claims)
            return Success(custom_token.decode("utf-8"))
        except Exception:
            logger.exception("Failed to create Firebase custom token")
            return Failure(
                error_code="FIREBASE_CUSTOM_TOKEN_FAILED",
                message="Failed to create custom token",
            )
