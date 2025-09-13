"""
Application entrypoint for the MLOps sentiment analysis service.

This module serves as the main application factory and lifecycle manager,
handling FastAPI app creation, middleware setup, and graceful shutdown.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings
from .api import router
from .ml.sentiment import get_sentiment_analyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a correlation ID to each request/response cycle.

    This helps in tracing requests across services and logging systems.

    Attributes:
        correlation_id_header (str): The name of the header used for the correlation ID
    """

    correlation_id_header: str = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and add the correlation ID to the response.

        Args:
            request (Request): The incoming request
            call_next: The next middleware or endpoint to process the request

        Returns:
            Response: The response with the correlation ID header added
        """
        correlation_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers[self.correlation_id_header] = correlation_id
        return response


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

    # Add correlation ID middleware
    app.add_middleware(CorrelationIDMiddleware)

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
