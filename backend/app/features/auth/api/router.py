"""API router aggregation for the IAM module."""

from __future__ import annotations

from fastapi import APIRouter

from app.features.auth.api.admin_routes import router as admin_router
from app.features.auth.api.auth_routes import router as auth_router
from app.features.auth.api.user_routes import router as user_router

iam_router = APIRouter(prefix="/api/v1")
iam_router.include_router(auth_router)
iam_router.include_router(user_router)
iam_router.include_router(admin_router)
