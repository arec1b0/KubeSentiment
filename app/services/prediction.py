"""
Prediction service for business logic.

This service encapsulates the business logic for making predictions,
separating it from the API and model layers.
"""

from typing import Any, Dict, List

from app.core.config import Settings
from app.core.logging import get_contextual_logger, get_logger
from app.models.base import ModelStrategy
from app.utils.exceptions import ModelNotLoadedError, TextEmptyError, TextTooLongError

logger = get_logger(__name__)


class PredictionService:
    """Orchestrates the sentiment analysis prediction workflow.

    This service class acts as an intermediary between the API layer and the
    model layer. It encapsulates the business logic for making predictions,
    ensuring that concerns are properly separated. It relies on a `ModelStrategy`
    instance, which is dependency-injected, allowing for flexibility in the
    choice of the underlying model backend.

    Attributes:
        model: An instance of a class that implements the `ModelStrategy`
            protocol.
        settings: The application's configuration settings.
        logger: A configured logger instance.
    """

    def __init__(self, model: ModelStrategy, settings: Settings):
        """Initializes the prediction service.

        Args:
            model: An instance of a model strategy (e.g., PyTorch or ONNX).
            settings: The application's configuration settings.
        """
        self.model = model
        self.settings = settings
        self.logger = get_logger(__name__)

    def predict(self, text: str) -> Dict[str, Any]:
        """Performs sentiment analysis on a given text.

        This method handles the core prediction logic. It first validates the
        input text and checks if the model is ready. It then calls the
        `predict` method of the injected model strategy and returns the result.

        Args:
            text: The input text to be analyzed.

        Returns:
            A dictionary containing the prediction results.

        Raises:
            TextEmptyError: If the input text is empty or contains only
                whitespace.
            ModelNotLoadedError: If the model is not loaded or ready for
                inference.
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
            raise TextEmptyError(context={"text_length": len(text) if text else 0})
        if len(text) > self.settings.max_text_length:
            raise TextTooLongError(text_length=len(text), max_length=self.settings.max_text_length)

        # Check model readiness
        if not self.model.is_ready():
            prediction_logger.error(
                "Model not ready for prediction",
                model_status="unavailable",
            )
            model_settings = getattr(self.model, "settings", None)
            model_name = model_settings.model_name if model_settings else "unknown"
            raise ModelNotLoadedError(
                model_name=model_name,
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

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Performs sentiment analysis on multiple texts using vectorized operations.

        This method provides significant performance improvements over sequential
        single predictions by leveraging batch processing and vectorization.

        Args:
            texts: A list of input texts to be analyzed.

        Returns:
            A list of dictionaries containing prediction results for each text.

        Raises:
            ValueError: If the input list is empty or all texts are empty.
            ModelNotLoadedError: If the model is not loaded or ready for inference.
        """
        # Create contextual logger for batch prediction
        batch_logger = get_contextual_logger(
            __name__,
            operation="batch_prediction_service",
            batch_size=len(texts),
        )

        batch_logger.debug("Starting batch prediction service", service="prediction")

        # Validate input
        if not texts or len(texts) == 0:
            raise ValueError("Batch must contain at least one text")

        # Filter empty and oversized texts
        validated_texts: List[str] = []
        errors: List[Dict[str, Any]] = []

        for idx, text in enumerate(texts):
            try:
                if not text or not text.strip():
                    errors.append({"index": idx, "error": "Empty text"})
                    validated_texts.append("")  # Placeholder
                elif len(text) > self.settings.max_text_length:
                    raise TextTooLongError(
                        text_length=len(text), max_length=self.settings.max_text_length
                    )
                else:
                    validated_texts.append(text.strip())
            except TextTooLongError:
                errors.append(
                    {
                        "index": idx,
                        "error": f"Text too long: {len(text)} > {self.settings.max_text_length}",
                    }
                )
                validated_texts.append("")  # Placeholder

        # Check if we have any valid texts
        valid_count = sum(1 for t in validated_texts if t)
        if valid_count == 0:
            raise ValueError("All texts in batch are empty or invalid")

        # Check model readiness
        if not self.model.is_ready():
            batch_logger.error(
                "Model not ready for batch prediction",
                model_status="unavailable",
            )
            model_settings = getattr(self.model, "settings", None)
            model_name = model_settings.model_name if model_settings else "unknown"
            raise ModelNotLoadedError(
                model_name=model_name,
                context={"service": "batch_prediction"},
            )

        # Perform batch prediction
        try:
            results = self.model.predict_batch(validated_texts)

            # Mark error results
            for error_info in errors:
                error_idx = error_info["index"]
                if isinstance(error_idx, int):
                    results[error_idx] = {
                        "label": "ERROR",
                        "score": 0.0,
                        "error": error_info["error"],
                        "inference_time_ms": 0.0,
                    }

            batch_logger.info(
                "Batch prediction completed successfully",
                batch_size=len(texts),
                valid_predictions=valid_count,
                errors=len(errors),
            )

            return results

        except Exception as e:
            batch_logger.error(
                "Batch prediction failed in service layer",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

    def get_model_status(self) -> Dict[str, Any]:
        """Retrieves the current status and information about the model.

        Returns:
            A dictionary containing the model's readiness status and other
            metadata.
        """
        return {
            "is_ready": self.model.is_ready(),
            "model_info": self.model.get_model_info(),
        }

    def clear_cache(self) -> Dict[str, str]:
        """Clears the prediction cache of the underlying model.

        This method checks if the injected model strategy supports cache
        clearing and, if so, invokes it.

        Returns:
            A dictionary indicating the status of the cache clearing operation.
        """
        if hasattr(self.model, "clear_cache"):
            self.model.clear_cache()
            self.logger.info("Prediction cache cleared")
            return {"status": "cache_cleared"}
        else:
            self.logger.warning("Model does not support cache clearing")
            return {"status": "not_supported"}
