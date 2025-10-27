"""
Application lifecycle event handlers for the MLOps sentiment analysis service.

This module defines the startup and shutdown logic for the application,
ensuring that resources such as machine learning models, Kafka consumers, and
batch processing services are properly initialized and gracefully terminated.
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
    startup, and the code after is executed on shutdown. This ensures that
    resources like model connections, background tasks, and service connections
    are properly initialized and released.

    Args:
        app: The FastAPI application instance, which can be used to store state
            (e.g., `app.state.model = model`).

    Yields:
        Control back to the application, which runs until it is terminated.
    """
    settings = get_settings()

    # Startup logic
    logger.info(
        "Starting application",
        app_name=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # Initialize and warm up the machine learning model
    try:
        from app.models.factory import ModelFactory
        from app.monitoring.model_warmup import get_warmup_manager

        default_backend = "onnx" if settings.onnx_model_path else "pytorch"
        model = ModelFactory.create_model(default_backend)

        if model.is_ready():
            logger.info("Model loaded successfully", backend=default_backend)
            warmup_manager = get_warmup_manager()
            warmup_stats = await warmup_manager.warmup_model(model, num_iterations=10)
            logger.info(
                "Model warm-up completed",
                avg_inference_ms=warmup_stats.get("avg_inference_time_ms"),
                p95_inference_ms=warmup_stats.get("p95_inference_time_ms"),
            )
        else:
            logger.warning("Model failed to load", backend=default_backend)

    except Exception as e:
        logger.error("Model initialization failed", error=str(e), exc_info=True)

    # Initialize and start the Kafka consumer if enabled
    if settings.kafka_enabled:
        try:
            from app.services.kafka_consumer import HighThroughputKafkaConsumer
            from app.services.stream_processor import StreamProcessor

            stream_processor = StreamProcessor(model)
            kafka_consumer = HighThroughputKafkaConsumer(stream_processor, settings)
            await kafka_consumer.start()
            app.state.kafka_consumer = kafka_consumer
            logger.info("Kafka consumer started successfully")

        except Exception as e:
            logger.error("Kafka consumer initialization failed", error=str(e), exc_info=True)

    # Initialize and start the async batch service
    try:
        from app.services.async_batch_service import AsyncBatchService
        from app.services.prediction import PredictionService
        from app.services.stream_processor import StreamProcessor

        prediction_svc = PredictionService(model, settings)
        stream_processor = StreamProcessor(model)
        async_batch_service = AsyncBatchService(prediction_svc, stream_processor)
        await async_batch_service.start()
        app.state.async_batch_service = async_batch_service
        logger.info("Async batch service started successfully")

    except Exception as e:
        logger.error("Async batch service initialization failed", error=str(e), exc_info=True)

    logger.info("Application startup complete")

    yield

    # Shutdown logic
    logger.info("Application shutdown initiated")

    if hasattr(app.state, "kafka_consumer") and app.state.kafka_consumer:
        try:
            await app.state.kafka_consumer.stop()
            logger.info("Kafka consumer stopped successfully")
        except Exception as e:
            logger.error("Error stopping Kafka consumer", error=str(e), exc_info=True)

    if hasattr(app.state, "async_batch_service") and app.state.async_batch_service:
        try:
            await app.state.async_batch_service.stop()
            logger.info("Async batch service stopped successfully")
        except Exception as e:
            logger.error("Error stopping async batch service", error=str(e), exc_info=True)

    logger.info("Application shutdown complete")
