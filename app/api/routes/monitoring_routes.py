"""
API routes for monitoring, drift detection, and advanced metrics.

This module provides endpoints for:
- Drift detection summaries and reports
- Advanced KPIs (business, quality, cost, performance)
- Model registry information
- Explainability and interpretability
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.drift_detection import get_drift_detector
from app.services.mlflow_registry import get_model_registry
from app.services.explainability import get_explainability_engine
from app.monitoring.advanced_metrics import get_advanced_metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# Request/Response Models
class ExplainRequest(BaseModel):
    """Request for prediction explanation."""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to explain")
    prediction: str = Field(..., description="Predicted label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    use_attention: bool = Field(default=True, description="Use attention weights")
    use_gradients: bool = Field(default=False, description="Use gradient-based methods")


# Drift Detection Endpoints
@router.get("/drift", summary="Get drift detection summary")
async def get_drift_summary() -> Dict[str, Any]:
    """
    Get drift detection summary and statistics.

    Returns drift metrics including:
    - Baseline status
    - Current window size
    - Recent drift detections
    - Drift scores and thresholds
    """
    detector = get_drift_detector()

    if detector is None or not detector.enabled:
        return {
            "enabled": False,
            "message": "Drift detection is not enabled"
        }

    return detector.get_drift_summary()


@router.get("/drift/check", summary="Check for current drift")
async def check_drift() -> Dict[str, Any]:
    """
    Check for drift in current window vs baseline.

    Performs statistical tests and returns drift metrics.
    """
    detector = get_drift_detector()

    if detector is None or not detector.enabled:
        raise HTTPException(status_code=503, detail="Drift detection not available")

    drift_metrics = detector.check_drift()

    if drift_metrics is None:
        return {
            "message": "Not enough data for drift detection",
            "baseline_established": detector.baseline_established,
            "min_samples_required": detector.min_samples
        }

    return {
        "timestamp": drift_metrics.timestamp.isoformat(),
        "data_drift_detected": drift_metrics.data_drift_detected,
        "prediction_drift_detected": drift_metrics.prediction_drift_detected,
        "drift_score": drift_metrics.drift_score,
        "statistical_tests": drift_metrics.statistical_tests,
        "feature_drifts": drift_metrics.feature_drifts
    }


@router.post("/drift/reset", summary="Reset drift detection window")
async def reset_drift_window() -> Dict[str, str]:
    """
    Reset the current drift detection window.

    Useful after deploying a new model or when baseline needs updating.
    """
    detector = get_drift_detector()

    if detector is None or not detector.enabled:
        raise HTTPException(status_code=503, detail="Drift detection not available")

    detector.reset_current_window()
    return {"message": "Drift detection window reset successfully"}


@router.post("/drift/update-baseline", summary="Update drift baseline")
async def update_drift_baseline() -> Dict[str, str]:
    """
    Update drift baseline with current window data.

    Moves current data to baseline and resets current window.
    """
    detector = get_drift_detector()

    if detector is None or not detector.enabled:
        raise HTTPException(status_code=503, detail="Drift detection not available")

    detector.update_baseline()
    return {"message": "Drift baseline updated successfully"}


@router.get("/drift/report", summary="Export drift report", response_class=None)
async def export_drift_report():
    """
    Export detailed drift report in HTML format.

    Uses Evidently library to generate comprehensive drift analysis.
    """
    detector = get_drift_detector()

    if detector is None or not detector.enabled:
        raise HTTPException(status_code=503, detail="Drift detection not available")

    report_html = detector.export_drift_report()

    if report_html is None:
        raise HTTPException(
            status_code=400,
            detail="Not enough data to generate drift report"
        )

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=report_html)


# Advanced KPI Endpoints
@router.get("/kpis/business", summary="Get business KPIs")
async def get_business_kpis() -> Dict[str, Any]:
    """
    Get business-focused KPIs.

    Returns:
    - Total predictions
    - Positive/negative ratios
    - Average confidence
    - High quality prediction ratio
    - Predictions by label and confidence bucket
    """
    collector = get_advanced_metrics_collector()

    if collector is None:
        raise HTTPException(status_code=503, detail="Advanced metrics not available")

    return collector.get_business_kpis()


@router.get("/kpis/quality", summary="Get quality metrics")
async def get_quality_metrics() -> Dict[str, Any]:
    """
    Get model quality metrics.

    Returns:
    - Low confidence rate
    - Confidence distribution statistics
    - Confidence percentiles (P50, P95, P99)
    """
    collector = get_advanced_metrics_collector()

    if collector is None:
        raise HTTPException(status_code=503, detail="Advanced metrics not available")

    return collector.get_quality_metrics()


@router.get("/kpis/cost", summary="Get cost metrics")
async def get_cost_metrics() -> Dict[str, Any]:
    """
    Get cost and efficiency metrics.

    Returns:
    - Total cost in USD
    - Cost per prediction
    - Monthly cost estimate
    - Cache savings percentage
    - Cost breakdown by day
    """
    collector = get_advanced_metrics_collector()

    if collector is None:
        raise HTTPException(status_code=503, detail="Advanced metrics not available")

    return collector.get_cost_metrics()


@router.get("/kpis/performance", summary="Get performance metrics")
async def get_performance_metrics() -> Dict[str, Any]:
    """
    Get detailed performance metrics.

    Returns:
    - Latency statistics (avg, P50, P95, P99)
    - Latency by backend
    - Current throughput (requests per second)
    """
    collector = get_advanced_metrics_collector()

    if collector is None:
        raise HTTPException(status_code=503, detail="Advanced metrics not available")

    return collector.get_performance_metrics()


@router.get("/kpis/slo", summary="Check SLO compliance")
async def check_slo_compliance(
    availability_target: float = Query(default=99.9, ge=0, le=100),
    latency_p95_target_ms: float = Query(default=100, ge=0),
    latency_p99_target_ms: float = Query(default=250, ge=0)
) -> Dict[str, Any]:
    """
    Check SLO (Service Level Objective) compliance.

    Args:
        availability_target: Target availability percentage (default: 99.9)
        latency_p95_target_ms: Target P95 latency in ms (default: 100)
        latency_p99_target_ms: Target P99 latency in ms (default: 250)

    Returns:
        SLO compliance status for availability and latency targets
    """
    collector = get_advanced_metrics_collector()

    if collector is None:
        raise HTTPException(status_code=503, detail="Advanced metrics not available")

    return collector.get_slo_compliance(
        availability_target=availability_target,
        latency_p95_target_ms=latency_p95_target_ms,
        latency_p99_target_ms=latency_p99_target_ms
    )


# Model Registry Endpoints
@router.get("/models", summary="List registered models")
async def list_models(
    filter_string: Optional[str] = Query(default=None, description="Filter expression"),
    max_results: int = Query(default=10, ge=1, le=100)
) -> Dict[str, Any]:
    """
    List registered models in MLflow registry.

    Args:
        filter_string: Optional filter (e.g., "name LIKE 'sentiment%'")
        max_results: Maximum number of results (1-100)

    Returns:
        List of registered models with metadata
    """
    registry = get_model_registry()

    if registry is None or not registry.enabled:
        return {
            "enabled": False,
            "message": "Model registry is not enabled",
            "models": []
        }

    models = registry.search_models(filter_string=filter_string, max_results=max_results)

    return {
        "enabled": True,
        "count": len(models),
        "models": models
    }


@router.get("/models/{model_name}/production", summary="Get production model")
async def get_production_model(model_name: str) -> Dict[str, Any]:
    """
    Get the production version of a model.

    Args:
        model_name: Name of the model

    Returns:
        Production model version information
    """
    registry = get_model_registry()

    if registry is None or not registry.enabled:
        raise HTTPException(status_code=503, detail="Model registry not available")

    model_info = registry.get_production_model(model_name)

    if model_info is None:
        raise HTTPException(
            status_code=404,
            detail=f"No production model found for {model_name}"
        )

    return model_info


@router.get("/models/{model_name}/versions", summary="Get all model versions")
async def get_all_production_models(model_name: str) -> Dict[str, Any]:
    """
    Get all production versions of a model (for A/B testing).

    Args:
        model_name: Name of the model

    Returns:
        List of production model versions
    """
    registry = get_model_registry()

    if registry is None or not registry.enabled:
        raise HTTPException(status_code=503, detail="Model registry not available")

    versions = registry.get_all_production_models(model_name)

    return {
        "model_name": model_name,
        "production_versions": versions,
        "count": len(versions)
    }


# Explainability Endpoints
@router.post("/explain", summary="Explain prediction")
async def explain_prediction(request: ExplainRequest) -> Dict[str, Any]:
    """
    Generate explanation for a prediction.

    Provides interpretability insights including:
    - Attention weights (if available)
    - Word-level importance scores
    - Confidence interpretation
    - Text features

    Args:
        request: Explanation request with text, prediction, and confidence

    Returns:
        Comprehensive explanation with various interpretation methods
    """
    explainer = get_explainability_engine()

    if explainer is None or not explainer.enabled:
        return {
            "enabled": False,
            "message": "Explainability engine is not enabled",
            "text": request.text,
            "prediction": request.prediction,
            "confidence": request.confidence
        }

    explanation = explainer.explain_prediction(
        text=request.text,
        prediction=request.prediction,
        confidence=request.confidence,
        use_attention=request.use_attention,
        use_gradients=request.use_gradients
    )

    return explanation


@router.post("/explain/html", summary="Get HTML explanation", response_class=None)
async def get_html_explanation(request: ExplainRequest):
    """
    Generate HTML visualization of prediction explanation.

    Args:
        request: Explanation request

    Returns:
        HTML page with visualization
    """
    explainer = get_explainability_engine()

    if explainer is None or not explainer.enabled:
        raise HTTPException(status_code=503, detail="Explainability engine not available")

    explanation = explainer.explain_prediction(
        text=request.text,
        prediction=request.prediction,
        confidence=request.confidence,
        use_attention=request.use_attention,
        use_gradients=request.use_gradients
    )

    html = explainer.generate_html_explanation(explanation)

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@router.get("/health", summary="Monitoring health check")
async def monitoring_health() -> Dict[str, Any]:
    """
    Check health of all monitoring components.

    Returns:
        Status of drift detection, model registry, explainability, and metrics
    """
    detector = get_drift_detector()
    registry = get_model_registry()
    explainer = get_explainability_engine()
    collector = get_advanced_metrics_collector()

    return {
        "drift_detection": {
            "enabled": detector is not None and detector.enabled,
            "healthy": detector is not None and detector.enabled and detector.baseline_established
        },
        "model_registry": {
            "enabled": registry is not None and registry.enabled,
            "healthy": registry is not None and registry.enabled
        },
        "explainability": {
            "enabled": explainer is not None and explainer.enabled,
            "healthy": explainer is not None and explainer.enabled
        },
        "advanced_metrics": {
            "enabled": collector is not None,
            "healthy": collector is not None
        }
    }
