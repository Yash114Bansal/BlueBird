"""
Main FastAPI application for Auth Service.
Entry point for the authentication microservice.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .core.config import config
from .db.database import DatabaseConnection
from .db.redis_client import RedisConnection
from .api.v1.router import router as v1_router
from .models.user import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
db_connection = DatabaseConnection()
redis_connection = RedisConnection()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Auth Service...")
    
    try:
        # Initialize database
        database_url = await config.get_database_url()
        db_connection.initialize(database_url)
        
        # Create tables
        db_connection.get_manager().create_tables()
        logger.info("Database initialized successfully")
        
        # Initialize Redis
        redis_url = await config.get_redis_url()
        redis_connection.initialize(redis_url)
        
        # Test Redis connection with ping
        redis_manager = redis_connection.get_manager()
        ping_result = await redis_manager.redis_client.ping()
        if not ping_result:
            raise Exception("Redis ping failed")
        logger.info("Redis initialized and ping successful")
        
        logger.info("Auth Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Auth Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Auth Service...")
    
    try:
        # Close Redis connection
        redis_manager = redis_connection.get_manager()
        await redis_manager.close()
        logger.info("Redis connection closed")
        
        # Close config connections
        await config.close()
        logger.info("Config connections closed")
        
        logger.info("Auth Service shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Evently Auth Service",
    description="Authentication and authorization microservice for Evently platform",
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
        
        return {
            "status": "healthy",
            "service": "auth-service",
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
                "service": "auth-service",
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
        "service": "Evently Auth Service",
        "version": "1.0.0",
        "description": "Authentication and authorization microservice",
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
        "service": "auth-service",
        "version": "1.0.0",
        "description": "Authentication and authorization microservice for Evently platform",
        "endpoints": {
            "auth": "/v1/auth",
            "admin": "/v1/admin",
            "health": "/health",
            "docs": "/docs"
        },
        "features": [
            "User registration and authentication",
            "JWT token management",
            "Session management",
            "Role-based access control",
            "Password management",
            "Rate limiting",
            "Admin user management"
        ]
    }

# Include API routers
app.include_router(v1_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )