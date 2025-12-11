"""
Application entrypoint for the MLOps sentiment analysis service.

This module serves as the main application factory and lifecycle manager,
handling FastAPI app creation, middleware setup, and graceful shutdown. It
initializes the FastAPI application, configures middleware for logging,
CORS, authentication, and metrics, sets up a global exception handler,
and includes the API routers.
"""

import time
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

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
        title=settings.server.app_name,
        description="A production-ready microservice for sentiment analysis using transformer models.",
        version=settings.server.app_version,
        debug=settings.server.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.server.debug else None,
        redoc_url="/redoc" if settings.server.debug else None,
        default_response_class=ORJSONResponse,
    )

    # Add correlation ID middleware (first to ensure all logs have correlation ID)
    app.add_middleware(CorrelationIdMiddleware)

    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Add CORS middleware to allow cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.allowed_origins,
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

    # Handler for Pydantic validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        """Handles FastAPI/Pydantic request validation errors.

        This handler provides detailed error information about validation failures,
        making it easier for API clients to understand what went wrong with their request.

        Args:
            request: The incoming request that failed validation.
            exc: The validation error instance.

        Returns:
            A ORJSONResponse with detailed validation error information.
        """
        correlation_id = getattr(request.state, "correlation_id", None)

        error_details = []
        for error in exc.errors():
            error_details.append(
                {
                    "loc": error["loc"],
                    "msg": error["msg"],
                    "type": error["type"],
                }
            )

        logger.warning(
            "Request validation failed",
            correlation_id=correlation_id,
            errors=error_details,
            path=request.url.path,
        )

        return ORJSONResponse(
            status_code=422,
            content={
                "error_code": "E1001",
                "error_message": "Request validation failed",
                "detail": "The request data failed validation. Please check the errors below.",
                "validation_errors": error_details,
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    # Global exception handler for unhandled errors
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
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
            A ORJSONResponse containing the error details.
        """
        # Extract correlation ID if available
        correlation_id = getattr(request.state, "correlation_id", None)

        # Map known service errors to their status codes
        if isinstance(exc, ServiceError):
            status_code = getattr(exc, "status_code", 500)
            error_code = getattr(exc, "code", "E0000")
            context = getattr(exc, "context", None)

            logger.warning(
                f"Service error occurred: {exc}",
                error_code=error_code,
                status_code=status_code,
                correlation_id=correlation_id,
                path=request.url.path,
                exc_info=False,
            )

            response_content = {
                "error_code": error_code,
                "error_message": str(exc),
                "status_code": status_code,
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Only include context if it exists and is not None
            if context:
                response_content["context"] = context

            return ORJSONResponse(
                status_code=status_code,
                content=response_content,
            )

        # Handle unexpected errors
        error_id = f"error_{int(time.time())}_{id(exc)}"
        logger.error(
            f"Unhandled exception: {exc}",
            error_id=error_id,
            correlation_id=correlation_id,
            path=request.url.path,
            exc_info=True,
        )

        return ORJSONResponse(
            status_code=500,
            content={
                "error_code": "E4001",
                "error_message": "An unexpected internal server error occurred",
                "status_code": 500,
                "error_id": error_id,
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    # Include API router
    app.include_router(router, prefix="/api/v1" if not settings.server.debug else "")

    # Include monitoring routes (Unified)
    from app.api.routes.monitoring_routes import router as monitoring_router
    
    app.include_router(
        monitoring_router,
        prefix="/api/v1" if not settings.server.debug else "",
        tags=["Monitoring"],
    )

    # Include feedback routes
    from app.api.routes.feedback import router as feedback_router

    app.include_router(
        feedback_router,
        prefix="/api/v1" if not settings.server.debug else "",
        tags=["Feedback"],
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
            "service": settings.server.app_name,
            "version": settings.server.app_version,
            "status": "operational",
            "docs_url": "/docs" if settings.server.debug else "disabled",
            "health_url": "/health" if settings.server.debug else "/api/v1/health",
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
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.debug,
        log_level=settings.monitoring.log_level.lower(),
        workers=1 if settings.server.debug else settings.server.workers,
    )
