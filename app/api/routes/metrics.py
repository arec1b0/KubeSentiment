"""
Metrics endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.schemas.responses import MetricsResponse
from app.core.config import Settings, get_settings
from app.core.dependencies import get_model_service
from app.utils.error_handlers import handle_metrics_error, handle_prometheus_metrics_error

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Get metrics in Prometheus format for monitoring and alerting.",
)
async def get_prometheus_metrics(
    settings: Settings = Depends(get_settings),
):
    """Exposes application and model metrics in Prometheus format.

    This endpoint is designed to be scraped by a Prometheus server. It provides
    a wide range of metrics, including request latency, error rates, and model
    performance, in the standardized Prometheus text-based format.

    Args:
        settings: The application's configuration settings.

    Returns:
        A `Response` object containing the metrics in Prometheus format.

    Raises:
        HTTPException: If the metrics endpoint is disabled in the settings.
    """
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
    """Provides service and model performance metrics in JSON format.

    This endpoint offers a structured JSON representation of the service's
    performance metrics. It can be used for custom monitoring dashboards or
    programmatic health checks.

    Args:
        model: The model service instance, injected as a dependency.
        settings: The application's configuration settings.

    Returns:
        A `MetricsResponse` object containing performance metrics.

    Raises:
        HTTPException: If the metrics endpoint is disabled in the settings.
    """
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")

    try:
        metrics = model.get_performance_metrics()
        return MetricsResponse(**metrics)

    except Exception as e:
        handle_metrics_error(e)
