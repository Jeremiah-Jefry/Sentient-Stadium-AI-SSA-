"""Navigation API router — aggregates all route endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.features.navigation.api.route_routes import router as route_router

navigation_router = APIRouter(prefix="/api/v1/navigation", tags=["Navigation"])
navigation_router.include_router(route_router)
