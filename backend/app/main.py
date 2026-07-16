"""FastAPI application factory and startup configuration."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.features.auth.api.error_handlers import register_error_handlers
from app.features.auth.api.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.features.auth.api.router import iam_router
from app.features.auth.services.firebase_service import FirebaseService

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize external services on startup."""
    logger.info("Starting StadiumMind IAM service (env=%s)", settings.APP_ENV)

    # Initialize Firebase Admin SDK
    FirebaseService.initialize()

    yield

    logger.info("Shutting down StadiumMind IAM service")


def create_app() -> FastAPI:
    """Application factory for the StadiumMind IAM service."""
    app = FastAPI(
        title="StadiumMind OS - IAM Service",
        description="Identity & Access Management for FIFA World Cup 2026 volunteers",
        version="1.0.0",
        docs_url="/docs" if settings.APP_DEBUG else None,
        redoc_url="/redoc" if settings.APP_DEBUG else None,
        openapi_url="/openapi.json" if settings.APP_DEBUG else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    # Security middleware (order matters: outermost runs first)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Routes
    app.include_router(iam_router)

    # Error handlers
    register_error_handlers(app)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": "stadiummind-iam"}

    return app


app = create_app()
