"""
Monitoring endpoints for the MLOps sentiment analysis service.

This module provides a set of API endpoints for monitoring the health,
performance, and status of the application and its components. These
endpoints are essential for observability and are typically used by monitoring
systems, orchestration platforms (like Kubernetes), and for debugging.
"""
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.api.schemas.responses import (
    AsyncBatchMetricsResponse,
    ComponentHealth,
    DetailedHealthResponse,
    HealthDetail,
    HealthResponse,
    KafkaMetricsResponse,
    MetricsResponse,
)
from app.core.config import Settings, get_settings
from app.core.dependencies import get_model_service
from app.core.logging import get_logger
from app.core.secrets import get_secret_manager
from app.monitoring.health import HealthChecker
from app.services.async_batch_service import AsyncBatchService
from app.utils.error_handlers import handle_prometheus_metrics_error

router = APIRouter()
logger = get_logger(__name__)


async def get_async_batch_service_dependency(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AsyncBatchService:
    """Dependency to get the async batch service instance for monitoring endpoints.

    Args:
        request: The FastAPI request object.
        settings: Application settings.

    Returns:
        The async batch service instance.

    Raises:
        HTTPException: If the service is not available or disabled.
    """
    if not settings.async_batch_enabled:
        raise HTTPException(status_code=404, detail="Async batch processing is disabled")
    if (
        not hasattr(request.app.state, "async_batch_service")
        or not request.app.state.async_batch_service
    ):
        raise HTTPException(status_code=503, detail="Async batch service not initialized")
    return request.app.state.async_batch_service


@router.get(
    "/health/details",
    response_model=DetailedHealthResponse,
    summary="Detailed service health check",
    description="Provides a detailed health status of the service and its dependencies.",
)
async def detailed_health_check(
    request: Request,
    settings: Settings = Depends(get_settings),
    model=Depends(get_model_service),
    secret_manager=Depends(get_secret_manager),
) -> DetailedHealthResponse:
    """Performs a detailed health check of all major components.

    This endpoint aggregates health information from various parts of the
    system, including the model, system resources, and external dependencies,
    to provide a comprehensive overview of the service's health.

    Args:
        request: The FastAPI request object.
        settings: Application settings.
        model: The ML model service.
        secret_manager: The secret management service.

    Returns:
        A `DetailedHealthResponse` with the overall status and a breakdown
        of each component's health.
    """
    health_checker = HealthChecker()
    checks = {
        "model": health_checker.check_model_health(model),
        "system": health_checker.check_system_health(),
        "secrets_backend": health_checker.check_secrets_backend_health(secret_manager),
    }
    # Optional components
    if settings.kafka_enabled:
        checks["kafka"] = health_checker.check_kafka_health(
            getattr(request.app.state, "kafka_consumer", None)
        )
    if settings.async_batch_enabled:
        checks["async_batch"] = health_checker.check_async_batch_health(
            getattr(request.app.state, "async_batch_service", None)
        )

    overall_status = "healthy"
    dependencies = []
    for name, result in checks.items():
        status = result.get("status", "unhealthy")
        if status != "healthy":
            overall_status = "unhealthy"
        dependencies.append(
            ComponentHealth(
                component_name=name, details=HealthDetail(status=status, error=result.get("error"))
            )
        )

    return DetailedHealthResponse(
        status=overall_status,
        version=settings.app_version,
        timestamp=time.time(),
        dependencies=dependencies,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Provides a high-level health status of the service, suitable for liveness probes.",
)
async def health_check(
    model=Depends(get_model_service),
    secret_manager=Depends(get_secret_manager),
) -> HealthResponse:
    """Performs a high-level health check of the service.

    This endpoint checks the basic readiness of the service, primarily focusing
    on the model's availability. It's intended for use as a liveness probe in
    orchestration systems like Kubernetes.

    Args:
        model: The ML model service.
        secret_manager: The secret management service.

    Returns:
        A `HealthResponse` indicating the overall status of the service.
    """
    model_ready = model.is_ready()
    secrets_healthy = secret_manager.is_healthy()
    status = "healthy" if model_ready and secrets_healthy else "unhealthy"
    return HealthResponse(status=status, model_status="available" if model_ready else "unavailable")


@router.get(
    "/ready",
    summary="Readiness check",
    description="Checks if the service is ready to accept traffic, suitable for readiness probes.",
)
async def readiness_check(model=Depends(get_model_service)):
    """Checks if the service is fully initialized and ready to accept traffic.

    This endpoint is intended for use as a readiness probe in Kubernetes. It
    verifies that the machine learning model is loaded and ready for inference.

    Args:
        model: The ML model service.

    Returns:
        A dictionary with a "ready" status if the service is ready.

    Raises:
        ServiceUnavailableError: If the model is not ready, returning a 503 status.
    """
    if not model.is_ready():
        from app.utils.exceptions import ServiceUnavailableError

        raise ServiceUnavailableError("Model not ready for inference.")
    return {"status": "ready"}


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Exposes performance and health metrics in Prometheus format.",
)
async def get_prometheus_metrics(settings: Settings = Depends(get_settings)):
    """Exposes application and model metrics in Prometheus format.

    This endpoint is designed to be scraped by a Prometheus server for
    monitoring and alerting. It provides a wide range of metrics, including
    request counts, latencies, and model-specific performance indicators.

    Args:
        settings: Application settings.

    Returns:
        A `Response` object with the metrics in Prometheus text format.
    """
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")
    try:
        from app.monitoring.prometheus import get_metrics

        metrics = get_metrics()
        return Response(
            content=metrics.get_metrics(), media_type=metrics.get_metrics_content_type()
        )
    except Exception as e:
        handle_prometheus_metrics_error(e)


