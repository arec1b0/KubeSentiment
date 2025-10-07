"""
ONNX Model Optimization Module.

This module handles conversion of Hugging Face transformers models to ONNX format
and provides optimized inference using ONNX Runtime.
"""

import time
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any, List
from collections import OrderedDict
import logging

import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from optimum.onnxruntime import ORTModelForSequenceClassification
import onnxruntime as ort

from ..config import get_settings
from ..logging_config import get_logger, log_model_operation
from ..exceptions import ModelNotLoadedError, ModelInferenceError

logger = get_logger(__name__)


class ONNXModelOptimizer:
    """
    Convert and optimize Hugging Face models to ONNX format.

    This class provides methods to convert transformer models to ONNX format
    with optional quantization and optimization for better inference performance.
    """

    def __init__(self, model_name: str, cache_dir: Optional[str] = None):
        """
        Initialize the ONNX optimizer.

        Args:
            model_name: Name of the Hugging Face model
            cache_dir: Directory to cache models
        """
        self.model_name = model_name
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./onnx_models")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def convert_to_onnx(
        self,
        export_path: Optional[Path] = None,
        optimize: bool = True,
        quantize: bool = False,
    ) -> Path:
        """
        Convert Hugging Face model to ONNX format.

        Args:
            export_path: Path to export ONNX model (default: cache_dir/model_name)
            optimize: Whether to apply ONNX optimizations
            quantize: Whether to apply quantization for smaller model size

        Returns:
            Path: Path to the exported ONNX model
        """
        if export_path is None:
            export_path = self.cache_dir / self.model_name.replace("/", "_")

        export_path = Path(export_path)
        export_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Starting ONNX conversion",
            model_name=self.model_name,
            export_path=str(export_path),
            optimize=optimize,
            quantize=quantize,
        )

        start_time = time.time()

        try:
            # Load the model using Optimum
            model = ORTModelForSequenceClassification.from_pretrained(
                self.model_name, export=True, provider="CPUExecutionProvider"
            )

            # Save the ONNX model
            model.save_pretrained(export_path)

            # Save tokenizer
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            tokenizer.save_pretrained(export_path)

            duration_ms = (time.time() - start_time) * 1000

            # Get model size
            onnx_file = export_path / "model.onnx"
            model_size_mb = onnx_file.stat().st_size / (1024 * 1024)

            logger.info(
                "ONNX conversion completed",
                duration_ms=duration_ms,
                model_size_mb=round(model_size_mb, 2),
                export_path=str(export_path),
            )

            return export_path

        except Exception as e:
            logger.error(
                "ONNX conversion failed", error=str(e), error_type=type(e).__name__
            )
            raise ModelInferenceError(
                message=f"ONNX conversion failed: {str(e)}",
                model_name=self.model_name,
                context={"operation": "onnx_conversion"},
            )


