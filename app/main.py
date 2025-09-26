"""
Application entrypoint for the MLOps sentiment analysis service.

This module serves as the main application factory and lifecycle manager,
handling FastAPI app creation, middleware setup, and graceful shutdown.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings
from .api import router
from .ml.sentiment import get_sentiment_analyzer
from .logging_config import setup_structured_logging, get_logger
from .exceptions import ServiceError
from .middleware import APIKeyAuthMiddleware

# Setup structured logging
setup_structured_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for proper resource management.

    Args:
        app: The FastAPI application instance

    Yields:
        None: Control during the application lifetime
    """
    settings = get_settings()

    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize the sentiment analyzer (loads the model)
    analyzer = get_sentiment_analyzer()
    if analyzer.is_ready():
        logger.info("Sentiment analysis model loaded successfully")
    else:
        logger.warning(
            "Sentiment analysis model failed to load - running in degraded mode"
        )

    # Application is ready
    logger.info(
        f"Application startup complete. Listening on {settings.host}:{settings.port}"
    )

    yield

    # Shutdown
    logger.info("Application shutdown initiated")
    # Add any cleanup logic here if needed
    logger.info("Application shutdown complete")



def create_app() -> FastAPI:
    """
    Application factory function.

    Creates and configures the FastAPI application with all necessary
    middleware, routers, and event handlers.

    Returns:
        FastAPI: The configured application instance
    """
    settings = get_settings()

    # Create FastAPI app with lifespan management
    app = FastAPI(
        title=settings.app_name,
        description="A production-ready microservice for sentiment analysis using transformer models.",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler for unhandled errors
    @app.exception_handler(Exception)
    async def global_exception_handler(exc: Exception) -> JSONResponse:
        """
        Global exception handler for unhandled errors.

        Logs the error and returns a generic error response.

        Args:
            exc: The exception that was raised

        Returns:
            JSONResponse: Error response
        """
        # Map known service errors to their status codes
        if isinstance(exc, ServiceError):
            logger.warning(f"Service error occurred: {exc}", exc_info=False)
            return JSONResponse(
                status_code=getattr(exc, "status_code", 400),
                content={
                    "detail": str(exc),
                    "error_code": getattr(exc, "code", "E0000"),
                    "context": getattr(exc, "context", None),
                },
            )

        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_id": f"error_{int(time.time())}",
            },
        )

    # Include API router
    app.include_router(router, prefix="/api/v1" if not settings.debug else "")

    # Add root endpoint
    @app.get("/", tags=["root"])
    async def root() -> dict:
        """
        Root endpoint providing basic service information.

        Returns:
            dict: Service information
        """
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "operational",
            "docs_url": "/docs" if settings.debug else "disabled",
            "health_url": "/health" if settings.debug else "/api/v1/health",
        }

    # Note: Correlation ID handling is now managed via contextvars in the logging system

    # Add API key auth middleware (no-op if api_key not configured)
    app.add_middleware(APIKeyAuthMiddleware)

    # Add metrics middleware
    try:
        from .monitoring import MetricsMiddleware

        app.add_middleware(MetricsMiddleware)
        logger.info("Prometheus metrics middleware enabled")
    except ImportError as e:
        logger.warning(f"Prometheus metrics not available: {e}")

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    """
    Development server entry point.

    This should only be used for local development.
    For production, use a proper ASGI server like uvicorn or gunicorn.
    """
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=1 if settings.debug else settings.workers,
    )
