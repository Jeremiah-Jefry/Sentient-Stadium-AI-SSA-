"""API router aggregation for the Digital Twin module."""

from __future__ import annotations

from fastapi import APIRouter

from app.features.digital_twin.api.entity_routes import router as entity_router
from app.features.digital_twin.api.spatial_routes import router as spatial_router
from app.features.digital_twin.api.zone_routes import router as zone_router

digital_twin_router = APIRouter(prefix="/api/v1")
digital_twin_router.include_router(entity_router)
digital_twin_router.include_router(zone_router)
digital_twin_router.include_router(spatial_router)
