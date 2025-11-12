"""
Base protocol for model strategies.

This module defines the ModelStrategy protocol, which provides a common interface
for all model implementations. This allows for interchangeable backends (PyTorch,
ONNX, etc.) while maintaining a consistent API throughout the application.
"""

from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class ModelStrategy(Protocol):
    """Protocol defining the interface for model implementations.

    This protocol ensures that all model backends (PyTorch, ONNX, etc.)
    provide the same interface, allowing them to be used interchangeably
    throughout the application via the Strategy pattern.

    All implementations must provide methods for:
    - Checking model readiness
    - Making predictions (single and batch)
    - Retrieving model information and performance metrics
    """

    settings: Any

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready for inference.

        Returns:
            True if the model is loaded and ready, False otherwise.
        """
        ...

    def predict(self, text: str) -> Dict[str, Any]:
        """Perform sentiment analysis on a single text input.

        Args:
            text: The input text to analyze.

        Returns:
            A dictionary containing prediction results with at least:
                - label: The predicted sentiment label
                - score: The confidence score for the prediction
                - inference_time_ms: The time taken for inference in milliseconds

        Raises:
            ModelNotLoadedError: If the model is not loaded.
            TextEmptyError: If the input text is empty.
            ModelInferenceError: If inference fails.
        """
        ...

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Perform sentiment analysis on a batch of texts.

        Args:
            texts: A list of input texts to analyze.

        Returns:
            A list of dictionaries containing prediction results for each text.

        Raises:
            ModelNotLoadedError: If the model is not loaded.
            ModelInferenceError: If inference fails.
        """
        ...

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model.

        Returns:
            A dictionary containing model information such as:
                - model_name: The name/identifier of the model
                - backend: The backend being used (pytorch, onnx, etc.)
                - device: The device the model is running on
                - Any other relevant model metadata
        """
        ...

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the model.

        Returns:
            A dictionary containing performance metrics such as:
                - total_predictions: Total number of predictions made
                - avg_inference_time_ms: Average inference time in milliseconds
                - cache_hit_rate: Cache hit rate (if caching is enabled)
                - Any other relevant performance metrics
        """
        ...
