"""
Sentiment analysis model management.

This module handles model loading, caching, and prediction logic
for sentiment analysis using Hugging Face transformers.
"""

import time
import hashlib
from typing import Dict, Optional, Any
from collections import OrderedDict

import torch
from transformers import pipeline, Pipeline

from ..config import get_settings
from ..logging_config import (
    get_logger,
    log_model_operation,
    log_security_event,
    get_contextual_logger,
)
from ..exceptions import (
    ModelNotLoadedError,
    ModelInferenceError,
    InvalidModelError,
    TextEmptyError,
)

# Import monitoring at module level to avoid circular imports
try:
    from ..monitoring import get_metrics

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

logger = get_logger(__name__)


class SentimentAnalyzer:
    """
    A wrapper class for sentiment analysis using Hugging Face transformers.

    This class provides methods for model loading, prediction, and performance monitoring
    with proper error handling and graceful degradation.
    """

    def __init__(self):
        """Initialize the sentiment analyzer."""
        self.settings = get_settings()
        self._pipeline: Optional[Pipeline] = None
        self._is_loaded = False
        # Use OrderedDict for LRU cache with O(1) operations
        self._prediction_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._cache_max_size = self.settings.prediction_cache_max_size
        self._load_model()

    def _get_cache_key(self, text: str) -> str:
        """
        Generate a cache key for the given text.

        Uses BLAKE2b for fast and secure cache key generation.
        BLAKE2b is 8x faster than SHA-256 while providing equivalent security.

        Args:
            text: The input text

        Returns:
            str: A hash-based cache key
        """
        # Create a hash of the text for cache key using BLAKE2b with 16-byte digest
        return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()

    def _get_cached_prediction(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached prediction if it exists.

        Implements LRU behavior by moving accessed items to the end of the OrderedDict.

        Args:
            cache_key: The cache key to look up

        Returns:
            Optional[Dict[str, Any]]: Cached prediction result or None
        """
        if cache_key in self._prediction_cache:
            # Move to end to mark as recently used (LRU)
            self._prediction_cache.move_to_end(cache_key)
            cached_result = self._prediction_cache[cache_key]
            logger.debug(f"Cache hit for text hash: {cache_key[:8]}...")
            return cached_result
        return None

    def _cache_prediction(self, cache_key: str, result: Dict[str, Any]) -> None:
        """
        Cache a prediction result with LRU eviction.

        Implements LRU (Least Recently Used) eviction strategy when cache size limit is reached.
        Uses OrderedDict for O(1) eviction of least recently used items.

        Args:
            cache_key: The cache key
            result: The prediction result to cache
        """
        if len(self._prediction_cache) >= self._cache_max_size:
            # Remove least recently used entry (first item in OrderedDict)
            lru_key = next(iter(self._prediction_cache))
            del self._prediction_cache[lru_key]
            logger.debug(f"Cache eviction: removed LRU entry {lru_key[:8]}...")

        # Add new entry (will be at the end as most recently used)
        self._prediction_cache[cache_key] = result
        logger.debug(f"Cached prediction for text hash: {cache_key[:8]}...")

    def clear_cache(self) -> None:
        """
        Clear all cached predictions.
        """
        cache_size = len(self._prediction_cache)
        self._prediction_cache.clear()
        logger.info(f"Cleared prediction cache ({cache_size} entries)")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict[str, Any]: Cache statistics
        """
        return {
            "cache_size": len(self._prediction_cache),
            "cache_max_size": self._cache_max_size,
            "cache_hit_ratio": 0.0,  # Could be implemented with hit/miss counters
        }

    def _validate_model_name(self, model_name: str) -> None:
        """
        Validate that the model name is in the allowed list.

        Security-critical function that prevents loading of unauthorized models
        which could lead to code execution or data exfiltration vulnerabilities.

        Args:
            model_name: The model name to validate

        Raises:
            ValueError: If model name is not in the allowed list
        """
        if model_name not in self.settings.allowed_models:
            log_security_event(
                logger,
                "invalid_model_name",
                {
                    "requested_model": model_name,
                    "allowed_models": self.settings.allowed_models,
                },
            )
            raise InvalidModelError(
                model_name=model_name,
                allowed_models=self.settings.allowed_models,
                context={"requested_model": model_name},
            )

        logger.info(
            "Model name validation passed",
            model_name=model_name,
            operation_type="validation",
        )

    def _load_model(self) -> None:
        """
        Load the sentiment analysis model from Hugging Face.

        Attempts to load the specified model using the transformers pipeline.
        Model validation is performed before loading to prevent security issues.
        If loading fails, the analyzer will operate in degraded mode with is_ready() returning False.

        Side Effects:
            - Updates self._pipeline and self._is_loaded
            - Updates monitoring metrics if available
            - Logs model loading events
        """
        try:
            # Validate model name first
            self._validate_model_name(self.settings.model_name)

            start_time = time.time()
            logger.info(
                "Starting model loading",
                model_name=self.settings.model_name,
                operation_type="model",
                operation="load_start",
            )

            if self.settings.model_cache_dir:
                self._pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.settings.model_name,
                    model_kwargs={"cache_dir": self.settings.model_cache_dir},
                )
            else:
                self._pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.settings.model_name,
                )

            self._is_loaded = True
            duration_ms = (time.time() - start_time) * 1000
            log_model_operation(
                logger,
                "load",
                self.settings.model_name,
                duration_ms=duration_ms,
                success=True,
            )

            # Update metrics
            if MONITORING_AVAILABLE:
                metrics = get_metrics()
                metrics.set_model_status(True)

        except Exception as e:
            log_model_operation(
                logger, "load", self.settings.model_name, success=False, error=str(e)
            )
            self._pipeline = None
            self._is_loaded = False

            # Update metrics
            if MONITORING_AVAILABLE:
                metrics = get_metrics()
                metrics.set_model_status(False)

    def is_ready(self) -> bool:
        """
        Check if the model is loaded and ready for predictions.

        Returns:
            bool: True if the model is ready, False otherwise
        """
        return self._is_loaded and self._pipeline is not None

    def _validate_input_text(self, text: str, logger) -> None:
        """
        Validate input text and model readiness.

        Args:
            text: The input text to validate
            logger: Logger instance for this request

        Raises:
            ModelNotLoadedError: If model is not ready
            TextEmptyError: If text is empty or whitespace
        """
        if not self.is_ready():
            logger.error(
                "Model not ready for prediction",
                model_loaded=self._is_loaded,
                operation_stage="validation_failed",
            )
            raise ModelNotLoadedError(
                model_name=self.settings.model_name, context={"operation": "prediction"}
            )

        if not text or not text.strip():
            logger.error(
                "Empty text provided for prediction",
                operation_stage="validation_failed",
            )
            raise TextEmptyError(
                context={
                    "operation": "prediction",
                    "text_length": len(text) if text else 0,
                }
            )

    def _try_get_cached_result(
        self, text: str, logger
    ) -> Optional[Dict[str, Any]]:
        """
        Try to retrieve a cached prediction result.

        Args:
            text: The input text
            logger: Logger instance for this request

        Returns:
            Optional[Dict[str, Any]]: Cached result if found, None otherwise
        """
        cache_key = self._get_cache_key(text.strip())
        logger.debug("Generated cache key", cache_key_prefix=cache_key[:8])

        cached_result = self._get_cached_prediction(cache_key)
        if cached_result:
            logger.info(
                "Returning cached prediction result",
                operation_stage="cache_hit",
                label=cached_result["label"],
                score=cached_result["score"],
            )
            # Return cached result with cache indicator
            cached_result_copy = cached_result.copy()
            cached_result_copy["cached"] = True
            return cached_result_copy

        return None

    def _preprocess_text(self, text: str, logger) -> tuple[str, str, bool]:
        """
        Preprocess input text (truncation if needed).

        Args:
            text: The input text
            logger: Logger instance for this request

        Returns:
            tuple: (processed_text, original_text, was_truncated)
        """
        original_text = text
        text_truncated = False

        if len(text) > self.settings.max_text_length:
            text = text[: self.settings.max_text_length]
            text_truncated = True
            logger.warning(
                "Input text truncated for processing",
                original_length=len(original_text),
                truncated_length=len(text),
                max_length=self.settings.max_text_length,
                operation_stage="preprocessing",
            )

        return text, original_text, text_truncated

    def _run_model_inference(
        self, text: str, original_text: str, logger
    ) -> tuple[Dict[str, Any], float]:
        """
        Run the actual model inference.

        Args:
            text: The preprocessed text
            original_text: The original unprocessed text
            logger: Logger instance for this request

        Returns:
            tuple: (prediction_result, inference_time_ms)

        Raises:
            ModelInferenceError: If inference fails
        """
        start_time = time.time()
        logger.debug("Starting model inference", operation_stage="inference_start")

        try:
            # Perform prediction
            result = self._pipeline(text)[0]
            inference_time = (time.time() - start_time) * 1000

            prediction_result = {
                "label": result["label"],
                "score": float(result["score"]),
                "inference_time_ms": round(inference_time, 2),
                "model_name": self.settings.model_name,
                "text_length": len(original_text),
                "cached": False,
            }

            return prediction_result, inference_time

        except Exception as e:
            inference_time = (time.time() - start_time) * 1000
            logger.error(
                "Model inference failed",
                error=str(e),
                error_type=type(e).__name__,
                operation_stage="inference_failed",
                inference_time_ms=round(inference_time, 2),
                exc_info=True,
            )
            raise ModelInferenceError(
                message=f"Prediction failed: {str(e)}",
                model_name=self.settings.model_name,
                context={
                    "original_text_length": len(original_text),
                    "truncated_text_length": len(text),
                },
            )

    def _record_prediction_metrics(
        self, score: float, text_length: int, inference_time_ms: float
    ) -> None:
        """
        Record prediction metrics for monitoring.

        Args:
            score: The prediction confidence score
            text_length: Length of the input text
            inference_time_ms: Inference time in milliseconds
        """
        if MONITORING_AVAILABLE:
            metrics = get_metrics()
            metrics.record_inference_duration(inference_time_ms / 1000)  # Convert to seconds
            metrics.record_prediction_metrics(score, text_length)

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Perform sentiment analysis on the input text.

        This is the main orchestrator method that coordinates the prediction workflow
        using smaller, focused helper methods for better testability and maintainability.

        Args:
            text (str): The input text to analyze

        Returns:
            Dict[str, Any]: Prediction result with label, score, and metadata

        Raises:
            ModelNotLoadedError: If the model is not loaded
            TextEmptyError: If the input text is invalid
            ModelInferenceError: If prediction fails
        """
        # Create contextual logger for this prediction
        prediction_logger = get_contextual_logger(
            __name__,
            operation="prediction",
            model_name=self.settings.model_name,
            text_length=len(text) if text else 0,
        )

        prediction_logger.debug("Starting prediction", operation_stage="validation")

        # Step 1: Validate input
        self._validate_input_text(text, prediction_logger)

        # Step 2: Check cache
        cached_result = self._try_get_cached_result(text, prediction_logger)
        if cached_result:
            return cached_result

        # Step 3: Preprocess text
        processed_text, original_text, text_truncated = self._preprocess_text(
            text, prediction_logger
        )

        # Step 4: Run inference
        prediction_result, inference_time = self._run_model_inference(
            processed_text, original_text, prediction_logger
        )

        # Step 5: Cache the result
        cache_key = self._get_cache_key(text.strip())
        self._cache_prediction(cache_key, prediction_result)

        # Step 6: Log success
        prediction_logger.info(
            "Prediction completed successfully",
            operation_stage="inference_complete",
            label=prediction_result["label"],
            score=prediction_result["score"],
            inference_time_ms=prediction_result["inference_time_ms"],
            text_truncated=text_truncated,
            cache_stored=True,
        )

        # Step 7: Record metrics
        self._record_prediction_metrics(
            prediction_result["score"],
            len(original_text),
            inference_time,
        )

        return prediction_result

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dict[str, Any]: Model information and status
        """
        cache_stats = self.get_cache_stats()
        return {
            "model_name": self.settings.model_name,
            "is_loaded": self._is_loaded,
            "is_ready": self.is_ready(),
            "cache_dir": self.settings.model_cache_dir,
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count()
            if torch.cuda.is_available()
            else 0,
            "cache_stats": cache_stats,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the model.

        Returns:
            Dict[str, Any]: Performance metrics
        """
        metrics = {
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
        }

        if torch.cuda.is_available():
            metrics.update(
                {
                    "cuda_memory_allocated_mb": round(
                        torch.cuda.memory_allocated() / 1e6, 2
                    ),
                    "cuda_memory_reserved_mb": round(
                        torch.cuda.memory_reserved() / 1e6, 2
                    ),
                    "cuda_device_count": torch.cuda.device_count(),
                }
            )
        else:
            metrics.update(
                {
                    "cuda_memory_allocated_mb": 0,
                    "cuda_memory_reserved_mb": 0,
                    "cuda_device_count": 0,
                }
            )

        return metrics


from functools import lru_cache


@lru_cache(maxsize=1)
def get_sentiment_analyzer() -> SentimentAnalyzer:
    """
    Dependency injection function to get the sentiment analyzer.

    Uses lru_cache to ensure a single instance per application,
    providing proper singleton behavior without global state.
    This is thread-safe and can be easily mocked for testing.

    Returns:
        SentimentAnalyzer: The sentiment analyzer instance
    """
    return SentimentAnalyzer()


def reset_sentiment_analyzer() -> None:
    """
    Reset the analyzer instance (useful for testing).

    Clears the lru_cache to allow a fresh instance to be created.
    """
    get_sentiment_analyzer.cache_clear()
