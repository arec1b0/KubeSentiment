"""
Sentiment analysis model management.

This module handles model loading, caching, and prediction logic
for sentiment analysis using Hugging Face transformers.
"""

import logging
import time
from typing import Dict, Optional, Any
from functools import lru_cache

import torch
from transformers import pipeline, Pipeline

from ..config import get_settings

logger = logging.getLogger(__name__)


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
        self._load_model()

    def _load_model(self) -> None:
        """
        Load the sentiment analysis model.

        Attempts to load the specified model from Hugging Face.
        If loading fails, the analyzer will operate in degraded mode.
        """
        try:
            logger.info(f"Loading sentiment analysis model: {self.settings.model_name}")

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
            logger.info("Sentiment analysis model loaded successfully")

            # Update metrics
            try:
                from ..monitoring import get_metrics

                metrics = get_metrics()
                metrics.set_model_status(True)
            except ImportError:
                pass

        except Exception as e:
            logger.error(f"Failed to load sentiment analysis model: {e}")
            self._pipeline = None
            self._is_loaded = False

            # Update metrics
            try:
                from ..monitoring import get_metrics

                metrics = get_metrics()
                metrics.set_model_status(False)
            except ImportError:
                pass

    def is_ready(self) -> bool:
        """
        Check if the model is loaded and ready for predictions.

        Returns:
            bool: True if the model is ready, False otherwise
        """
        return self._is_loaded and self._pipeline is not None

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Perform sentiment analysis on the input text.

        Args:
            text (str): The input text to analyze

        Returns:
            Dict[str, Any]: Prediction result with label, score, and metadata

        Raises:
            RuntimeError: If the model is not loaded
            ValueError: If the input text is invalid
        """
        if not self.is_ready():
            raise RuntimeError("Model is not loaded or unavailable")

        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        # Truncate text if too long
        if len(text) > self.settings.max_text_length:
            text = text[: self.settings.max_text_length]
            logger.warning(
                f"Input text truncated to {self.settings.max_text_length} characters"
            )

        start_time = time.time()

        try:
            # Perform prediction
            result = self._pipeline(text)[0]
            inference_time = (time.time() - start_time) * 1000

            # Record metrics (import here to avoid circular imports)
            try:
                from ..monitoring import get_metrics

                metrics = get_metrics()
                metrics.record_inference_duration(
                    inference_time / 1000
                )  # Convert to seconds
                metrics.record_prediction_metrics(float(result["score"]), len(text))
            except ImportError:
                # Metrics not available, continue without them
                pass

            return {
                "label": result["label"],
                "score": float(result["score"]),
                "inference_time_ms": round(inference_time, 2),
                "model_name": self.settings.model_name,
                "text_length": len(text),
            }

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise RuntimeError(f"Prediction failed: {str(e)}")

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dict[str, Any]: Model information and status
        """
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


# Global sentiment analyzer instance
_sentiment_analyzer: Optional[SentimentAnalyzer] = None


@lru_cache()
def get_sentiment_analyzer() -> SentimentAnalyzer:
    """
    Get the global sentiment analyzer instance.

    This function implements the singleton pattern to ensure
    only one model instance is loaded per application.

    Returns:
        SentimentAnalyzer: The sentiment analyzer instance
    """
    global _sentiment_analyzer

    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()

    return _sentiment_analyzer
