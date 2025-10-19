"""
Prediction endpoints.
"""

from fastapi import APIRouter, Depends, Response

from app.api.schemas.requests import TextInput
from app.api.schemas.responses import PredictionResponse
from app.core.config import Settings, get_settings
from app.core.dependencies import get_model_backend, get_prediction_service
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
) -> PredictionResponse:
    """
    Analyze sentiment of the input text.

    Args:
        payload: The input text data
        response: FastAPI response object for headers
        prediction_service: The prediction service
        backend: The backend being used
        settings: Application settings

    Returns:
        PredictionResponse: Sentiment prediction results

    Raises:
        HTTPException: If the model is unavailable or prediction fails
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

