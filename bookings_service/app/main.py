"""
Main FastAPI application for Bookings Service.
Handles application startup, middleware, and routing.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import config
from app.db.database import db_manager
from app.db.redis_client import redis_manager
from app.api.v1.router import router as api_router
from app.services.event_subscriber import event_subscriber

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
    logger.info("Starting Bookings Service...")
    
    try:
        # Initialize database
        await db_manager.initialize()
        logger.info("Database manager initialized")
        
        # Initialize Redis
        await redis_manager.initialize()
        logger.info("Redis manager initialized")
        
        # Create database tables (skip if already exist)
        try:
            await db_manager.create_tables()
            logger.info("Database tables created")
        except Exception as e:
            logger.warning(f"Database tables may already exist: {e}")
            # Continue startup even if tables already exist
        
        # Start event subscriber
        await event_subscriber.start()
        logger.info("Event subscriber started")
        
        logger.info("Bookings Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Bookings Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Bookings Service...")
    
    try:
        # Stop event subscriber
        await event_subscriber.stop()
        logger.info("Event subscriber stopped")
        
        # Close database connections
        await db_manager.close()
        logger.info("Database connections closed")
        
        # Close Redis connections
        await redis_manager.close()
        logger.info("Redis connections closed")
        
        logger.info("Bookings Service shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Bookings Service",
    description="High consistency booking management service for Evently",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "error_message": "An internal server error occurred",
            "details": {"exception": str(exc)},
            "timestamp": datetime.now().isoformat()
        }
    )


# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler for FastAPI HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "error_message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )


# Include API router
app.include_router(api_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Bookings Service",
        "version": "1.0.0",
        "status": "running",
        "description": "High consistency booking management service",
        "endpoints": {
            "api": "/api/v1",
            "health": "/api/v1/health",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


# Health check endpoint (simple)
@app.get("/health")
async def simple_health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "bookings"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )