"""
Main API router for Bookings Service.
Combines all API endpoints and provides health checks.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.api.dependencies import check_service_health
from app.db.database import get_db
from app.schemas.booking import HealthCheckResponse

logger = logging.getLogger(__name__)

# Create main router
router = APIRouter(prefix="/api/v1")

# Include sub-routers
from app.api.v1.bookings import router as bookings_router
from app.api.v1.availability import router as availability_router
from app.api.v1.admin import router as admin_router

router.include_router(bookings_router)
router.include_router(availability_router)
router.include_router(admin_router)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint for the bookings service.
    
    Returns:
        Service health status
    """
    try:
        # Check service health
        health_status = await check_service_health()
        
        # Determine overall status
        if health_status["overall"] == "healthy":
            status_code = "healthy"
        else:
            status_code = "unhealthy"
        
        return HealthCheckResponse(
            status=status_code,
            version="1.0.0",
            database=health_status["database"],
            redis=health_status["redis"],
            uptime=0.0  # This would be calculated from service start time
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            version="1.0.0",
            database="unknown",
            redis="unknown",
            uptime=0.0
        )


@router.get("/info")
async def service_info():
    """
    Service information endpoint.
    
    Returns:
        Service information and capabilities
    """
    return {
        "service": "Bookings Service",
        "version": "1.0.0",
        "description": "High consistency booking management service",
        "capabilities": [
            "Booking creation and management",
            "Real-time availability tracking",
            "Distributed locking for consistency",
            "Audit trail and compliance",
            "Admin management tools"
        ],
        "endpoints": {
            "bookings": "/api/v1/bookings",
            "availability": "/api/v1/availability",
            "admin": "/api/v1/admin",
            "health": "/api/v1/health",
            "docs": "/docs"
        },
        "features": {
            "high_consistency": True,
            "distributed_locking": True,
            "optimistic_concurrency": True,
            "audit_trail": True,
            "caching": True,
            "pagination": True
        }
    }