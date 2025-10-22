"""
Sentiment analysis model management.

This module handles model loading, caching, and prediction logic
for sentiment analysis using Hugging Face transformers.
"""

import hashlib
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

import torch
from transformers import Pipeline, pipeline

from ..config import get_settings
from ..exceptions import InvalidModelError, ModelInferenceError, ModelNotLoadedError, TextEmptyError
from ..logging_config import (
    get_contextual_logger,
    get_logger,
    log_model_operation,
    log_security_event,
)

# Import monitoring at module level to avoid circular imports
try:
    from ..monitoring import get_metrics

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

logger = get_logger(__name__)


class SentimentAnalyzer:
    """Manages sentiment analysis using a Hugging Face transformer model.

    This class encapsulates the logic for loading a sentiment analysis model,
    performing predictions, and caching results. It is designed to be a
    self-contained component that can be easily integrated into the application.
    It includes an LRU cache for predictions to improve performance for
    repeated requests.

    Attributes:
        settings: The application's configuration settings.
    """

    def __init__(self):
        """Initializes the sentiment analyzer and loads the model."""
        self.settings = get_settings()
        self._pipeline: Optional[Pipeline] = None
        self._is_loaded = False
        # Use OrderedDict for LRU cache with O(1) operations
        self._prediction_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._cache_max_size = self.settings.prediction_cache_max_size
        self._load_model()

    def _get_cache_key(self, text: str) -> str:
        """Generates a secure and efficient cache key for a given text.

        This method uses the BLAKE2b hashing algorithm, which is faster than
        SHA-256 while providing a high level of security against collisions,
        making it suitable for use in a caching system.

        Args:
            text: The input text to be hashed.

        Returns:
            A hexadecimal string representing the hash of the text.
        """
        # Create a hash of the text for cache key using BLAKE2b with 16-byte digest
        return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()

    def _get_cached_prediction(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a prediction from the cache if it exists.

        This method implements an LRU (Least Recently Used) caching policy by
        moving any accessed item to the end of the `OrderedDict`, which marks
        it as recently used.

        Args:
            cache_key: The cache key for the desired prediction.

        Returns:
            The cached prediction dictionary, or `None` if not found.
        """
        if cache_key in self._prediction_cache:
            # Move to end to mark as recently used (LRU)
            self._prediction_cache.move_to_end(cache_key)
            cached_result = self._prediction_cache[cache_key]
            logger.debug(f"Cache hit for text hash: {cache_key[:8]}...")
            return cached_result
        return None

    def _cache_prediction(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Adds a prediction to the cache and handles eviction.

        If the cache is full, this method evicts the least recently used item
        before adding the new one. The `OrderedDict`'s behavior ensures that
        the item at the beginning of the dictionary is the LRU item.

        Args:
            cache_key: The key under which to store the prediction.
            result: The prediction dictionary to be cached.
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
        """Clears all entries from the prediction cache."""
        cache_size = len(self._prediction_cache)
        self._prediction_cache.clear()
        logger.info(f"Cleared prediction cache ({cache_size} entries)")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Retrieves statistics about the prediction cache.

        Returns:
            A dictionary containing the current and maximum size of the cache.
        """
        return {
            "cache_size": len(self._prediction_cache),
            "cache_max_size": self._cache_max_size,
            "cache_hit_ratio": 0.0,  # Could be implemented with hit/miss counters
        }

    def _validate_model_name(self, model_name: str) -> None:
        """Validates the model name against an allowed list from the settings.

        This is a security measure to prevent the loading of arbitrary,
        potentially malicious models from the Hugging Face Hub.

        Args:
            model_name: The name of the model to be validated.

        Raises:
            InvalidModelError: If the model name is not in the allowed list.
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
        """Loads the sentiment analysis model from Hugging Face.

        This method initializes the Hugging Face pipeline for sentiment
        analysis. It first validates the model name for security. If the model
        fails to load, the analyzer will be in a non-ready state.
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
        """Checks if the model is loaded and ready for inference.

        Returns:
            `True` if the model is loaded, `False` otherwise.
        """
        return self._is_loaded and self._pipeline is not None

    def _validate_input_text(self, text: str, logger) -> None:
        """Validates the input text and ensures the model is ready.

        Args:
            text: The input text to be validated.
            logger: The logger instance for this request.

        Raises:
            ModelNotLoadedError: If the model is not loaded and ready.
            TextEmptyError: If the input text is empty or contains only
                whitespace.
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

    def _try_get_cached_result(self, text: str, logger) -> Optional[Dict[str, Any]]:
        """Attempts to retrieve a prediction from the cache.

        Args:
            text: The input text for which to check the cache.
            logger: The logger instance for this request.

        Returns:
            The cached prediction dictionary if found, otherwise `None`.
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
        """Preprocesses the input text before inference.

        Currently, this method's primary function is to truncate the text if
        it exceeds the maximum configured length.

        Args:
            text: The input text to be preprocessed.
            logger: The logger instance for this request.

        Returns:
            A tuple containing the processed text, the original text, and a
            boolean indicating if the text was truncated.
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
        """Runs the sentiment analysis model on the preprocessed text.

        Args:
            text: The preprocessed (and possibly truncated) text.
            original_text: The original, unprocessed text.
            logger: The logger instance for this request.

        Returns:
            A tuple containing the prediction result dictionary and the
            inference time in milliseconds.

        Raises:
            ModelInferenceError: If an error occurs during the model's
                prediction process.
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
        """Records Prometheus metrics for a prediction.

        If monitoring is enabled, this method updates the relevant Prometheus
        metrics, such as inference duration and prediction scores.

        Args:
            score: The confidence score of the prediction.
            text_length: The length of the input text.
            inference_time_ms: The inference time in milliseconds.
        """
        if MONITORING_AVAILABLE:
            metrics = get_metrics()
            metrics.record_inference_duration(inference_time_ms / 1000)  # Convert to seconds
            metrics.record_prediction_metrics(score, text_length)

    def predict(self, text: str) -> Dict[str, Any]:
        """Performs sentiment analysis on a given text.

        This method orchestrates the entire prediction process, including input
        validation, cache checking, text preprocessing, model inference, and
        result caching.

        Args:
            text: The input text to be analyzed.

        Returns:
            A dictionary containing the prediction results.

        Raises:
            ModelNotLoadedError: If the model is not ready for inference.
            TextEmptyError: If the input text is empty.
            ModelInferenceError: If an error occurs during inference.
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
        """Retrieves metadata about the PyTorch model and its environment.

        Returns:
            A dictionary containing details about the model, its readiness,
            and the underlying PyTorch and CUDA environment.
        """
        cache_stats = self.get_cache_stats()
        return {
            "model_name": self.settings.model_name,
            "is_loaded": self._is_loaded,
            "is_ready": self.is_ready(),
            "cache_dir": self.settings.model_cache_dir,
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "cache_stats": cache_stats,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Retrievess performance metrics, particularly related to CUDA.

        Returns:
            A dictionary of performance metrics, including CUDA memory usage if
            a GPU is available.
        """
        metrics = {
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
        }

        if torch.cuda.is_available():
            metrics.update(
                {
                    "cuda_memory_allocated_mb": round(torch.cuda.memory_allocated() / 1e6, 2),
                    "cuda_memory_reserved_mb": round(torch.cuda.memory_reserved() / 1e6, 2),
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
    """Creates and retrieves a singleton instance of the sentiment analyzer.

    This factory function uses `@lru_cache(maxsize=1)` to ensure that only one
    instance of the `SentimentAnalyzer` is created. This approach provides
    thread-safe, singleton-like behavior, which is efficient for managing a
    resource-intensive object like a model.

    Returns:
        The singleton instance of the `SentimentAnalyzer`.
    """
    return SentimentAnalyzer()


def reset_sentiment_analyzer() -> None:
    """Resets the singleton instance of the sentiment analyzer.

    This function is primarily intended for use in testing scenarios where a
    fresh instance of the analyzer is needed for different test cases. It
    works by clearing the cache of the `get_sentiment_analyzer` function.
    """
    get_sentiment_analyzer.cache_clear()
