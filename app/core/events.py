"""
Application lifecycle event handlers for the MLOps sentiment analysis service.

This module defines the startup and shutdown logic for the application,
ensuring that resources such as machine learning models, Kafka consumers, and
batch processing services are properly initialized and gracefully terminated.
"""

import asyncio
from contextlib import asynccontextmanager
import signal
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SHUTDOWN_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def _handle_shutdown_signal(app: FastAPI, sig: signal.Signals) -> None:
    """Trigger an early graceful shutdown when a termination signal is received."""
    shutdown_event = getattr(app.state, "shutdown_event", None)
    if shutdown_event and not shutdown_event.is_set():
        shutdown_event.set()

    # Avoid spawning duplicate drain tasks
    if getattr(app.state, "_shutdown_draining", False):
        return

    try:
        loop = asyncio.get_running_loop()
        app.state.shutdown_task = loop.create_task(
            _shutdown_services(app, reason=f"signal:{sig.name}")
        )
    except RuntimeError:
        logger.error("No running event loop to handle shutdown signal", signal=sig.name)


def _register_signal_handlers(app: FastAPI) -> None:
    """Register SIGTERM/SIGINT handlers so we can start draining immediately."""
    app.state.shutdown_event = asyncio.Event()
    app.state._shutdown_draining = False
    app.state.shutdown_task = None

    try:
        loop = asyncio.get_running_loop()
        for sig in SHUTDOWN_SIGNALS:
            loop.add_signal_handler(
                sig,
                lambda s=sig: _handle_shutdown_signal(app, s),
            )
    except (RuntimeError, NotImplementedError):
        # Fallback for environments where add_signal_handler is unsupported
        for sig in SHUTDOWN_SIGNALS:
            try:
                signal.signal(sig, lambda *_: _handle_shutdown_signal(app, sig))
            except Exception as exc:
                logger.warning("Failed to register signal handler", signal=sig.name, error=str(exc))


