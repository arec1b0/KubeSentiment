"""
Base protocol for model strategies.

This module defines the ModelStrategy protocol, which provides a common interface
for all model implementations. This allows for interchangeable backends (PyTorch,
ONNX, etc.) while maintaining a consistent API throughout the application.

It also provides BaseModelMetrics, a base class that implements shared
metrics tracking functionality to reduce code duplication across model backends.
"""

from typing import Any, Protocol, runtime_checkable


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

    def predict(self, text: str) -> dict[str, Any]:
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

    def predict_batch(self, texts: list[str]) -> list[dict[str, Any]]:
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

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the model.

        Returns:
            A dictionary containing model information such as:
                - model_name: The name/identifier of the model
                - backend: The backend being used (pytorch, onnx, etc.)
                - device: The device the model is running on
                - Any other relevant model metadata
        """
        ...

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics for the model.

        Returns:
            A dictionary containing performance metrics such as:
                - total_predictions: Total number of predictions made
                - avg_inference_time_ms: Average inference time in milliseconds
                - cache_hit_rate: Cache hit rate (if caching is enabled)
                - Any other relevant performance metrics
        """
        ...


class BaseModelMetrics:
    """Base class for model metrics tracking.

    This class provides shared functionality for tracking performance metrics
    across different model backends. It implements common patterns for:
    - Prediction counting
    - Inference time tracking
    - Cache hit/miss statistics
    - Performance metrics calculation

    Subclasses must implement a _cached_predict method decorated with
    @lru_cache(maxsize=N) that returns a tuple of (label, score).

    Attributes:
        _prediction_count: Total number of predictions made.
        _total_inference_time: Cumulative inference time in seconds.
        _cache_hits: Number of cache hits.
        _cache_misses: Number of cache misses.
    """

    def __init__(self) -> None:
        """Initialize metrics tracking attributes."""
        self._prediction_count: int = 0
        self._total_inference_time: float = 0.0
        self._cache_hits: int = 0
        self._cache_misses: int = 0

    def _track_cache_stats(self, cache_info_before: Any, cache_info_after: Any) -> bool:
        """Track cache statistics by comparing cache info before and after prediction.

        Args:
            cache_info_before: Cache info before prediction.
            cache_info_after: Cache info after prediction.

        Returns:
            True if cache hit occurred, False otherwise.
        """
        if cache_info_after.hits > cache_info_before.hits:
            self._cache_hits += 1
            return True
        else:
            self._cache_misses += 1
            return False

    def _update_metrics(self, inference_time: float, prediction_count: int = 1) -> None:
        """Update prediction metrics.

        Args:
            inference_time: Time taken for inference in seconds.
            prediction_count: Number of predictions made (default: 1).
        """
        self._prediction_count += prediction_count
        self._total_inference_time += inference_time

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics for the model.

        Returns:
            A dictionary containing performance statistics including:
                - total_predictions: Total number of predictions made
                - avg_inference_time_ms: Average inference time in milliseconds
                - total_inference_time_seconds: Total cumulative inference time
                - cache_hits: Number of cache hits
                - cache_misses: Number of cache misses
                - cache_hit_rate: Ratio of cache hits to total cache requests
                - cache_info: Detailed LRU cache information
        """
        cache_info = self._cached_predict.cache_info()
        total_cache_requests = self._cache_hits + self._cache_misses
        cache_hit_rate = (
            self._cache_hits / total_cache_requests if total_cache_requests > 0 else 0.0
        )

        avg_inference_time = (
            (self._total_inference_time / self._prediction_count) * 1000
            if self._prediction_count > 0
            else 0.0
        )

        return {
            "total_predictions": self._prediction_count,
            "avg_inference_time_ms": avg_inference_time,
            "total_inference_time_seconds": self._total_inference_time,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": cache_hit_rate,
            "cache_info": {
                "hits": cache_info.hits,
                "misses": cache_info.misses,
                "maxsize": cache_info.maxsize,
                "currsize": cache_info.currsize,
            },
        }

    def clear_cache(self) -> None:
        """Clear the prediction cache.

        This method clears the LRU cache, forcing all subsequent predictions
        to be recomputed.
        """
        self._cached_predict.cache_clear()
