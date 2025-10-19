"""
Application lifecycle events.

This module handles startup and shutdown events for proper resource management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import get_logger

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
    logger.info(
        "Starting application",
        app_name=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # Initialize models
    try:
        from app.models.factory import ModelFactory

        # Pre-load default model
        default_backend = "onnx" if settings.onnx_model_path else "pytorch"
        model = ModelFactory.create_model(default_backend)

        if model.is_ready():
            logger.info("Model loaded successfully", backend=default_backend)
        else:
            logger.warning(
                "Model failed to load - running in degraded mode",
                backend=default_backend,
            )

    except Exception as e:
        logger.error("Model initialization failed", error=str(e), exc_info=True)

    # Application is ready
    logger.info("Application startup complete", host=settings.host, port=settings.port)

    yield

    # Shutdown
    logger.info("Application shutdown initiated")
    # Add any cleanup logic here if needed
    logger.info("Application shutdown complete")