async def _shutdown_services(app: FastAPI, reason: str) -> None:
    """Stop background services safely; idempotent to handle repeated triggers."""
    if getattr(app.state, "_shutdown_draining", False):
        return

    if getattr(app.state, "shutdown_task", None) is None:
        app.state.shutdown_task = asyncio.current_task()

    app.state._shutdown_draining = True
    shutdown_event = getattr(app.state, "shutdown_event", None)
    if shutdown_event and not shutdown_event.is_set():
        shutdown_event.set()

    logger.info("Application shutdown initiated", reason=reason)

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

    if hasattr(app.state, "feedback_service") and app.state.feedback_service:
        try:
            await app.state.feedback_service.stop()
            logger.info("Feedback service stopped successfully")
        except Exception as e:
            logger.error("Error stopping feedback service", error=str(e), exc_info=True)

    if hasattr(app.state, "shadow_mode_service") and app.state.shadow_mode_service:
        try:
            await app.state.shadow_mode_service.stop()
            logger.info("Shadow mode service stopped successfully")
        except Exception as e:
            logger.error("Error stopping shadow mode service", error=str(e), exc_info=True)

    logger.info("Application shutdown complete", reason=reason)


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

    # Register shutdown handlers early so SIGTERM from spot interruption starts draining immediately
    _register_signal_handlers(app)

    # Startup logic
    logger.info(
        "Starting application",
        app_name=settings.server.app_name,
        version=settings.server.app_version,
        debug=settings.server.debug,
    )

    # Initialize and warm up the machine learning model
    try:
        from app.models.factory import ModelFactory
        from app.monitoring.model_warmup import get_warmup_manager

        default_backend = "onnx" if settings.model.onnx_model_path else "pytorch"
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
    if settings.mlops.mlflow_enabled:
        try:
            from app.services.mlflow_registry import initialize_model_registry

            registry = initialize_model_registry(
                tracking_uri=settings.mlops.mlflow_tracking_uri,
                enabled=settings.mlops.mlflow_enabled,
            )
            logger.info("MLflow Model Registry initialized")
            app.state.model_registry = registry
        except Exception as e:
            logger.error("MLflow initialization failed", error=str(e), exc_info=True)

    # Initialize Drift Detection
    if settings.mlops.drift_detection_enabled:
        try:
            from app.services.drift_detection import initialize_drift_detector

            drift_detector = initialize_drift_detector(
                window_size=settings.mlops.drift_window_size,
                psi_threshold=settings.mlops.drift_psi_threshold,
                enabled=settings.mlops.drift_detection_enabled,
            )
            logger.info("Drift Detection initialized")
            app.state.drift_detector = drift_detector
        except Exception as e:
            logger.error("Drift detection initialization failed", error=str(e), exc_info=True)

    # Initialize Explainability Engine
    if settings.mlops.explainability_enabled:
        try:
            from app.services.explainability import initialize_explainability_engine

            explainer = initialize_explainability_engine(
                model=model if "model" in locals() else None,
                model_name=settings.model.model_name,
                enabled=settings.mlops.explainability_enabled,
            )
            logger.info("Explainability Engine initialized")
            app.state.explainability_engine = explainer
        except Exception as e:
            logger.error("Explainability engine initialization failed", error=str(e), exc_info=True)

    # Initialize Shadow Mode Service
    if settings.mlops.shadow_mode_enabled:
        try:
            from app.services.shadow_mode import initialize_shadow_mode_service

            shadow_service = initialize_shadow_mode_service(
                settings=settings,
                primary_model=model if "model" in locals() else None,
            )
            await shadow_service.start()
            app.state.shadow_mode_service = shadow_service
            logger.info(
                "Shadow Mode Service initialized",
                shadow_model=settings.mlops.shadow_model_name,
                traffic_percentage=settings.mlops.shadow_traffic_percentage,
            )
        except Exception as e:
            logger.error("Shadow mode service initialization failed", error=str(e), exc_info=True)

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
    if settings.kafka.kafka_enabled:
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
        from app.features.feature_engineering import get_feature_engineer

        # Initialize feature engineer with NLTK download controlled by settings
        # Only download if feature engineering is enabled to save startup time
        feature_engineer = get_feature_engineer(
            download_nltk_data=settings.model.enable_feature_engineering
        )
        prediction_svc = PredictionService(model, settings, feature_engineer)
        stream_processor = StreamProcessor(model)
        async_batch_service = AsyncBatchService(prediction_svc, stream_processor)
        await async_batch_service.start()
        app.state.async_batch_service = async_batch_service
        logger.info("Async batch service started successfully")

    except Exception as e:
        logger.error("Async batch service initialization failed", error=str(e), exc_info=True)

    # Initialize and start the data lake writer
    if settings.data_lake.data_lake_enabled:
        try:
            from app.services.data_writer import get_data_writer

            data_writer = get_data_writer(settings)
            await data_writer.start()
            app.state.data_writer = data_writer
            logger.info(
                "Data lake writer started successfully",
                provider=settings.data_lake.data_lake_provider,
                bucket=settings.data_lake.data_lake_bucket,
            )

        except Exception as e:
            logger.error("Data lake writer initialization failed", error=str(e), exc_info=True)

    # Initialize and start the feedback service
    try:
        from app.services.feedback_service import get_feedback_service

        feedback_service = get_feedback_service(settings)
        await feedback_service.start()
        app.state.feedback_service = feedback_service
        logger.info("Feedback service started successfully")

    except Exception as e:
        logger.error("Feedback service initialization failed", error=str(e), exc_info=True)

    logger.info("Application startup complete")

    yield

    # Shutdown logic
    shutdown_task = getattr(app.state, "shutdown_task", None)
    if shutdown_task and not shutdown_task.done():
        await shutdown_task
    else:
        await _shutdown_services(app, reason="lifespan_exit")
