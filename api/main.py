"""ClipVault Public API - Main FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from pydantic import BaseModel

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class HealthResponse(BaseModel):
    """Health check response model."""

    pong: bool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting ClipVault Public API")

    # TODO: Initialize database connections, Redis, etc.

    yield

    # Shutdown
    logger.info("Shutting down ClipVault Public API")

    # TODO: Close database connections, Redis, etc.


# Create FastAPI application
app = FastAPI(
    title="ClipVault Public API",
    description="Public API for ClipVault MVP - link ingestion, search, and collections",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.get("/ping", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    logger.debug("Health check requested")
    return HealthResponse(pong=True)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Root endpoint - redirects to docs."""
    return {
        "message": "ClipVault Public API",
        "docs": "/docs",
        "health": "/ping"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
