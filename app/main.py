"""
Application entrypoint for the MLOps sentiment analysis service.

This module serves as the main application factory and lifecycle manager,
handling FastAPI app creation, middleware setup, and graceful shutdown. It
initializes the FastAPI application, configures middleware for logging,
CORS, authentication, and metrics, sets up a global exception handler,
and includes the API routers.
"""

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.api.middleware import (
    APIKeyAuthMiddleware,
    CorrelationIdMiddleware,
    MetricsMiddleware,
    RequestLoggingMiddleware,
)
from app.core.config import get_settings
from app.core.events import lifespan
from app.core.logging import get_logger, setup_structured_logging
from app.core.tracing import setup_tracing, instrument_fastapi_app
from app.monitoring.routes import router as monitoring_router
from app.utils.exceptions import ServiceError

# Setup structured logging
setup_structured_logging()
logger = get_logger(__name__)

# Setup distributed tracing
setup_tracing()


def create_app() -> FastAPI:
    """Creates and configures a FastAPI application instance.

    This factory function initializes the FastAPI application, sets up middleware,
    registers routers, and defines event handlers. It centralizes the
    application's construction, making it easier to manage and test. The
    middleware is configured in a specific order to ensure that correlation IDs
    and logging are available for all requests.

    Returns:
        The configured FastAPI application instance.
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

    # Add correlation ID middleware (first to ensure all logs have correlation ID)
    app.add_middleware(CorrelationIdMiddleware)

    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Add CORS middleware to allow cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add API key auth middleware for securing endpoints
    app.add_middleware(APIKeyAuthMiddleware)

    # Add metrics middleware for Prometheus monitoring
    try:
        app.add_middleware(MetricsMiddleware)
        logger.info("Prometheus metrics middleware enabled")
    except Exception as e:
        logger.warning(f"Prometheus metrics not available: {e}")

    # Instrument FastAPI for distributed tracing
    try:
        instrument_fastapi_app(app)
        logger.info("Distributed tracing instrumentation enabled")
    except Exception as e:
        logger.warning(f"Distributed tracing not available: {e}")

    # Global exception handler for unhandled errors
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception) -> JSONResponse:
        """Handles unexpected exceptions across the application.

        This global handler catches any unhandled exceptions, logs them, and
        returns a standardized JSON error response. It distinguishes between
        custom `ServiceError` exceptions, which have a defined status code and
        error code, and other unexpected errors, which are treated as 500
        Internal Server Errors.

        Args:
            request: The incoming request that caused the exception.
            exc: The exception instance that was raised.

        Returns:
            A JSONResponse containing the error details.
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
    app.include_router(
        monitoring_router,
        prefix="/api/v1" if not settings.debug else "",
        tags=["Monitoring"],
    )

    # Add root endpoint
    @app.get("/", tags=["root"])
    async def root() -> dict:
        """Provides basic service information at the root endpoint.

        This endpoint serves as a simple health check and provides metadata
        about the service, such as its name, version, and links to the
        documentation and health check endpoints.

        Returns:
            A dictionary containing service information.
        """
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "operational",
            "docs_url": "/docs" if settings.debug else "disabled",
            "health_url": "/health" if settings.debug else "/api/v1/health",
        }

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    """
    Development server entry point.

    This script is intended for local development only and should not be used
    to run the application in a production environment. For production, use a
    proper ASGI server like Gunicorn or Uvicorn with multiple worker processes.
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
