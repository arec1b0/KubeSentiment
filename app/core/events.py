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

        # Store model in app state
        app.state.model = model

    except Exception as e:
        logger.error("Model initialization failed", error=str(e), exc_info=True)

    # Initialize MLflow Model Registry
    if settings.mlflow_enabled:
        try:
            from app.services.mlflow_registry import initialize_model_registry

            registry = initialize_model_registry(
                tracking_uri=settings.mlflow_tracking_uri, enabled=settings.mlflow_enabled
            )
            logger.info("MLflow Model Registry initialized")
            app.state.model_registry = registry
        except Exception as e:
            logger.error("MLflow initialization failed", error=str(e), exc_info=True)

    # Initialize Drift Detection
    if settings.drift_detection_enabled:
        try:
            from app.services.drift_detection import initialize_drift_detector

            drift_detector = initialize_drift_detector(
                window_size=settings.drift_window_size,
                psi_threshold=settings.drift_psi_threshold,
                enabled=settings.drift_detection_enabled,
            )
            logger.info("Drift Detection initialized")
            app.state.drift_detector = drift_detector
        except Exception as e:
            logger.error("Drift detection initialization failed", error=str(e), exc_info=True)

    # Initialize Explainability Engine
    if settings.explainability_enabled:
        try:
            from app.services.explainability import initialize_explainability_engine

            explainer = initialize_explainability_engine(
                model=model if "model" in locals() else None,
                model_name=settings.model_name,
                enabled=settings.explainability_enabled,
            )
            logger.info("Explainability Engine initialized")
            app.state.explainability_engine = explainer
        except Exception as e:
            logger.error("Explainability engine initialization failed", error=str(e), exc_info=True)

    # Initialize Advanced Metrics Collector
    if settings.advanced_metrics_enabled:
        try:
            from app.monitoring.advanced_metrics import initialize_advanced_metrics_collector

            metrics_collector = initialize_advanced_metrics_collector(
                enable_detailed_tracking=settings.advanced_metrics_detailed_tracking,
                cost_per_1k_predictions=settings.advanced_metrics_cost_per_1k,
            )
            logger.info("Advanced Metrics Collector initialized")
            app.state.metrics_collector = metrics_collector
        except Exception as e:
            logger.error("Advanced metrics initialization failed", error=str(e), exc_info=True)

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

    # Initialize and start the data lake writer
    if settings.data_lake_enabled:
        try:
            from app.services.data_writer import get_data_writer

            data_writer = get_data_writer(settings)
            await data_writer.start()
            app.state.data_writer = data_writer
            logger.info(
                "Data lake writer started successfully",
                provider=settings.data_lake_provider,
                bucket=settings.data_lake_bucket,
            )

        except Exception as e:
            logger.error("Data lake writer initialization failed", error=str(e), exc_info=True)

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

    if hasattr(app.state, "data_writer") and app.state.data_writer:
        try:
            await app.state.data_writer.stop()
            logger.info("Data lake writer stopped successfully")
        except Exception as e:
            logger.error("Error stopping data lake writer", error=str(e), exc_info=True)

    logger.info("Application shutdown complete")
