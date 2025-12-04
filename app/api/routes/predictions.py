"""
Prediction endpoints.

This module provides the primary endpoints for making sentiment analysis
predictions. It includes synchronous and asynchronous endpoints for
single predictions and batch processing.
"""

import asyncio
import uuid

from fastapi import APIRouter, Depends, Response

from app.api.schemas.requests import TextInput
from app.api.schemas.responses import PredictionResponse
from app.core.config import Settings, get_settings
from app.core.dependencies import get_data_writer, get_model_backend, get_prediction_service
from app.core.logging import get_contextual_logger
from app.utils.error_codes import ErrorCode, raise_validation_error
from app.utils.exceptions import ModelNotLoadedError

router = APIRouter()


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Analyze text sentiment",
    description="Perform sentiment analysis on the provided text using the selected backend.",
)
async def predict_sentiment(
    payload: TextInput,
    response: Response,
    prediction_service=Depends(get_prediction_service),
    backend: str = Depends(get_model_backend),
    settings: Settings = Depends(get_settings),
    data_writer=Depends(get_data_writer),
) -> PredictionResponse:
    """Analyzes the sentiment of a given text.

    This is the primary endpoint for real-time sentiment analysis. It accepts a
    JSON payload with a single text input and returns a prediction of its
    sentiment, including a label (e.g., 'POSITIVE', 'NEGATIVE') and a
    confidence score. The endpoint also provides performance metadata in its
    response headers, such as the inference time and the model backend used.

    Args:
        payload: The request body, which should be a `TextInput` object
            containing the text to be analyzed.
        response: The FastAPI `Response` object, used to set custom headers
            with metadata about the prediction.
        prediction_service: The prediction service, injected as a dependency,
            which encapsulates the business logic for making predictions.
        backend: The name of the model backend in use (e.g., 'pytorch', 'onnx'),
            injected as a dependency.
        settings: The application's configuration settings, injected as a
            dependency.

    Returns:
        A `PredictionResponse` object with the sentiment analysis results,
        including the predicted label and confidence score.

    Raises:
        HTTPException: If the input text is invalid, the model is not loaded,
            or if an unexpected error occurs during the prediction process.
    """
    # Create contextual logger for this request
    logger = get_contextual_logger(
        __name__,
        endpoint="predict",
        text_length=len(payload.text),
        backend=backend,
    )

    logger.info("Starting sentiment prediction", operation="predict_start")

    try:
        # Perform sentiment analysis through service
        result = prediction_service.predict(payload.text)
        
        # Generate unique prediction ID
        prediction_id = str(uuid.uuid4())
        result["prediction_id"] = prediction_id

        # Add inference time to response headers
        response.headers["X-Inference-Time-MS"] = str(result["inference_time_ms"])
        response.headers["X-Model-Backend"] = backend

        logger.info(
            "Sentiment prediction completed successfully",
            operation="predict_success",
            label=result["label"],
            score=result["score"],
            inference_time_ms=result["inference_time_ms"],
            cached=result.get("cached", False),
        )

        # Add backend to response
        result["backend"] = backend

        # Stream prediction to data lake asynchronously
        if settings.data_lake.data_lake_enabled:
            prediction_data = {
                "prediction_id": prediction_id,
                "text": payload.text,
                "label": result["label"],
                "score": result["score"],
                "inference_time_ms": result["inference_time_ms"],
                "backend": backend,
                "cached": result.get("cached", False),
                "features": result.get("features"),
            }
            # Fire and forget - don't await to keep response fast
            asyncio.create_task(data_writer.write_prediction(prediction_data))

        return PredictionResponse(**result)

    except ModelNotLoadedError as e:
        logger.error(
            "Model not ready for prediction",
            model_status="unavailable",
            operation="predict_failed",
        )
        raise

    except Exception as e:
        logger.error(
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
