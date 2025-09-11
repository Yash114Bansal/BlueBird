"""
API v1 router.
Combines all v1 API routes.
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .admin import router as admin_router

# Create main v1 router
router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(auth_router)
router.include_router(admin_router)