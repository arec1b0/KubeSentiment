"""
Prediction service for business logic.

This service encapsulates the business logic for making predictions,
separating it from the API and model layers.
"""

from typing import Any, Dict

from app.core.config import Settings
from app.core.logging import get_contextual_logger, get_logger
from app.models.base import ModelStrategy
from app.utils.exceptions import ModelNotLoadedError, TextEmptyError

logger = get_logger(__name__)


class PredictionService:
    """
    Service class for handling sentiment predictions.

    This class encapsulates the business logic for predictions,
    coordinating between models and providing a clean interface
    for the API layer.
    """

    def __init__(self, model: ModelStrategy, settings: Settings):
        """
        Initialize the prediction service.

        Args:
            model: The model strategy instance
            settings: Application settings
        """
        self.model = model
        self.settings = settings
        self.logger = get_logger(__name__)

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Perform sentiment prediction on input text.

        This method orchestrates the prediction workflow, including:
        - Input validation
        - Model readiness check
        - Prediction execution
        - Result post-processing

        Args:
            text: The input text to analyze

        Returns:
            Dict[str, Any]: Prediction result with label, score, and metadata

        Raises:
            ModelNotLoadedError: If the model is not ready
            TextEmptyError: If the input text is invalid
        """
        # Create contextual logger for this prediction
        prediction_logger = get_contextual_logger(
            __name__,
            operation="prediction_service",
            text_length=len(text) if text else 0,
        )

        prediction_logger.debug("Starting prediction service", service="prediction")

        # Validate input
        if not text or not text.strip():
            raise TextEmptyError(
                context={"text_length": len(text) if text else 0}
            )

        # Check model readiness
        if not self.model.is_ready():
            prediction_logger.error(
                "Model not ready for prediction",
                model_status="unavailable",
            )
            raise ModelNotLoadedError(
                model_name=getattr(self.model, "settings", None).model_name
                if hasattr(self.model, "settings")
                else "unknown",
                context={"service": "prediction"},
            )

        # Perform prediction
        try:
            result = self.model.predict(text.strip())

            prediction_logger.info(
                "Prediction completed successfully",
                label=result.get("label"),
                score=result.get("score"),
                inference_time_ms=result.get("inference_time_ms"),
            )

            return result

        except Exception as e:
            prediction_logger.error(
                "Prediction failed in service layer",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

    def get_model_status(self) -> Dict[str, Any]:
        """
        Get the current status of the model.

        Returns:
            Dict[str, Any]: Model status information
        """
        return {
            "is_ready": self.model.is_ready(),
            "model_info": self.model.get_model_info(),
        }

    def clear_cache(self) -> Dict[str, str]:
        """
        Clear the prediction cache.

        Returns:
            Dict[str, str]: Status message
        """
        if hasattr(self.model, "clear_cache"):
            self.model.clear_cache()
            self.logger.info("Prediction cache cleared")
            return {"status": "cache_cleared"}
        else:
            self.logger.warning("Model does not support cache clearing")
            return {"status": "not_supported"}

