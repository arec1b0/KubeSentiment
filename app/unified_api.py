"""
Unified API router supporting multiple model backends.

This module provides a consolidated API that works with both PyTorch and ONNX
backends through the strategy pattern, eliminating code duplication.
"""

import time
from functools import lru_cache
from typing import Any, Callable, Dict

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field

from .core.config import Settings, get_settings
from .core.logging import get_contextual_logger, get_logger
from .ml.model_strategy import ModelBackend, ModelStrategy
from .ml.onnx_optimizer import ONNXSentimentAnalyzer, get_onnx_sentiment_analyzer
from .ml.sentiment import SentimentAnalyzer, get_sentiment_analyzer
from .utils.error_codes import ErrorCode, raise_validation_error
from .utils.exceptions import ModelNotLoadedError, TextEmptyError, TextTooLongError

logger = get_logger(__name__)

# Create unified router
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

    @property
    def validated_text(self) -> str:
        """Get validated and cleaned text."""
        if not self.text or not self.text.strip():
            raise TextEmptyError(context={"text_length": len(self.text) if self.text else 0})
        return self.text.strip()


class PredictionResponse(BaseModel):
    """Response schema for sentiment predictions."""

    label: str = Field(..., description="Predicted sentiment label")
    score: float = Field(..., description="Confidence score (0.0 to 1.0)")
    inference_time_ms: float = Field(..., description="Model inference time in milliseconds")
    model_name: str = Field(..., description="Name of the model used")
    text_length: int = Field(..., description="Length of processed text")
    backend: str = Field(..., description="Model backend used (pytorch/onnx)")
    cached: bool = Field(default=False, description="Whether result was cached")


class HealthResponse(BaseModel):
    """Response schema for health checks."""

    status: str = Field(..., description="Service status")
    model_status: str = Field(..., description="Model availability status")
    version: str = Field(..., description="Application version")
    backend: str = Field(..., description="Model backend in use")
    timestamp: float = Field(..., description="Health check timestamp")


class MetricsResponse(BaseModel):
    """Response schema for service metrics."""

    torch_version: str = Field(..., description="PyTorch version")
    cuda_available: bool = Field(..., description="CUDA availability")
    cuda_memory_allocated_mb: float = Field(..., description="CUDA memory allocated in MB")
    cuda_memory_reserved_mb: float = Field(..., description="CUDA memory reserved in MB")
    cuda_device_count: int = Field(..., description="Number of CUDA devices")


# --- Model Backend Selection ---


def get_model_backend(
    backend: str = Query(None, description="Model backend to use (pytorch/onnx)"),
) -> str:
    """
    Determine which model backend to use.

    Args:
        backend: Optional backend override from query parameter

    Returns:
        Backend name to use
    """
    settings = get_settings()

    # Use query parameter if provided, otherwise use ONNX if path is configured
    if backend:
        return backend.lower()
    elif settings.onnx_model_path:
        return ModelBackend.ONNX
    else:
        return ModelBackend.PYTORCH


def get_model_strategy(
    backend: str = Depends(get_model_backend),
    settings: Settings = Depends(get_settings),
) -> ModelStrategy:
    """
    Get the appropriate model strategy based on backend selection.

    Args:
        backend: The selected backend
        settings: Application settings

    Returns:
        Model strategy instance
    """
    if backend == ModelBackend.ONNX:
        onnx_path = settings.onnx_model_path or settings.onnx_model_path_default
        return get_onnx_sentiment_analyzer(onnx_path)
    else:
        return get_sentiment_analyzer()


# --- Unified API Endpoints ---


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Analyze text sentiment",
    description="Perform sentiment analysis on the provided text using the selected backend.",
)
async def predict_sentiment(
    payload: TextInput,
    response: Response,
    model: ModelStrategy = Depends(get_model_strategy),
    backend: str = Depends(get_model_backend),
    settings: Settings = Depends(get_settings),
) -> PredictionResponse:
    """
    Analyze sentiment of the input text.

    Args:
        payload: The input text data
        response: FastAPI response object for headers
        model: The model strategy instance
        backend: The backend being used
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
        backend=backend,
    )

    request_logger.info("Starting sentiment prediction", operation="predict_start")

    if not model.is_ready():
        request_logger.error(
            "Model not ready for prediction",
            model_status="unavailable",
            operation="predict_failed",
        )
        raise ModelNotLoadedError(
            model_name=backend,
            context={"service_status": "unavailable", "endpoint": "predict"},
        )

    try:
        # Get validated text
        validated_text = payload.validated_text

        # Perform sentiment analysis
        result = model.predict(validated_text)

        # Add inference time to response headers
        response.headers["X-Inference-Time-MS"] = str(result["inference_time_ms"])
        response.headers["X-Model-Backend"] = backend

        request_logger.info(
            "Sentiment prediction completed successfully",
            operation="predict_success",
            label=result["label"],
            score=result["score"],
            inference_time_ms=result["inference_time_ms"],
            cached=result.get("cached", False),
        )

        # Add backend to response
        result["backend"] = backend

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
    model: ModelStrategy = Depends(get_model_strategy),
    backend: str = Depends(get_model_backend),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """
    Perform a health check of the service.

    Args:
        model: The model strategy instance
        backend: The backend being used
        settings: Application settings

    Returns:
        HealthResponse: Service health information
    """
    model_status = "available" if model.is_ready() else "unavailable"

    return HealthResponse(
        status="healthy",
        model_status=model_status,
        version=settings.app_version,
        backend=backend,
        timestamp=time.time(),
    )


@router.get(
    "/metrics-json",
    response_model=MetricsResponse,
    summary="Service metrics (JSON)",
    description="Get performance metrics and system information in JSON format.",
)
async def get_metrics_json(
    model: ModelStrategy = Depends(get_model_strategy),
    settings: Settings = Depends(get_settings),
) -> MetricsResponse:
    """
    Get service performance metrics in JSON format.

    Args:
        model: The model strategy instance
        settings: Application settings

    Returns:
        MetricsResponse: Performance metrics
    """
    if not settings.enable_metrics:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")

    try:
        metrics = model.get_performance_metrics()
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
    model: ModelStrategy = Depends(get_model_strategy),
    backend: str = Depends(get_model_backend),
) -> Dict[str, Any]:
    """
    Get information about the loaded model.

    Args:
        model: The model strategy instance
        backend: The backend being used

    Returns:
        Dict[str, Any]: Model information
    """
    try:
        info = model.get_model_info()
        info["backend"] = backend
        return info
    except Exception as e:
        from .utils.error_handlers import handle_model_info_error

        handle_model_info_error(e)
