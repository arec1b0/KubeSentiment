"""
PyTorch-based sentiment analysis model implementation.

This module provides a PyTorch implementation of the sentiment analysis model
using Hugging Face Transformers. It implements the ModelStrategy protocol and
provides caching, metrics tracking, and comprehensive error handling.
"""

from functools import lru_cache
import time
from typing import Any, Optional

import torch
from transformers import pipeline

from app.core.config import Settings, get_settings
from app.core.logging import get_contextual_logger, get_logger
from app.models.base import BaseModelMetrics
from app.utils.exceptions import ModelInferenceError, ModelNotLoadedError, TextEmptyError

logger = get_logger(__name__)

# Singleton instance
_sentiment_analyzer_instance: Optional["SentimentAnalyzer"] = None


class SentimentAnalyzer(BaseModelMetrics):
    """PyTorch-based sentiment analysis model.

    This class provides sentiment analysis using a Hugging Face Transformers
    model loaded via the pipeline API. It implements the ModelStrategy protocol
    and includes features like prediction caching, performance metrics tracking,
    and batch prediction support.

    Inherits from BaseModelMetrics for shared metrics tracking functionality.

    Attributes:
        settings: Application configuration settings.
        _pipeline: The Hugging Face sentiment analysis pipeline.
        _is_loaded: Flag indicating whether the model is loaded.
        _device: The device being used for inference (cuda, mps, or cpu).
    """

    def __init__(self, settings: Settings | None = None):
        """Initialize the sentiment analyzer.

        Args:
            settings: Optional settings instance. If not provided, will use
                the default settings from get_settings().
        """
        super().__init__()  # Initialize BaseModelMetrics
        self.settings = settings or get_settings()
        self._pipeline = None
        self._is_loaded = False
        self._device = self._determine_device()

        # Initialize the model
        self._load_model()

    def _determine_device(self) -> str:
        """Determine the best available device for inference.

        Returns:
            Device string ('cuda', 'mps', or 'cpu').
        """
        if torch.cuda.is_available():
            device = "cuda"
            logger.info(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
            logger.info("Using Apple Metal Performance Shaders (MPS)")
        else:
            device = "cpu"
            logger.info("Using CPU for inference")
        return device

    def _load_model(self) -> None:
        """Load the sentiment analysis model.

        Raises:
            RuntimeError: If model loading fails.
        """
        try:
            logger.info(f"Loading model: {self.settings.model_name}")
            start_time = time.time()

            # Determine device index
            device = -1 if self._device == "cpu" else 0

            self._pipeline = pipeline(
                "sentiment-analysis",
                model=self.settings.model_name,
                device=device,
                model_kwargs=(
                    {"cache_dir": self.settings.model_cache_dir}
                    if self.settings.model_cache_dir
                    else {}
                ),
            )

            load_time = time.time() - start_time
            self._is_loaded = True
            logger.info(f"Model loaded successfully in {load_time:.2f} seconds")

        except Exception as e:
            logger.error(f"Failed to load model {self.settings.model_name}: {e}")
            self._is_loaded = False
            raise RuntimeError(f"Failed to load model: {e}") from e

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready for inference.

        Returns:
            True if the model is loaded, False otherwise.
        """
        return self._is_loaded and self._pipeline is not None

    def _validate_input_text(self, text: str, ctx_logger: Any) -> None:
        """Validate input text before prediction.

        Args:
            text: The input text to validate.
            ctx_logger: Contextual logger for logging validation issues.

        Raises:
            ModelNotLoadedError: If the model is not loaded.
            TextEmptyError: If the text is empty or whitespace-only.
        """
        if not self.is_ready():
            ctx_logger.error("Model not loaded")
            raise ModelNotLoadedError(self.settings.model_name)

        if not text or not text.strip():
            ctx_logger.error("Empty text provided")
            raise TextEmptyError()

    @lru_cache(maxsize=1000)
    def _cached_predict(self, text: str) -> tuple:
        """Internal cached prediction method.

        This method is cached using LRU cache to avoid recomputing predictions
        for identical inputs.

        Args:
            text: The input text to analyze.

        Returns:
            A tuple of (label, score) for the prediction.

        Raises:
            ModelInferenceError: If inference fails.
        """
        try:
            result = self._pipeline(text[: self.settings.max_text_length])[0]
            return (result["label"], result["score"])
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise ModelInferenceError(f"Model inference failed: {e}") from e

    def predict(self, text: str) -> dict[str, Any]:
        """Perform sentiment analysis on a single text input.

        Args:
            text: The input text to analyze.

        Returns:
            A dictionary containing:
                - label: The predicted sentiment label
                - score: The confidence score
                - inference_time_ms: Time taken for inference in milliseconds

        Raises:
            ModelNotLoadedError: If the model is not loaded.
            TextEmptyError: If the input text is empty.
            ModelInferenceError: If inference fails.
        """
        ctx_logger = get_contextual_logger(logger)
        ctx_logger.info("Starting prediction", extra={"text_length": len(text)})

        # Validate input
        self._validate_input_text(text, ctx_logger)

        # Clean and truncate text
        cleaned_text = text.strip()
        if len(cleaned_text) > self.settings.max_text_length:
            cleaned_text = cleaned_text[: self.settings.max_text_length]
            ctx_logger.warning(
                "Text truncated",
                extra={
                    "original_length": len(text),
                    "max_length": self.settings.max_text_length,
                },
            )

        # Perform prediction with timing
        start_time = time.time()

        # Check if result is cached
        cache_info_before = self._cached_predict.cache_info()

        try:
            label, score = self._cached_predict(cleaned_text)
        except Exception as e:
            ctx_logger.error("Prediction failed", extra={"error": str(e)})
            raise

        inference_time = time.time() - start_time
        inference_time_ms = inference_time * 1000

        # Update cache statistics
        cache_info_after = self._cached_predict.cache_info()
        is_cache_hit = self._track_cache_stats(cache_info_before, cache_info_after)
        ctx_logger.debug("Cache hit" if is_cache_hit else "Cache miss")

        # Update metrics
        self._update_metrics(inference_time, prediction_count=1)

        ctx_logger.info(
            "Prediction completed",
            extra={
                "label": label,
                "score": score,
                "inference_time_ms": inference_time_ms,
            },
        )

        return {
            "label": label,
            "score": float(score),
            "inference_time_ms": inference_time_ms,
        }

    def predict_batch(self, texts: list[str]) -> list[dict[str, Any]]:
        """Perform sentiment analysis on a batch of texts.

        This method uses the pipeline's native batch processing capabilities
        for improved performance compared to sequential predictions.

        Args:
            texts: A list of input texts to analyze.

        Returns:
            A list of dictionaries containing prediction results for each text.

        Raises:
            ModelNotLoadedError: If the model is not loaded.
            ModelInferenceError: If batch inference fails.
        """
        ctx_logger = get_contextual_logger(logger)
        ctx_logger.info("Starting batch prediction", extra={"batch_size": len(texts)})

        if not self.is_ready():
            raise ModelNotLoadedError(self.settings.model_name)

        if not texts:
            return []

        # Clean and truncate texts
        cleaned_texts = [
            t.strip()[: self.settings.max_text_length] if t and t.strip() else "" for t in texts
        ]

        # Filter out empty texts and track their indices
        valid_texts = []
        valid_indices = []
        for idx, text in enumerate(cleaned_texts):
            if text:
                valid_texts.append(text)
                valid_indices.append(idx)

        # Perform batch prediction
        start_time = time.time()

        try:
            if valid_texts:
                raw_results = self._pipeline(valid_texts)
            else:
                raw_results = []
        except Exception as e:
            ctx_logger.error("Batch prediction failed", extra={"error": str(e)})
            raise ModelInferenceError(f"Batch inference failed: {e}") from e

        inference_time = time.time() - start_time
        inference_time_ms = inference_time * 1000

        # Update metrics
        self._update_metrics(inference_time, prediction_count=len(valid_texts))

        # Build results array with placeholders for invalid texts
        results = []
        result_iter = iter(raw_results)

        for idx in range(len(texts)):
            if idx in valid_indices:
                result = next(result_iter)
                results.append(
                    {
                        "label": result["label"],
                        "score": float(result["score"]),
                        "inference_time_ms": inference_time_ms / len(valid_texts),
                    }
                )
            else:
                results.append(
                    {
                        "error": "Invalid or empty input",
                        "label": None,
                        "score": None,
                    }
                )

        ctx_logger.info(
            "Batch prediction completed",
            extra={
                "batch_size": len(texts),
                "valid_count": len(valid_texts),
                "total_inference_time_ms": inference_time_ms,
            },
        )

        return results

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the model.

        Returns:
            A dictionary containing model metadata.
        """
        cache_info = self._cached_predict.cache_info()

        return {
            "model_name": self.settings.model_name,
            "backend": "pytorch",
            "device": self._device,
            "is_loaded": self._is_loaded,
            "max_text_length": self.settings.max_text_length,
            "cache_size": cache_info.currsize,
            "cache_maxsize": cache_info.maxsize,
        }

    def clear_cache(self) -> None:
        """Clear the prediction cache.

        This method clears the LRU cache, forcing all subsequent predictions
        to be recomputed. Extends the base class method to add logging.
        """
        super().clear_cache()
        logger.info("Prediction cache cleared")


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get the singleton instance of the sentiment analyzer.

    This function implements the singleton pattern, ensuring that only one
    instance of the SentimentAnalyzer is created and reused across the
    application.

    Returns:
        The singleton SentimentAnalyzer instance.

    Example:
        >>> analyzer = get_sentiment_analyzer()
        >>> result = analyzer.predict("This is amazing!")
        >>> print(result['label'])
        'POSITIVE'
    """
    global _sentiment_analyzer_instance

    if _sentiment_analyzer_instance is None:
        logger.info("Creating new SentimentAnalyzer instance")
        _sentiment_analyzer_instance = SentimentAnalyzer()
    else:
        logger.debug("Returning existing SentimentAnalyzer instance")

    return _sentiment_analyzer_instance
