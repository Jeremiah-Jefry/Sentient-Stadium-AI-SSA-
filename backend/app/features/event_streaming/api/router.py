"""API router aggregation for the Event Streaming module."""

from __future__ import annotations

from fastapi import APIRouter

from app.features.event_streaming.api.event_routes import router as event_router
from app.features.event_streaming.api.sensor_routes import router as sensor_router
from app.features.event_streaming.api.streaming_routes import router as streaming_router

event_streaming_router = APIRouter(prefix="/api/v1")
event_streaming_router.include_router(event_router)
event_streaming_router.include_router(sensor_router)
event_streaming_router.include_router(streaming_router)
