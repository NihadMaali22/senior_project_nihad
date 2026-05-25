# ============================================================
# API Router Aggregator
# ============================================================
"""
Aggregates all sub-routers under the /api/v1 prefix.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.admin.router import router as admin_router
from app.api.assistant import router as assistant_router
from app.api.documents import router as documents_router
from app.auth.router import router as auth_router
from app.api.tts import router as tts_router
from app.robot.router import router as robot_router

# Main API router with versioned prefix
api_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
api_router.include_router(auth_router)
api_router.include_router(assistant_router)
api_router.include_router(documents_router)
api_router.include_router(admin_router)
api_router.include_router(tts_router)
api_router.include_router(robot_router)
