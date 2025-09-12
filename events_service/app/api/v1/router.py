"""
API v1 router for Events Service.
"""

from fastapi import APIRouter

from .events_public import router as events_public_router
from .events_admin import router as events_admin_router

router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(events_public_router)
router.include_router(events_admin_router)