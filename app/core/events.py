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
    """Manages the application's startup and shutdown events.

    This asynchronous context manager is used by FastAPI to handle application
    lifecycle events. The code before the `yield` statement is executed on
    startup, and the code after is executed on shutdown. It ensures that
    resources like model connections are properly initialized and released.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control back to the application, which runs until it's terminated.
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

    # Initialize Kafka consumer if enabled
    kafka_consumer = None
    if settings.kafka_enabled:
        try:
            from app.services.stream_processor import StreamProcessor
            from app.services.kafka_consumer import HighThroughputKafkaConsumer

            # Create stream processor with the loaded model
            stream_processor = StreamProcessor(model)

            # Create and start Kafka consumer
            kafka_consumer = HighThroughputKafkaConsumer(stream_processor, settings)
            await kafka_consumer.start()

            logger.info(
                "Kafka consumer started successfully",
                topic=settings.kafka_topic,
                consumer_group=settings.kafka_consumer_group,
                threads=settings.kafka_consumer_threads,
            )

        except Exception as e:
            logger.error("Kafka consumer initialization failed", error=str(e), exc_info=True)

    # Store consumer in app state for access by other components
    app.state.kafka_consumer = kafka_consumer

    # Application is ready
    logger.info("Application startup complete", host=settings.host, port=settings.port)

    yield

    # Shutdown
    logger.info("Application shutdown initiated")

    # Shutdown Kafka consumer
    if hasattr(app.state, 'kafka_consumer') and app.state.kafka_consumer:
        try:
            await app.state.kafka_consumer.stop()
            logger.info("Kafka consumer stopped successfully")
        except Exception as e:
            logger.error("Error stopping Kafka consumer", error=str(e), exc_info=True)

    # Add any other cleanup logic here if needed
    logger.info("Application shutdown complete")
