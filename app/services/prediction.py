"""
Prediction service for the MLOps sentiment analysis service.

This module encapsulates the business logic for making predictions, acting as
an intermediary between the API layer and the underlying machine learning
model. It ensures that concerns are properly separated and provides a clean
interface for the rest of the application to interact with the model.
"""

from typing import Any, Dict, List

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.feature_engineering import FeatureEngineer
from app.interfaces.prediction_interface import IPredictionService
from app.models.base import ModelStrategy
from app.utils.exceptions import ModelNotLoadedError, TextEmptyError, TextTooLongError

logger = get_logger(__name__)


class PredictionService(IPredictionService):
    """Orchestrates the sentiment analysis prediction workflow.

    This service class handles the core logic for making predictions. It
    validates the input, checks the model's readiness, and invokes the
    appropriate model backend. By decoupling the business logic from the API
    and model layers, it improves modularity and testability.

    Attributes:
        model: An instance of a class that implements the `ModelStrategy`
            protocol, providing an abstraction over the model backend.
        settings: The application's configuration settings.
        feature_engineer: An instance of the `FeatureEngineer` for extracting
            advanced text features.
    """

    def __init__(
        self,
        model: ModelStrategy,
        settings: Settings,
        feature_engineer: FeatureEngineer,
    ):
        """Initializes the prediction service.

        Args:
            model: An instance of a model strategy (e.g., PyTorch or ONNX).
            settings: The application's configuration settings.
            feature_engineer: An instance of the feature engineering service.
        """
        self.model = model
        self.settings = settings
        self.feature_engineer = feature_engineer
        self.logger = get_logger(__name__)

    def predict(self, text: str) -> Dict[str, Any]:
        """Performs sentiment analysis on a given text.

        This method handles input validation, checks the model's readiness,
        and then calls the `predict` method of the injected model strategy.
        If feature engineering is enabled, it also extracts and includes
        advanced features in the result.

        Args:
            text: The input text to be analyzed.

        Returns:
            A dictionary containing the prediction results, including the
            sentiment label, confidence score, and optional features.

        Raises:
            TextEmptyError: If the input text is empty or whitespace.
            TextTooLongError: If the input text exceeds the configured max length.
            ModelNotLoadedError: If the model is not loaded or ready for inference.
        """
        if not text or not text.strip():
            raise TextEmptyError()
        if len(text) > self.settings.max_text_length:
            raise TextTooLongError(len(text), self.settings.max_text_length)
        if not self.model.is_ready():
            raise ModelNotLoadedError(getattr(self.model.settings, "model_name", "unknown"))

        result = self.model.predict(text.strip())
        if self.settings.enable_feature_engineering:
            result["features"] = self.feature_engineer.extract_features(text.strip())

        return result

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Performs sentiment analysis on a batch of texts.

        This method leverages the model's batch prediction capabilities for
        improved performance. It validates each text in the batch and returns
        a list of results.

        Args:
            texts: A list of input texts to be analyzed.

        Returns:
            A list of dictionaries containing prediction results for each text.
        """
        if not self.model.is_ready():
            raise ModelNotLoadedError(getattr(self.model.settings, "model_name", "unknown"))

        # Pre-validate texts and prepare for batch prediction
        valid_texts = [
            t.strip() if t and t.strip() and len(t) <= self.settings.max_text_length else None
            for t in texts
        ]

        # Get predictions for valid texts
        results = self.model.predict_batch([t for t in valid_texts if t is not None])

        # Merge results with placeholders for invalid texts
        final_results = []
        result_iter = iter(results)
        for text in valid_texts:
            if text is None:
                final_results.append({"error": "Invalid input"})
            else:
                final_results.append(next(result_iter))
        return final_results
