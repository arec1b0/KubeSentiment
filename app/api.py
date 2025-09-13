"""
API router definitions for the MLOps sentiment analysis service.

This module contains all API endpoints organized using FastAPI routers
for better modularity and maintainability.
"""

import logging
import time
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Response, Depends
from pydantic import BaseModel, Field, validator

from .config import get_settings, Settings
from .ml.sentiment import get_sentiment_analyzer, SentimentAnalyzer

logger = logging.getLogger(__name__)

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
            raise ValueError("Text cannot be empty or whitespace only")
        return v.strip()


class PredictionResponse(BaseModel):
    """Response schema for sentiment predictions."""

    label: str = Field(..., description="Predicted sentiment label")
    score: float = Field(..., description="Confidence score (0.0 to 1.0)")
    inference_time_ms: float = Field(
        ..., description="Model inference time in milliseconds"
    )
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
    cuda_memory_allocated_mb: float = Field(
        ..., description="CUDA memory allocated in MB"
    )
    cuda_memory_reserved_mb: float = Field(
        ..., description="CUDA memory reserved in MB"
    )
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
    if not analyzer.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Service Unavailable: Sentiment analysis model is not loaded",
        )

    try:
        # Perform sentiment analysis
        result = analyzer.predict(payload.text)

        # Add inference time to response headers
        response.headers["X-Inference-Time-MS"] = str(result["inference_time_ms"])

        return PredictionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid input: {str(e)}")
    except RuntimeError as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during prediction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
    response_model=MetricsResponse,
    summary="Service metrics",
    description="Get performance metrics and system information.",
)
async def get_metrics(
    analyzer: SentimentAnalyzer = Depends(get_sentiment_analyzer),
    settings: Settings = Depends(get_settings),
) -> MetricsResponse:
    """
    Get service performance metrics.

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
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


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
        logger.error(f"Error retrieving model info: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve model information"
        )
