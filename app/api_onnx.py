"""
Optimized FastAPI application using ONNX Runtime.

This module provides an optimized API endpoint for sentiment analysis
using ONNX Runtime for faster inference.
"""

from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import time

from .config import get_settings
from .logging_config import get_logger
from .exceptions import ModelNotLoadedError, ModelInferenceError, TextEmptyError
from .ml.onnx_optimizer import ONNXSentimentAnalyzer, get_onnx_sentiment_analyzer
from .middleware import (
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from .correlation_middleware import CorrelationIDMiddleware
from .monitoring import get_metrics

logger = get_logger(__name__)
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="MLOps Sentiment Analysis API (ONNX Optimized)",
    description="Production-ready sentiment analysis API using ONNX Runtime",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIDMiddleware)


# Global exception handler for ServiceError and subclasses
from fastapi.responses import JSONResponse
from .exceptions import ServiceError


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    """Handle custom service errors consistently."""
    logger.warning(f"Service error: {exc}", exc_info=False)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc),
            "error_code": exc.code,
            "context": exc.context,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_id": f"error_{int(time.time())}",
        },
    )


# Request/Response models
class SentimentRequest(BaseModel):
    """Request model for sentiment analysis."""

    text: str = Field(
        ...,
        description="Text to analyze for sentiment",
        min_length=1,
        max_length=5000,
        example="This product is amazing!",
    )


class SentimentResponse(BaseModel):
    """Response model for sentiment analysis."""

    label: str = Field(..., description="Predicted sentiment label")
    score: float = Field(..., description="Confidence score", ge=0.0, le=1.0)
    inference_time_ms: float = Field(..., description="Inference time in milliseconds")
    model_type: str = Field(default="ONNX", description="Model type used for inference")
    cached: bool = Field(default=False, description="Whether result was cached")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    model_loaded: bool
    model_type: str
    timestamp: float


class ModelInfoResponse(BaseModel):
    """Response model for model information."""

    model_type: str
    model_path: str
    is_loaded: bool
    is_ready: bool
    model_size_mb: float
    cache_size: int
    cache_max_size: int


# Dependency injection
def get_analyzer() -> ONNXSentimentAnalyzer:
    """Dependency injection for ONNX analyzer."""
    onnx_path = settings.onnx_model_path or settings.onnx_model_path_default
    return get_onnx_sentiment_analyzer(onnx_path)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "MLOps Sentiment Analysis API (ONNX Optimized)",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(analyzer: ONNXSentimentAnalyzer = Depends(get_analyzer)):
    """
    Health check endpoint.

    Returns the current health status of the API and model.
    """
    try:
        is_ready = analyzer.is_ready()

        return HealthResponse(
            status="healthy" if is_ready else "degraded",
            model_loaded=analyzer._is_loaded,
            model_type="ONNX",
            timestamp=time.time(),
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        from .exceptions import ServiceUnavailableError

        raise ServiceUnavailableError(
            message="Health check failed", context={"error": str(e)}
        )


@app.get("/ready", tags=["Health"])
async def readiness_check(analyzer: ONNXSentimentAnalyzer = Depends(get_analyzer)):
    """
    Readiness check for Kubernetes.

    Returns 200 if the service is ready to accept traffic.
    """
    if not analyzer.is_ready():
        from .exceptions import ServiceUnavailableError

        raise ServiceUnavailableError(
            message="Service not ready", context={"model_loaded": analyzer._is_loaded}
        )

    return {"status": "ready"}


@app.get("/model/info", response_model=ModelInfoResponse, tags=["Model"])
async def get_model_info(analyzer: ONNXSentimentAnalyzer = Depends(get_analyzer)):
    """
    Get information about the loaded ONNX model.

    Returns model metadata, configuration, and performance information.
    """
    try:
        info = analyzer.get_model_info()
        return ModelInfoResponse(**info)
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        from .exceptions import InternalError

        raise InternalError(
            message="Failed to retrieve model info", context={"error": str(e)}
        )


@app.post("/predict", response_model=SentimentResponse, tags=["Prediction"])
async def predict_sentiment(
    request: SentimentRequest, analyzer: ONNXSentimentAnalyzer = Depends(get_analyzer)
):
    """
    Predict sentiment for the provided text using ONNX model.

    This endpoint uses ONNX Runtime for optimized inference performance.
    Results are cached to improve response times for repeated requests.

    Args:
        request: SentimentRequest containing the text to analyze

    Returns:
        SentimentResponse with prediction results

    Raises:
        HTTPException: If prediction fails or model is not ready
    """
    try:
        # Perform prediction
        result = analyzer.predict(request.text)

        # Record metrics
        metrics = get_metrics()
        metrics.record_inference_duration(result["inference_time_ms"] / 1000)
        metrics.record_prediction_metrics(result["score"], len(request.text))

        return SentimentResponse(
            label=result["label"],
            score=result["score"],
            inference_time_ms=result["inference_time_ms"],
            model_type="ONNX",
            cached=result.get("cached", False),
        )

    except TextEmptyError as e:
        logger.warning(f"Empty text provided: {e}")
        raise  # Re-raise custom exception to be handled by global exception handler

    except ModelNotLoadedError as e:
        logger.error(f"Model not loaded: {e}")
        raise  # Re-raise custom exception to be handled by global exception handler

    except ModelInferenceError as e:
        logger.error(f"Inference failed: {e}")
        raise  # Re-raise custom exception to be handled by global exception handler

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        from .exceptions import InternalError

        raise InternalError(
            message=f"Unexpected error during prediction: {str(e)}",
            context={"error_type": type(e).__name__},
        )


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response

    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting ONNX-optimized Sentiment Analysis API")

    try:
        # Initialize analyzer
        onnx_path = settings.onnx_model_path or settings.onnx_model_path_default
        analyzer = get_onnx_sentiment_analyzer(onnx_path)

        if analyzer.is_ready():
            logger.info("ONNX model loaded successfully")
        else:
            logger.warning("ONNX model failed to load")

    except Exception as e:
        logger.error(f"Startup failed: {e}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down ONNX-optimized Sentiment Analysis API")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api_onnx:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
    )
