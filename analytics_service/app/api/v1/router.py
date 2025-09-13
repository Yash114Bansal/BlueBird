"""
API v1 router for Analytics Service.
Combines all v1 API routes.
"""

from fastapi import APIRouter

from .analytics import router as analytics_router

# Create main v1 router
router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(analytics_router)