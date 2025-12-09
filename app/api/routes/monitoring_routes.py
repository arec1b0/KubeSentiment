"""
API routes for monitoring, drift detection, and advanced metrics.

This module provides endpoints for:
- System health and readiness checks (Standard)
- Prometheus and JSON metrics (Standard)
- Drift detection summaries and reports (Advanced)
- Advanced KPIs (business, quality, cost, performance) (Advanced)
- Model registry information (Advanced)
- Explainability and interpretability (Advanced)
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Request, Response
from pydantic import BaseModel, Field

from app.api.schemas.responses import (
    AsyncBatchMetricsResponse,
    DetailedHealthResponse,
    HealthResponse,
    KafkaMetricsResponse,
    MetricsResponse,
)
from app.core.config import Settings, get_settings
from app.core.dependencies import require_initialized, get_model_service
from app.core.secrets import get_secret_manager
from app.services.monitoring_service import MonitoringService
from app.services.async_batch_service import AsyncBatchService
from app.services.drift_detection import get_drift_detector
from app.services.mlflow_registry import get_model_registry
from app.services.explainability import get_explainability_engine
from app.monitoring.advanced_metrics import get_advanced_metrics_collector
from app.utils.error_codes import ErrorCode, raise_validation_error
from app.utils.error_handlers import handle_prometheus_metrics_error

logger = logging.getLogger(__name__)

# Use empty prefix so we can mount standard routes at root (e.g. /health)
# and advanced routes under /monitoring
router = APIRouter(tags=["monitoring"])


def get_monitoring_service(settings: Settings = Depends(get_settings)) -> MonitoringService:
    return MonitoringService(settings)


async def get_async_batch_service_dependency(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AsyncBatchService:
    if not settings.performance.async_batch_enabled:
        raise HTTPException(status_code=404, detail="Async batch processing is disabled")
    if (
        not hasattr(request.app.state, "async_batch_service")
        or not request.app.state.async_batch_service
    ):
        raise HTTPException(status_code=503, detail="Async batch service not initialized")
    return request.app.state.async_batch_service


# Request/Response Models
class ExplainRequest(BaseModel):
    """Request for prediction explanation."""

    text: str = Field(..., min_length=1, max_length=10000, description="Text to explain")
    prediction: str = Field(..., description="Predicted label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    use_attention: bool = Field(default=True, description="Use attention weights")
    use_gradients: bool = Field(default=False, description="Use gradient-based methods")


# --- Standard Monitoring Endpoints ---

@router.get(
    "/health/details",
    response_model=DetailedHealthResponse,
    summary="Detailed service health check",
    description="Provides a detailed health status of the service and its dependencies.",
)
async def detailed_health_check(
    request: Request,
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    model=Depends(get_model_service),
    secret_manager=Depends(get_secret_manager),
) -> DetailedHealthResponse:
    """Performs a detailed health check of all major components."""
    return await monitoring_service.get_detailed_health(request, model, secret_manager)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Provides a high-level health status of the service, suitable for liveness probes.",
)
async def health_check(
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    model=Depends(get_model_service),
    secret_manager=Depends(get_secret_manager),
) -> HealthResponse:
    """Performs a high-level health check of the service."""
    return await monitoring_service.get_simple_health(model, secret_manager)


@router.get(
    "/ready",
    summary="Readiness check",
    description="Checks if the service is ready to accept traffic, suitable for readiness probes.",
)
async def readiness_check(
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
    model=Depends(get_model_service),
):
    """Checks if the service is fully initialized and ready to accept traffic."""
    is_ready = await monitoring_service.get_readiness(model)
    if not is_ready:
        from app.utils.exceptions import ServiceUnavailableError
        raise ServiceUnavailableError("Model not ready for inference.")
    return {"status": "ready"}


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Exposes performance and health metrics in Prometheus format.",
)
async def get_prometheus_metrics(
    settings: Settings = Depends(get_settings),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
):
    """Exposes application and model metrics in Prometheus format."""
    if not settings.monitoring.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")
    try:
        metrics = monitoring_service.get_prometheus_metrics()
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
    """Provides service and model performance metrics in JSON format."""
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
    """Retrieves detailed metrics about the Kafka consumer's performance."""
    if not settings.kafka.kafka_enabled:
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
    """Retrieves performance metrics for the asynchronous batch processing service."""
    try:
        return await async_batch_service.get_batch_metrics()
    except Exception as e:
        logger.error(f"Error retrieving async batch metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


# --- Advanced Monitoring Endpoints (Prefixed with /monitoring) ---

# Drift Detection Endpoints
@router.get("/monitoring/drift", summary="Get drift detection summary")
async def get_drift_summary() -> Dict[str, Any]:
    """Get drift detection summary and statistics."""
    detector = get_drift_detector()

    if detector is None or not detector.enabled:
        return {"enabled": False, "message": "Drift detection is not enabled"}

    return detector.get_drift_summary()


@router.get("/monitoring/drift/check", summary="Check for current drift")
async def check_drift() -> Dict[str, Any]:
    """Check for drift in current window vs baseline."""
    detector = get_drift_detector()
    detector = require_initialized(
        detector,
        service_name="drift_detector",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Drift detection not available",
    )

    drift_metrics = detector.check_drift()

    if drift_metrics is None:
        return {
            "message": "Not enough data for drift detection",
            "baseline_established": detector.baseline_established,
            "min_samples_required": detector.min_samples,
        }

    return {
        "timestamp": drift_metrics.timestamp.isoformat(),
        "data_drift_detected": drift_metrics.data_drift_detected,
        "prediction_drift_detected": drift_metrics.prediction_drift_detected,
        "drift_score": drift_metrics.drift_score,
        "statistical_tests": drift_metrics.statistical_tests,
        "feature_drifts": drift_metrics.feature_drifts,
    }


@router.post("/monitoring/drift/reset", summary="Reset drift detection window")
async def reset_drift_window() -> Dict[str, str]:
    """Reset the current drift detection window."""
    detector = get_drift_detector()
    detector = require_initialized(
        detector,
        service_name="drift_detector",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Drift detection not available",
    )

    detector.reset_current_window()
    return {"message": "Drift detection window reset successfully"}


@router.post("/monitoring/drift/update-baseline", summary="Update drift baseline")
async def update_drift_baseline() -> Dict[str, str]:
    """Update drift baseline with current window data."""
    detector = get_drift_detector()
    detector = require_initialized(
        detector,
        service_name="drift_detector",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Drift detection not available",
    )

    detector.update_baseline()
    return {"message": "Drift baseline updated successfully"}


@router.get("/monitoring/drift/report", summary="Export drift report", response_class=None)
async def export_drift_report():
    """Export detailed drift report in HTML format."""
    detector = get_drift_detector()
    detector = require_initialized(
        detector,
        service_name="drift_detector",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Drift detection not available",
    )

    report_html = detector.export_drift_report()

    if report_html is None:
        raise_validation_error(
            error_code=ErrorCode.MONITORING_DATA_INSUFFICIENT,
            detail="Not enough data to generate drift report",
            status_code=400,
        )

    from fastapi.responses import HTMLResponse

    return HTMLResponse(content=report_html)


# Advanced KPI Endpoints
@router.get("/monitoring/kpis/business", summary="Get business KPIs")
async def get_business_kpis() -> Dict[str, Any]:
    """Get business-focused KPIs."""
    collector = get_advanced_metrics_collector()
    collector = require_initialized(
        collector,
        service_name="advanced_metrics_collector",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Advanced metrics not available",
    )

    return collector.get_business_kpis()


@router.get("/monitoring/kpis/quality", summary="Get quality metrics")
async def get_quality_metrics() -> Dict[str, Any]:
    """Get model quality metrics."""
    collector = get_advanced_metrics_collector()
    collector = require_initialized(
        collector,
        service_name="advanced_metrics_collector",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Advanced metrics not available",
    )

    return collector.get_quality_metrics()


@router.get("/monitoring/kpis/cost", summary="Get cost metrics")
async def get_cost_metrics() -> Dict[str, Any]:
    """Get cost and efficiency metrics."""
    collector = get_advanced_metrics_collector()
    collector = require_initialized(
        collector,
        service_name="advanced_metrics_collector",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Advanced metrics not available",
    )

    return collector.get_cost_metrics()


@router.get("/monitoring/kpis/performance", summary="Get performance metrics")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get detailed performance metrics."""
    collector = get_advanced_metrics_collector()
    collector = require_initialized(
        collector,
        service_name="advanced_metrics_collector",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Advanced metrics not available",
    )

    return collector.get_performance_metrics()


@router.get("/monitoring/kpis/slo", summary="Check SLO compliance")
async def check_slo_compliance(
    availability_target: float = Query(default=99.9, ge=0, le=100),
    latency_p95_target_ms: float = Query(default=100, ge=0),
    latency_p99_target_ms: float = Query(default=250, ge=0),
) -> Dict[str, Any]:
    """Check SLO (Service Level Objective) compliance."""
    collector = get_advanced_metrics_collector()
    collector = require_initialized(
        collector,
        service_name="advanced_metrics_collector",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Advanced metrics not available",
    )

    return collector.get_slo_compliance(
        availability_target=availability_target,
        latency_p95_target_ms=latency_p95_target_ms,
        latency_p99_target_ms=latency_p99_target_ms,
    )


# Model Registry Endpoints
@router.get("/monitoring/models", summary="List registered models")
async def list_models(
    filter_string: Optional[str] = Query(default=None, description="Filter expression"),
    max_results: int = Query(default=10, ge=1, le=100),
) -> Dict[str, Any]:
    """List registered models in MLflow registry."""
    registry = get_model_registry()

    if registry is None or not registry.enabled:
        return {"enabled": False, "message": "Model registry is not enabled", "models": []}

    models = registry.search_models(filter_string=filter_string, max_results=max_results)

    return {"enabled": True, "count": len(models), "models": models}


@router.get("/monitoring/models/{model_name}/production", summary="Get production model")
async def get_production_model(model_name: str) -> Dict[str, Any]:
    """Get the production version of a model."""
    registry = get_model_registry()
    registry = require_initialized(
        registry,
        service_name="model_registry",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Model registry not available",
    )

    model_info = registry.get_production_model(model_name)

    if model_info is None:
        raise_validation_error(
            error_code=ErrorCode.MODEL_REGISTRY_ERROR,
            detail=f"No production model found for {model_name}",
            status_code=404,
            model_name=model_name,
        )

    return model_info


@router.get("/monitoring/models/{model_name}/versions", summary="Get all model versions")
async def get_all_production_models(model_name: str) -> Dict[str, Any]:
    """Get all production versions of a model (for A/B testing)."""
    registry = get_model_registry()
    registry = require_initialized(
        registry,
        service_name="model_registry",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Model registry not available",
    )

    versions = registry.get_all_production_models(model_name)

    return {"model_name": model_name, "production_versions": versions, "count": len(versions)}


# Explainability Endpoints
@router.post("/monitoring/explain", summary="Explain prediction")
async def explain_prediction(request: ExplainRequest) -> Dict[str, Any]:
    """Generate explanation for a prediction."""
    explainer = get_explainability_engine()

    if explainer is None or not explainer.enabled:
        return {
            "enabled": False,
            "message": "Explainability engine is not enabled",
            "text": request.text,
            "prediction": request.prediction,
            "confidence": request.confidence,
        }

    explanation = explainer.explain_prediction(
        text=request.text,
        prediction=request.prediction,
        confidence=request.confidence,
        use_attention=request.use_attention,
        use_gradients=request.use_gradients,
    )

    return explanation


@router.post("/monitoring/explain/html", summary="Get HTML explanation", response_class=None)
async def get_html_explanation(request: ExplainRequest):
    """Generate HTML visualization of prediction explanation."""
    explainer = get_explainability_engine()
    explainer = require_initialized(
        explainer,
        service_name="explainability_engine",
        error_code=ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
        detail="Explainability engine not available",
    )

    explanation = explainer.explain_prediction(
        text=request.text,
        prediction=request.prediction,
        confidence=request.confidence,
        use_attention=request.use_attention,
        use_gradients=request.use_gradients,
    )

    html = explainer.generate_html_explanation(explanation)

    from fastapi.responses import HTMLResponse

    return HTMLResponse(content=html)


@router.get("/monitoring/health", summary="Monitoring subsystem health check")
async def monitoring_subsystem_health() -> Dict[str, Any]:
    """Check health of advanced monitoring components (drift, registry, etc)."""
    detector = get_drift_detector()
    registry = get_model_registry()
    explainer = get_explainability_engine()
    collector = get_advanced_metrics_collector()

    return {
        "drift_detection": {
            "enabled": detector is not None and detector.enabled,
            "healthy": detector is not None and detector.enabled and detector.baseline_established,
        },
        "model_registry": {
            "enabled": registry is not None and registry.enabled,
            "healthy": registry is not None and registry.enabled,
        },
        "explainability": {
            "enabled": explainer is not None and explainer.enabled,
            "healthy": explainer is not None and explainer.enabled,
        },
        "advanced_metrics": {"enabled": collector is not None, "healthy": collector is not None},
    }
