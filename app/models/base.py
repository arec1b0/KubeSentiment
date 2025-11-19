"""
Base protocol for model strategies.

This module defines the ModelStrategy protocol, which provides a common interface
for all model implementations. This allows for interchangeable backends (PyTorch,
ONNX, etc.) while maintaining a consistent API throughout the application.

It also provides the BaseModelMetrics class for shared metrics tracking across
all model implementations.
"""

from typing import Any, Protocol, runtime_checkable


class BaseModelMetrics:
    """Base class for tracking model performance metrics.

    This class provides shared metrics tracking functionality for all model
    backends, implementing the DRY principle by centralizing metrics collection
    and reporting.

    Attributes:
        _prediction_count: Total number of predictions made.
        _total_inference_time: Cumulative inference time in seconds.
        _cache_hits: Number of cache hits.
        _cache_misses: Number of cache misses.
    """

    def __init__(self) -> None:
        """Initialize metrics tracking."""
        self._prediction_count: int = 0
        self._total_inference_time: float = 0.0
        self._cache_hits: int = 0
        self._cache_misses: int = 0

    def update_prediction_metrics(self, inference_time: float, count: int = 1) -> None:
        """Update prediction count and inference time metrics.

        Args:
            inference_time: Time taken for inference in seconds.
            count: Number of predictions made (default: 1).
        """
        self._prediction_count += count
        self._total_inference_time += inference_time

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self._cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self._cache_misses += 1

    def track_cache_operation(self, cache_func: Any) -> Any:
        """Get cache info before a cached operation.

        This method should be called before executing a cached function
        to capture the cache state.

        Args:
            cache_func: The LRU cached function to track.

        Returns:
            Cache info before the operation.
        """
        return cache_func.cache_info()

    def update_cache_stats(self, cache_func: Any, cache_info_before: Any) -> bool:
        """Update cache statistics after a cached operation.

        Compares the cache state before and after an operation to determine
        if it was a cache hit or miss.

        Args:
            cache_func: The LRU cached function.
            cache_info_before: Cache info before the operation.

        Returns:
            True if it was a cache hit, False if it was a cache miss.
        """
        cache_info_after = cache_func.cache_info()
        if cache_info_after.hits > cache_info_before.hits:
            self.record_cache_hit()
            return True
        else:
            self.record_cache_miss()
            return False

    def get_performance_metrics(self, cache_func: Any | None = None) -> dict[str, Any]:
        """Get performance metrics.

        Args:
            cache_func: Optional LRU cached function to get cache info from.

        Returns:
            A dictionary containing performance statistics including:
                - total_predictions: Total number of predictions made
                - avg_inference_time_ms: Average inference time in milliseconds
                - total_inference_time_seconds: Total inference time in seconds
                - cache_hits: Number of cache hits
                - cache_misses: Number of cache misses
                - cache_hit_rate: Cache hit rate (0.0 to 1.0)
                - cache_info: Detailed cache information (if cache_func provided)
        """
        total_cache_requests = self._cache_hits + self._cache_misses
        cache_hit_rate = (
            self._cache_hits / total_cache_requests if total_cache_requests > 0 else 0.0
        )

        avg_inference_time = (
            (self._total_inference_time / self._prediction_count) * 1000
            if self._prediction_count > 0
            else 0.0
        )

        metrics = {
            "total_predictions": self._prediction_count,
            "avg_inference_time_ms": avg_inference_time,
            "total_inference_time_seconds": self._total_inference_time,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": cache_hit_rate,
        }

        # Add detailed cache info if provided
        if cache_func is not None:
            cache_info = cache_func.cache_info()
            metrics["cache_info"] = {
                "hits": cache_info.hits,
                "misses": cache_info.misses,
                "maxsize": cache_info.maxsize,
                "currsize": cache_info.currsize,
            }

        return metrics

    def reset_metrics(self) -> None:
        """Reset all metrics to zero.

        This is useful for testing or when you want to start fresh metrics collection.
        """
        self._prediction_count = 0
        self._total_inference_time = 0.0
        self._cache_hits = 0
        self._cache_misses = 0


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
