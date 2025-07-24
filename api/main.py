"""ClipVault Public API - Main FastAPI application."""

import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import auth service and routes
from api.services.auth import init_auth_service, shutdown_auth_service
from api.services.supabase import init_database_service, shutdown_database_service
from api.services.pubsub import init_pubsub_service, shutdown_pubsub_service
from api.routes import auth

# Configure structured logging for production
def configure_logging():
    """Configure structured logging for Cloud Run."""
    log_level = os.getenv("LOG_LEVEL", "info").upper()
    
    # Configure structlog for Cloud Run compatible JSON logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set log level
    import logging
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        stream=sys.stdout,
        format="%(message)s"
    )

# Initialize logging
configure_logging()
logger = structlog.get_logger()


class HealthResponse(BaseModel):
    """Health check response model."""
    pong: bool
    environment: str
    version: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    environment = os.getenv("ENVIRONMENT", "development")
    logger.info(
        "Starting ClipVault Public API",
        environment=environment,
        python_version=sys.version.split()[0],
        port=os.getenv("PORT", "8000")
    )

    # Initialize auth service
    try:
        await init_auth_service()
        logger.info("Auth service initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize auth service", error=str(e))
        # Continue startup - auth service can be initialized on first request

    # Initialize database service
    try:
        await init_database_service()
        logger.info("Database service initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database service", error=str(e))
        logger.warning("Starting API without database - some features will be limited")
        # Continue startup - we can still serve auth and health endpoints

    # Initialize Pub/Sub service
    try:
        await init_pubsub_service()
        logger.info("Pub/Sub service initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize Pub/Sub service", error=str(e))
        logger.warning("Starting API without Pub/Sub - clip events will not be published")
        # Continue startup - clip ingestion can work without events

    # TODO: Initialize database connections, Redis, etc.
    # Example:
    # try:
    #     await initialize_database()
    #     await initialize_redis()
    #     logger.info("Database and Redis connections initialized")
    # except Exception as e:
    #     logger.error("Failed to initialize connections", error=str(e))
    #     raise

    yield

    # Shutdown
    logger.info("Shutting down ClipVault Public API")
    
    # Cleanup auth service
    try:
        await shutdown_auth_service()
        logger.info("Auth service shut down successfully")
    except Exception as e:
        logger.error("Error shutting down auth service", error=str(e))
    
    # Cleanup database service
    try:
        await shutdown_database_service()
        logger.info("Database service shut down successfully")
    except Exception as e:
        logger.error("Error shutting down database service", error=str(e))
    
    # Cleanup Pub/Sub service
    try:
        await shutdown_pubsub_service()
        logger.info("Pub/Sub service shut down successfully")
    except Exception as e:
        logger.error("Error shutting down Pub/Sub service", error=str(e))
    
    # TODO: Close database connections, Redis, etc.
    # await close_database()
    # await close_redis()


# Create FastAPI application with Cloud Run optimizations
app = FastAPI(
    title="ClipVault Public API",
    description="Public API for ClipVault MVP - link ingestion, search, and collections",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    # Disable docs in production for security (uncomment if needed)
    # docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs",
    # redoc_url=None if os.getenv("ENVIRONMENT") == "production" else "/redoc",
)

# Configure CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(auth.router)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all HTTP requests with structured logging."""
    import time
    
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time_ms=round(process_time * 1000, 2),
        client_ip=request.client.host if request.client else None,
    )
    
    return response


@app.get("/ping", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint for Cloud Run."""
    logger.debug("Health check requested")
    return HealthResponse(
        pong=True,
        environment=os.getenv("ENVIRONMENT", "development"),
        version="0.1.0"
    )


@app.get("/health", tags=["Health"])
async def detailed_health_check():
    """Detailed health check including database and Pub/Sub status."""
    from api.services.database import get_database
    from api.services.pubsub import get_pubsub_service
    
    try:
        db = await get_database()
        db_health = await db.health_check()
        
        # Check Pub/Sub service health
        try:
            pubsub = get_pubsub_service()
            pubsub_health = await pubsub.health_check()
        except RuntimeError:
            # Service not initialized
            pubsub_health = {"status": "not_initialized", "error": "Service not initialized"}
        except Exception as e:
            pubsub_health = {"status": "unhealthy", "error": str(e)}
        
        # Overall health status
        overall_status = "healthy"
        if db_health.get("status") != "healthy" or pubsub_health.get("status") != "healthy":
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "version": "0.1.0",
            "services": {
                "api": "healthy",
                "database": db_health,
                "pubsub": pubsub_health
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "environment": os.getenv("ENVIRONMENT", "development"), 
            "version": "0.1.0",
            "services": {
                "api": "healthy",
                "database": {"status": "unhealthy", "error": str(e)},
                "pubsub": {"status": "unknown", "error": "Could not check due to database error"}
            }
        }


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Root endpoint - redirects to docs."""
    return {
        "message": "ClipVault Public API",
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "docs": "/docs",
        "health": "/ping"
    }


# Add a simple endpoint to test auth (shortcut access to /me)
@app.get("/me", include_in_schema=False)
async def me_shortcut():
    """Shortcut to /auth/me - convenience for testing."""
    from fastapi import Depends
    from api.services.auth import get_current_user
    from api.schemas.auth import UserProfile
    from api.routes.auth import get_me
    
    # This just redirects to the actual /auth/me endpoint
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/auth/me", status_code=307)


# Error handlers for better production error handling
@app.exception_handler(500)
async def internal_server_error(request: Request, exc: Exception):
    """Handle internal server errors."""
    logger.error(
        "Internal server error",
        error=str(exc),
        url=str(request.url),
        method=request.method,
        exc_info=True
    )
    return {"error": "Internal server error", "status_code": 500}


@app.exception_handler(404)
async def not_found_error(request: Request, exc: Exception):
    """Handle not found errors."""
    logger.warning(
        "Endpoint not found",
        url=str(request.url),
        method=request.method,
    )
    return {"error": "Endpoint not found", "status_code": 404}


if __name__ == "__main__":
    import uvicorn

    # Get port from environment (Cloud Run sets PORT environment variable)
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        # Cloud Run specific optimizations
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
