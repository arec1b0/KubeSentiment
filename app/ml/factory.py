"""
Model factory for creating model instances based on backend selection.

This module provides a factory pattern implementation for instantiating
different model backends (PyTorch, ONNX) in a uniform way.
"""

from typing import Union

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ml.model_strategy import ModelBackend, ModelStrategy
from app.ml.onnx_optimizer import ONNXSentimentAnalyzer, get_onnx_sentiment_analyzer
from app.ml.sentiment import SentimentAnalyzer, get_sentiment_analyzer

logger = get_logger(__name__)


class ModelFactory:
    """Factory class for creating model instances based on backend type.

    This factory centralizes the logic for instantiating different model
    backends, making it easier to add new backends in the future and
    ensuring consistent model creation across the application.
    """

    @staticmethod
    def create_model(backend: str) -> Union[SentimentAnalyzer, ONNXSentimentAnalyzer]:
        """Creates and returns a model instance based on the specified backend.

        Args:
            backend: The model backend to use ('pytorch' or 'onnx').

        Returns:
            A model instance implementing the ModelStrategy protocol.

        Raises:
            ValueError: If an unsupported backend is specified.
        """
        settings = get_settings()
        backend_lower = backend.lower()

        logger.info(f"Creating model with backend: {backend_lower}")

        if backend_lower == ModelBackend.PYTORCH:
            return get_sentiment_analyzer()
        elif backend_lower == ModelBackend.ONNX:
            onnx_path = settings.onnx_model_path or settings.onnx_model_path_default
            return get_onnx_sentiment_analyzer(onnx_path)
        else:
            error_msg = f"Unsupported model backend: {backend}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    @staticmethod
    def get_available_backends() -> list[str]:
        """Returns a list of available model backends.

        Returns:
            A list of backend names that can be used with create_model().
        """
        return [ModelBackend.PYTORCH, ModelBackend.ONNX]