@router.get(
    "/metrics-json",
    response_model=MetricsResponse,
    summary="Service metrics (JSON)",
    description="Provides performance metrics in JSON format (legacy endpoint).",
)
async def get_metrics_json(model=Depends(get_model_service)):
    """Provides service and model performance metrics in JSON format.

    This endpoint serves as an alternative to the Prometheus metrics endpoint,
    providing a structured JSON response with key performance indicators.

    Args:
        model: The ML model service.

    Returns:
        A `MetricsResponse` object with performance metrics.
    """
    try:
        return MetricsResponse(**model.get_performance_metrics())
    except Exception as e:
        logger.error(f"Error retrieving JSON metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get(
    "/kafka-metrics",
    response_model=KafkaMetricsResponse,
    summary="Kafka consumer metrics",
    description="Provides detailed metrics about the Kafka consumer's performance.",
)
async def get_kafka_metrics(request: Request, settings: Settings = Depends(get_settings)):
    """Retrieves detailed metrics about the Kafka consumer's performance.

    Args:
        request: The FastAPI request object.
        settings: Application settings.

    Returns:
        A `KafkaMetricsResponse` with consumer performance data.
    """
    if not settings.kafka_enabled:
        raise HTTPException(status_code=404, detail="Kafka consumer is disabled")
    consumer = getattr(request.app.state, "kafka_consumer", None)
    if not consumer:
        raise HTTPException(status_code=503, detail="Kafka consumer not initialized")
    return KafkaMetricsResponse(**consumer.get_metrics())


@router.get(
    "/async-batch-metrics",
    response_model=AsyncBatchMetricsResponse,
    summary="Async batch processing metrics",
    description="Provides comprehensive metrics for the async batch processing service.",
)
async def get_async_batch_metrics(
    async_batch_service: AsyncBatchService = Depends(get_async_batch_service_dependency),
):
    """Retrieves performance metrics for the asynchronous batch processing service.

    Args:
        async_batch_service: The async batch service dependency.

    Returns:
        An `AsyncBatchMetricsResponse` with detailed batch processing metrics.
    """
    try:
        return await async_batch_service.get_batch_metrics()
    except Exception as e:
        logger.error(f"Error retrieving async batch metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


# Import and include the new monitoring routes for advanced features
from app.api.routes.monitoring_routes import router as advanced_monitoring_router

# Note: The advanced monitoring router is included here for backwards compatibility
# It provides additional endpoints for drift detection, MLflow registry, explainability, and advanced KPIs
