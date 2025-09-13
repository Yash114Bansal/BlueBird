"""
Main FastAPI application for Analytics Service.
Entry point for the analytics microservice.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .core.config import config
from .api.v1.router import router as v1_router
from .models.analytics import Base
from .api.dependencies import db_connection, redis_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Analytics Service...")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        database_url = await config.get_database_url()
        logger.info(f"Database URL: {database_url}")
        db_connection.initialize(database_url)
        
        # Create tables
        logger.info("Creating database tables...")
        db_connection.get_manager().create_tables()
        logger.info("Analytics database initialized successfully")
        
        # Initialize Redis
        logger.info("Initializing Redis...")
        redis_url = await config.get_redis_url()
        logger.info(f"Redis URL: {redis_url}")
        redis_connection.initialize(redis_url)
        
        # Test Redis connection with ping
        redis_manager = redis_connection.get_manager()
        await redis_manager.initialize()
        ping_result = await redis_manager.redis_client.ping()
        if not ping_result:
            raise Exception("Redis ping failed")
        logger.info("Redis initialized and ping successful")
        
        # Start event subscriber
        logger.info("Starting event subscriber...")
        from .services.event_subscriber import EventSubscriber
        db_manager = db_connection.get_manager()
        redis_manager = redis_connection.get_manager()
        event_subscriber = EventSubscriber(db_manager, redis_manager)
        await event_subscriber.start()
        logger.info("Event subscriber started successfully")
        
        logger.info("Analytics Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Analytics Service: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Analytics Service...")
    
    try:
        # Stop event subscriber
        logger.info("Stopping event subscriber...")
        from .services.event_subscriber import EventSubscriber
        db_manager = db_connection.get_manager()
        redis_manager = redis_connection.get_manager()
        event_subscriber = EventSubscriber(db_manager, redis_manager)
        await event_subscriber.stop()
        logger.info("Event subscriber stopped")
        
        # Close Redis connection
        redis_manager = redis_connection.get_manager()
        await redis_manager.close()
        logger.info("Redis connection closed")
        
        # Close config connections
        await config.close()
        logger.info("Config connections closed")
        
        logger.info("Analytics Service shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Evently Analytics Service",
    description="Analytics and reporting microservice for Evently platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
@app.middleware("http")
async def add_cors_headers(request, call_next):
    """Add CORS headers to all responses."""
    response = await call_next(request)
    
    # Get allowed origins from config
    try:
        origins = await config.get_cors_origins()
        origin = request.headers.get("origin")
        
        if origin in origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
    except Exception as e:
        logger.warning(f"Failed to set CORS headers: {e}")
    
    return response

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # In production, specify actual hosts
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "success": False
        }
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Service health status
    """
    try:
        # Check database connection
        db_manager = db_connection.get_manager()
        session = db_manager.SessionLocal()
        try:
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
        finally:
            session.close()
        
        # Check Redis connection
        redis_manager = redis_connection.get_manager()
        await redis_manager.initialize()
        await redis_manager.redis_client.ping()
        
        return {
            "status": "healthy",
            "service": "analytics-service",
            "version": "1.0.0",
            "database": "connected",
            "redis": "connected"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "analytics-service",
                "version": "1.0.0",
                "error": str(e)
            }
        )

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    
    Returns:
        Service information
    """
    return {
        "service": "Evently Analytics Service",
        "version": "1.0.0",
        "description": "Analytics and reporting microservice for Evently platform",
        "docs": "/docs",
        "health": "/health"
    }

# Service information endpoint
@app.get("/info", tags=["Info"])
async def service_info():
    """
    Service information endpoint.
    
    Returns:
        Detailed service information
    """
    return {
        "service": "analytics-service",
        "version": "1.0.0",
        "description": "Analytics and reporting microservice for Evently platform",
        "endpoints": {
            "analytics": "/api/v1/analytics",
            "health": "/health",
            "docs": "/docs"
        },
        "features": [
            "Real-time analytics dashboard",
            "Event-driven data aggregation",
            "Booking trends and patterns",
            "Revenue analytics",
            "Capacity utilization tracking",
            "Top events ranking",
            "Daily analytics reports",
            "Admin-only access control",
            "Redis caching for performance",
            "Rate limiting protection"
        ],
        "architecture": {
            "type": "Event-driven microservice",
            "database": "PostgreSQL with optimized analytics tables",
            "cache": "Redis for performance optimization",
            "authentication": "JWT token validation via auth service",
            "event_processing": "Real-time event subscription and aggregation"
        }
    }

# Include API routers
app.include_router(v1_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )