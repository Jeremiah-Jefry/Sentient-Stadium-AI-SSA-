"""FastAPI application factory and startup configuration."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.features.ai_intelligence.api.deps import get_intelligence_service
from app.features.ai_intelligence.api.error_handlers import (
    register_ai_intelligence_error_handlers,
)
from app.features.ai_intelligence.api.router import ai_intelligence_router
from app.features.ai_intelligence.api.websocket import intelligence_websocket
from app.features.ai_intelligence.consumers.intelligence_consumer import (
    IntelligenceConsumer,
)
from app.features.auth.api.error_handlers import register_error_handlers
from app.features.auth.api.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.features.auth.api.router import iam_router
from app.features.auth.services.firebase_service import FirebaseService
from app.features.digital_twin.api.error_handlers import (
    register_digital_twin_error_handlers,
)
from app.features.digital_twin.api.router import digital_twin_router
from app.features.digital_twin.api.websocket import digital_twin_websocket
from app.features.event_streaming.api.deps import get_event_bus
from app.features.event_streaming.api.error_handlers import (
    register_event_streaming_error_handlers,
)
from app.features.event_streaming.api.router import event_streaming_router
from app.features.event_streaming.api.websocket import event_stream_websocket
from app.features.navigation.api.deps import get_navigation_consumer, get_navigation_router
from app.features.navigation.api.error_handlers import (
    register_navigation_error_handlers,
)
from app.features.navigation.api.router import navigation_router

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize external services on startup."""
    logger.info("Starting StadiumMind OS (env=%s)", settings.APP_ENV)

    # Initialize Firebase Admin SDK
    FirebaseService.initialize()

    # Start the event streaming bus
    event_bus = get_event_bus()
    await event_bus.start()
    logger.info("Event streaming bus started")

    # Start AI Intelligence consumer
    intelligence_service = get_intelligence_service()
    intelligence_consumer = IntelligenceConsumer(intelligence_service)
    event_bus.register_consumer(intelligence_consumer)
    await intelligence_consumer.start()
    logger.info("AI Intelligence consumer started")

    # Start Navigation consumer
    nav_consumer = get_navigation_consumer()
    event_bus.subscribe(
        subscriber_id=nav_consumer.SUBSCRIBER_ID,
        callback=nav_consumer.handle_event,
        categories={"crowd", "weather", "emergency", "medical",
                     "security", "infrastructure"},
    )
    await nav_consumer.start()
    logger.info("Navigation consumer started")

    yield

    # Shutdown Navigation consumer
    await nav_consumer.stop()
    event_bus.unsubscribe(nav_consumer.SUBSCRIBER_ID)
    logger.info("Navigation consumer stopped")

    # Shutdown AI Intelligence consumer
    await intelligence_consumer.stop()
    logger.info("AI Intelligence consumer stopped")

    # Shutdown the event streaming bus
    await event_bus.stop()
    logger.info("Shutting down StadiumMind OS")


def create_app() -> FastAPI:
    """Application factory for StadiumMind OS."""
    app = FastAPI(
        title="StadiumMind OS",
        description="Enterprise Multi-Agent AI Platform for FIFA World Cup 2026",
        version="2.0.0",
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
    app.include_router(digital_twin_router)
    app.include_router(event_streaming_router)
    app.include_router(ai_intelligence_router)
    app.include_router(navigation_router)

    # WebSocket endpoints
    app.websocket("/ws/digital-twin")(digital_twin_websocket)
    app.websocket("/ws/events")(event_stream_websocket)
    app.websocket("/ws/intelligence")(intelligence_websocket)

    # Error handlers
    register_error_handlers(app)
    register_digital_twin_error_handlers(app)
    register_event_streaming_error_handlers(app)
    register_ai_intelligence_error_handlers(app)
    register_navigation_error_handlers(app)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": "stadiummind-os", "version": "2.0.0"}

    return app


app = create_app()