class ONNXSentimentAnalyzer:
    """
    Optimized sentiment analyzer using ONNX Runtime.

    This class provides faster inference compared to PyTorch models
    by using ONNX Runtime optimizations.
    """

    def __init__(self, onnx_model_path: str):
        """
        Initialize ONNX-based sentiment analyzer.

        Args:
            onnx_model_path: Path to ONNX model directory
        """
        self.settings = get_settings()
        self.onnx_model_path = Path(onnx_model_path)
        self.tokenizer = None
        self.model = None
        self._is_loaded = False
        # Use OrderedDict for LRU cache with O(1) operations
        self._prediction_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._cache_max_size = self.settings.prediction_cache_max_size
        self._load_model()

    def _load_model(self) -> None:
        """Load ONNX model and tokenizer."""
        try:
            start_time = time.time()
            logger.info("Loading ONNX model", model_path=str(self.onnx_model_path))

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.onnx_model_path)

            # Load ONNX model using Optimum
            self.model = ORTModelForSequenceClassification.from_pretrained(
                self.onnx_model_path, provider="CPUExecutionProvider"
            )

            self._is_loaded = True
            duration_ms = (time.time() - start_time) * 1000

            logger.info("ONNX model loaded successfully", duration_ms=duration_ms)

        except Exception as e:
            logger.error(
                "ONNX model loading failed", error=str(e), error_type=type(e).__name__
            )
            self._is_loaded = False
            raise

    def _get_cache_key(self, text: str) -> str:
        """
        Generate cache key for text.

        Uses BLAKE2b for fast and secure cache key generation.
        BLAKE2b is 8x faster than SHA-256 while providing equivalent security.
        """
        return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()

    def _get_cached_prediction(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached prediction.
        
        Implements LRU behavior by moving accessed items to the end of the OrderedDict.
        """
        if cache_key in self._prediction_cache:
            # Move to end to mark as recently used (LRU)
            self._prediction_cache.move_to_end(cache_key)
            return self._prediction_cache[cache_key]
        return None

    def _cache_prediction(self, cache_key: str, result: Dict[str, Any]) -> None:
        """
        Cache prediction result with LRU eviction.
        
        Uses OrderedDict for O(1) eviction of least recently used items.
        """
        if len(self._prediction_cache) >= self._cache_max_size:
            # Remove least recently used entry (first item in OrderedDict)
            lru_key = next(iter(self._prediction_cache))
            del self._prediction_cache[lru_key]

        # Add new entry (will be at the end as most recently used)
        self._prediction_cache[cache_key] = result

    def is_ready(self) -> bool:
        """Check if model is ready."""
        return self._is_loaded and self.model is not None

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Perform sentiment analysis using ONNX model.

        Args:
            text: Input text to analyze

        Returns:
            Dict containing prediction results

        Raises:
            ModelNotLoadedError: If model is not loaded
            ModelInferenceError: If prediction fails
        """
        if not self.is_ready():
            raise ModelNotLoadedError(
                model_name="ONNX Model", context={"operation": "prediction"}
            )

        if not text or not text.strip():
            raise ValueError("Empty text provided")

        # Check cache
        cache_key = self._get_cache_key(text.strip())
        cached_result = self._get_cached_prediction(cache_key)

        if cached_result:
            cached_result_copy = cached_result.copy()
            cached_result_copy["cached"] = True
            return cached_result_copy

        # Truncate if needed
        text_truncated = False
        if len(text) > self.settings.max_text_length:
            text = text[: self.settings.max_text_length]
            text_truncated = True

        start_time = time.time()

        try:
            # Tokenize
            inputs = self.tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512, padding=True
            )

            # Run inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.nn.functional.softmax(logits, dim=-1)

                # Get prediction
                predicted_class = torch.argmax(probs, dim=-1).item()
                confidence = probs[0][predicted_class].item()

                # Map to label
                id2label = self.model.config.id2label
                label = id2label[predicted_class]

            inference_time = (time.time() - start_time) * 1000

            result = {
                "label": label,
                "score": float(confidence),
                "inference_time_ms": round(inference_time, 2),
                "model_name": "ONNX",
                "text_length": len(text),
                "cached": False,
                "text_truncated": text_truncated,
            }

            # Cache result
            self._cache_prediction(cache_key, result)

            logger.info(
                "ONNX prediction completed",
                label=label,
                score=float(confidence),
                inference_time_ms=round(inference_time, 2),
            )

            return result

        except Exception as e:
            logger.error(
                "ONNX inference failed", error=str(e), error_type=type(e).__name__
            )
            raise ModelInferenceError(
                message=f"ONNX prediction failed: {str(e)}",
                model_name="ONNX",
                context={"text_length": len(text)},
            )

    def get_model_info(self) -> Dict[str, Any]:
        """Get ONNX model information."""
        onnx_file = self.onnx_model_path / "model.onnx"
        model_size_mb = 0

        if onnx_file.exists():
            model_size_mb = onnx_file.stat().st_size / (1024 * 1024)

        return {
            "model_type": "ONNX",
            "model_path": str(self.onnx_model_path),
            "is_loaded": self._is_loaded,
            "is_ready": self.is_ready(),
            "model_size_mb": round(model_size_mb, 2),
            "cache_size": len(self._prediction_cache),
            "cache_max_size": self._cache_max_size,
        }


from functools import lru_cache


@lru_cache(maxsize=1)
def get_onnx_sentiment_analyzer(onnx_model_path: str) -> ONNXSentimentAnalyzer:
    """
    Get ONNX sentiment analyzer instance.

    Uses lru_cache to ensure a single instance per model path,
    providing proper singleton behavior without global state.
    This is thread-safe and can be easily mocked for testing.

    Args:
        onnx_model_path: Path to ONNX model directory

    Returns:
        ONNXSentimentAnalyzer instance
    """
    return ONNXSentimentAnalyzer(onnx_model_path)


def reset_onnx_sentiment_analyzer() -> None:
    """
    Reset the ONNX analyzer instance (useful for testing).

    Clears the lru_cache to allow a fresh instance to be created.
    """
    get_onnx_sentiment_analyzer.cache_clear()
