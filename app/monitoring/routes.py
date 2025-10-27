"""
Monitoring endpoints.
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
from app.core.dependencies import get_model_backend, get_model_service
from app.core.logging import get_logger
from app.core.secrets import get_secret_manager
from app.monitoring.health import HealthChecker
from app.services.async_batch_service import AsyncBatchService
from app.utils.error_handlers import (
    handle_prometheus_metrics_error,
)

router = APIRouter()
logger = get_logger(__name__)


async def get_async_batch_service_dependency(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AsyncBatchService:
    """Get the async batch service instance for monitoring endpoints.

    Args:
        request: The FastAPI request object.
        settings: Application settings.

    Returns:
        The async batch service instance.

    Raises:
        HTTPException: If the service is not available.
    """
    if not settings.async_batch_enabled:
        raise HTTPException(status_code=404, detail="Async batch processing is disabled")

    if not hasattr(request.app.state, 'async_batch_service') or not request.app.state.async_batch_service:
        raise HTTPException(status_code=404, detail="Async batch service not initialized")

    return request.app.state.async_batch_service  # type: ignore


@router.get(
    "/health/details",
    response_model=DetailedHealthResponse,
    summary="Detailed service health check",
    description="Get a detailed health status of the service and its dependencies.",
)
async def detailed_health_check(
    request: Request,
    settings: Settings = Depends(get_settings),
    model=Depends(get_model_service),
    secret_manager=Depends(get_secret_manager),
) -> DetailedHealthResponse:
    """Performs a detailed health check of all components."""
    health_checker = HealthChecker()

    checks = {
        "model": health_checker.check_model_health(model),
        "system": health_checker.check_system_health(),
        "secrets_backend": health_checker.check_secrets_backend_health(
            secret_manager
        ),
    }

    # Add Kafka health check if enabled
    if settings.kafka_enabled and hasattr(request.app.state, 'kafka_consumer') and request.app.state.kafka_consumer:
        checks["kafka"] = health_checker.check_kafka_health(request.app.state.kafka_consumer)

    # Add async batch health check if enabled
    if settings.async_batch_enabled and hasattr(request.app.state, 'async_batch_service') and request.app.state.async_batch_service:
        checks["async_batch"] = health_checker.check_async_batch_health(request.app.state.async_batch_service)

    overall_status = "healthy"
    dependencies = []

    for component, result in checks.items():
        status = result.get("status", "unhealthy")
        if status != "healthy":
            overall_status = "unhealthy"

        dependencies.append(
            ComponentHealth(
                component_name=component,
                details=HealthDetail(status=status, error=result.get("error")),
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
    description="Check the health status of the service and model availability.",
)
async def health_check(
    request: Request,
    model=Depends(get_model_service),
    backend: str = Depends(get_model_backend),
    settings: Settings = Depends(get_settings),
    secret_manager=Depends(get_secret_manager),
) -> HealthResponse:
    """Performs a comprehensive health check of the service."""
    model_status = "available" if model.is_ready() else "unavailable"
    secrets_healthy = secret_manager.is_healthy()

    # Check Kafka health if enabled
    kafka_status = "disabled"
    kafka_healthy = True
    if settings.kafka_enabled and hasattr(request.app.state, 'kafka_consumer') and request.app.state.kafka_consumer:
        kafka_health = HealthChecker().check_kafka_health(request.app.state.kafka_consumer)
        kafka_status = kafka_health.get("status", "unknown")
        kafka_healthy = kafka_status == "healthy"

    # Check async batch health if enabled
    async_batch_status = "disabled"
    async_batch_healthy = True
    if settings.async_batch_enabled and hasattr(request.app.state, 'async_batch_service') and request.app.state.async_batch_service:
        async_batch_health = HealthChecker().check_async_batch_health(request.app.state.async_batch_service)
        async_batch_status = async_batch_health.get("status", "unknown")
        async_batch_healthy = async_batch_status == "healthy"

    overall_status = "healthy"
    if not model.is_ready() or not secrets_healthy or not kafka_healthy or not async_batch_healthy:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        model_status=model_status,
        version=settings.app_version,
        backend=backend,
        timestamp=time.time(),
        kafka_status=kafka_status if settings.kafka_enabled else None,
        async_batch_status=async_batch_status if settings.async_batch_enabled else None,
    )


@router.get(
    "/ready",
    summary="Readiness check",
    description="Kubernetes readiness probe endpoint.",
)
async def readiness_check(
    model=Depends(get_model_service),
):
    """Checks if the service is ready to accept incoming traffic."""
    if not model.is_ready():
        from app.utils.exceptions import ServiceUnavailableError

        raise ServiceUnavailableError(
            message="Service not ready",
            context={"model_loaded": getattr(model, "_is_loaded", False)},
        )

    return {"status": "ready"}


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Get metrics in Prometheus format for monitoring and alerting.",
)
async def get_prometheus_metrics(
    settings: Settings = Depends(get_settings),
):
    """Exposes application and model metrics in Prometheus format."""
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")

    try:
        from app.monitoring.prometheus import get_metrics

        metrics = get_metrics()
        content = metrics.get_metrics()
        content_type = metrics.get_metrics_content_type()

        return Response(content=content, media_type=content_type)

    except Exception as e:
        handle_prometheus_metrics_error(e)


@router.get(
    "/metrics-json",
    response_model=MetricsResponse,
    summary="Service metrics (JSON)",
    description="Get performance metrics and system information in JSON format (legacy endpoint).",
)
async def get_metrics_json(
    model=Depends(get_model_service),
    settings: Settings = Depends(get_settings),
) -> MetricsResponse:
    """Provides service and model performance metrics in JSON format."""
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")

    try:
        metrics = model.get_performance_metrics()
        return MetricsResponse(**metrics)

    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get(
    "/kafka-metrics",
    response_model=KafkaMetricsResponse,
    summary="Kafka consumer metrics",
    description="Get detailed metrics about the Kafka consumer performance and health.",
)
async def get_kafka_metrics(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> KafkaMetricsResponse:
    """Get Kafka consumer metrics if Kafka is enabled."""
    if not settings.kafka_enabled:
        raise HTTPException(status_code=404, detail="Kafka consumer is disabled")

    if not hasattr(request.app.state, 'kafka_consumer') or not request.app.state.kafka_consumer:
        raise HTTPException(status_code=404, detail="Kafka consumer not initialized")

    try:
        metrics = request.app.state.kafka_consumer.get_metrics()
        return KafkaMetricsResponse(**metrics)

    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get(
    "/async-batch-metrics",
    response_model=AsyncBatchMetricsResponse,
    summary="Async batch processing metrics",
    description="Get comprehensive metrics for async batch processing performance.",
)
async def get_async_batch_metrics(
    async_batch_service: AsyncBatchService = Depends(get_async_batch_service_dependency),
) -> AsyncBatchMetricsResponse:
    """Get async batch processing metrics.

    Args:
        async_batch_service: The async batch service dependency.

    Returns:
        AsyncBatchMetricsResponse with comprehensive metrics.

    Raises:
        HTTPException: If async batch processing is not enabled or available.
    """
    try:
        metrics = await async_batch_service.get_batch_metrics()
        return metrics  # type: ignore

    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")
