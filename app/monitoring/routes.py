"""
Monitoring endpoints.
"""
import time

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.schemas.responses import (
    ComponentHealth,
    DetailedHealthResponse,
    HealthDetail,
    HealthResponse,
    MetricsResponse,
)
from app.core.config import Settings, get_settings
from app.core.dependencies import get_model_backend, get_model_service
from app.core.secrets import get_secret_manager
from app.monitoring.health import HealthChecker
from app.utils.error_handlers import (
    handle_metrics_error,
    handle_prometheus_metrics_error,
)

router = APIRouter()


@router.get(
    "/health/details",
    response_model=DetailedHealthResponse,
    summary="Detailed service health check",
    description="Get a detailed health status of the service and its dependencies.",
)
async def detailed_health_check(
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
    model=Depends(get_model_service),
    backend: str = Depends(get_model_backend),
    settings: Settings = Depends(get_settings),
    secret_manager=Depends(get_secret_manager),
) -> HealthResponse:
    """Performs a comprehensive health check of the service."""
    model_status = "available" if model.is_ready() else "unavailable"
    secrets_healthy = secret_manager.is_healthy()

    overall_status = "healthy"
    if not model.is_ready() or not secrets_healthy:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        model_status=model_status,
        version=settings.app_version,
        backend=backend,
        timestamp=time.time(),
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
        handle_metrics_error(e)
