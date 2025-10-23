"""
API router definitions for the MLOps sentiment analysis service.

This module contains all API endpoints organized using FastAPI routers
for better modularity and maintainability.
"""

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, validator

from .core.config import Settings, get_settings
from .core.logging import get_contextual_logger, get_logger, log_api_request
from .error_codes import ErrorCode, raise_validation_error
from .ml.sentiment import SentimentAnalyzer, get_sentiment_analyzer
from .utils.exceptions import ModelNotLoadedError, TextEmptyError, TextTooLongError

logger = get_logger(__name__)

# Create API router
router = APIRouter()


# --- Pydantic Models ---


class TextInput(BaseModel):
    """Input schema for text analysis requests."""

    text: str = Field(
        ...,
        description="Text to analyze for sentiment",
        min_length=1,
        max_length=10000,
        example="I love this product! It's amazing.",
    )

    @validator("text")
    def validate_text(cls, v):
        """Validate and clean input text."""
        if not v or not v.strip():
            raise TextEmptyError(context={"text_length": len(v) if v else 0})

        # Check for maximum length
        settings = get_settings()
        # Coerce max_text_length to int safely; tests may provide a Mock
        try:
            max_len = int(getattr(settings, "max_text_length", None))
        except Exception:
            # Fallback to default defined on Settings
            from .core.config import Settings

            max_len = Settings().max_text_length

        if len(v.strip()) > max_len:
            raise TextTooLongError(
                text_length=len(v.strip()),
                max_length=max_len,
                context={"raw_length": len(v)},
            )

        return v.strip()


class PredictionResponse(BaseModel):
    """Response schema for sentiment predictions."""

    label: str = Field(..., description="Predicted sentiment label")
    score: float = Field(..., description="Confidence score (0.0 to 1.0)")
    inference_time_ms: float = Field(..., description="Model inference time in milliseconds")
    model_name: str = Field(..., description="Name of the model used")
    text_length: int = Field(..., description="Length of processed text")


class HealthResponse(BaseModel):
    """Response schema for health checks."""

    status: str = Field(..., description="Service status")
    model_status: str = Field(..., description="Model availability status")
    version: str = Field(..., description="Application version")
    timestamp: float = Field(..., description="Health check timestamp")


class MetricsResponse(BaseModel):
    """Response schema for service metrics."""

    torch_version: str = Field(..., description="PyTorch version")
    cuda_available: bool = Field(..., description="CUDA availability")
    cuda_memory_allocated_mb: float = Field(..., description="CUDA memory allocated in MB")
    cuda_memory_reserved_mb: float = Field(..., description="CUDA memory reserved in MB")
    cuda_device_count: int = Field(..., description="Number of CUDA devices")


# --- API Endpoints ---


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Analyze text sentiment",
    description="Perform sentiment analysis on the provided text and return the prediction with confidence score.",
)
async def predict_sentiment(
    payload: TextInput,
    response: Response,
    analyzer: SentimentAnalyzer = Depends(get_sentiment_analyzer),
    settings: Settings = Depends(get_settings),
) -> PredictionResponse:
    """
    Analyze sentiment of the input text.

    Args:
        payload: The input text data
        response: FastAPI response object for headers
        analyzer: The sentiment analyzer instance
        settings: Application settings

    Returns:
        PredictionResponse: Sentiment prediction results

    Raises:
        HTTPException: If the model is unavailable or prediction fails
    """
    # Create contextual logger for this request
    request_logger = get_contextual_logger(
        __name__,
        endpoint="predict",
        text_length=len(payload.text),
        model_name=settings.model_name,
    )

    request_logger.info("Starting sentiment prediction", operation="predict_start")

    if not analyzer.is_ready():
        request_logger.error(
            "Model not ready for prediction",
            model_status="unavailable",
            operation="predict_failed",
        )
        raise ModelNotLoadedError(
            model_name=settings.model_name,
            context={"service_status": "unavailable", "endpoint": "predict"},
        )

    try:
        # Perform sentiment analysis
        result = analyzer.predict(payload.text)

        # Add inference time to response headers
        response.headers["X-Inference-Time-MS"] = str(result["inference_time_ms"])

        request_logger.info(
            "Sentiment prediction completed successfully",
            operation="predict_success",
            label=result["label"],
            score=result["score"],
            inference_time_ms=result["inference_time_ms"],
            cached=result.get("cached", False),
        )

        return PredictionResponse(**result)

    except Exception as e:
        request_logger.error(
            "Prediction failed",
            error=str(e),
            error_type=type(e).__name__,
            operation="predict_failed",
            exc_info=True,
        )
        raise_validation_error(
            ErrorCode.MODEL_INFERENCE_FAILED,
            detail=f"Failed to analyze sentiment: {str(e)}",
            status_code=500,
            text_length=len(payload.text),
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Check the health status of the service and model availability.",
)
async def health_check(
    analyzer: SentimentAnalyzer = Depends(get_sentiment_analyzer),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """
    Perform a health check of the service.

    Args:
        analyzer: The sentiment analyzer instance
        settings: Application settings

    Returns:
        HealthResponse: Service health information
    """
    model_status = "available" if analyzer.is_ready() else "unavailable"

    return HealthResponse(
        status="healthy",
        model_status=model_status,
        version=settings.app_version,
        timestamp=time.time(),
    )


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Get metrics in Prometheus format for monitoring and alerting.",
)
async def get_prometheus_metrics(
    settings: Settings = Depends(get_settings),
):
    """
    Get metrics in Prometheus format.

    Args:
        settings: Application settings

    Returns:
        str: Metrics in Prometheus text format
    """
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")

    try:
        from .monitoring import get_metrics

        metrics = get_metrics()
        content = metrics.get_metrics()
        content_type = metrics.get_metrics_content_type()

        return Response(content=content, media_type=content_type)

    except Exception as e:
        from .utils.error_handlers import handle_prometheus_metrics_error

        handle_prometheus_metrics_error(e)


@router.get(
    "/metrics-json",
    response_model=MetricsResponse,
    summary="Service metrics (JSON)",
    description="Get performance metrics and system information in JSON format (legacy endpoint).",
)
async def get_metrics_json(
    analyzer: SentimentAnalyzer = Depends(get_sentiment_analyzer),
    settings: Settings = Depends(get_settings),
) -> MetricsResponse:
    """
    Get service performance metrics in JSON format.

    Args:
        analyzer: The sentiment analyzer instance
        settings: Application settings

    Returns:
        MetricsResponse: Performance metrics
    """
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")

    try:
        metrics = analyzer.get_performance_metrics()
        return MetricsResponse(**metrics)

    except Exception as e:
        from .utils.error_handlers import handle_metrics_error

        handle_metrics_error(e)


@router.get(
    "/model-info",
    summary="Model information",
    description="Get detailed information about the loaded model.",
)
async def get_model_info(
    analyzer: SentimentAnalyzer = Depends(get_sentiment_analyzer),
) -> Dict[str, Any]:
    """
    Get information about the loaded model.

    Args:
        analyzer: The sentiment analyzer instance

    Returns:
        Dict[str, Any]: Model information
    """
    try:
        return analyzer.get_model_info()
    except Exception as e:
        from .utils.error_handlers import handle_model_info_error

        handle_model_info_error(e)
