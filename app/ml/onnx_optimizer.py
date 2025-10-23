"""
ONNX Model Optimization Module.

This module handles conversion of Hugging Face transformers models to ONNX format
and provides optimized inference using ONNX Runtime.
"""

import hashlib
import time
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import torch
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer

from ..core.config import get_settings
from ..core.logging import get_logger
from ..utils.exceptions import ModelInferenceError, ModelNotLoadedError

logger = get_logger(__name__)


class ONNXModelOptimizer:
    """Handles the conversion and optimization of Hugging Face models to ONNX.

    This class provides a straightforward way to convert transformer models from
    the Hugging Face Hub into the ONNX format. The conversion can include
    optimizations that may improve inference performance.

    Attributes:
        model_name: The name of the Hugging Face model to be converted.
        cache_dir: The directory where the converted ONNX models will be stored.
    """

    def __init__(self, model_name: str, cache_dir: Optional[str] = None):
        """Initializes the ONNX model optimizer.

        Args:
            model_name: The name of the Hugging Face model to convert.
            cache_dir: The directory to cache the converted models. If not
                provided, a default directory will be used.
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
        """Converts a Hugging Face transformer model to the ONNX format.

        This method uses the `optimum` library to handle the conversion. The
        resulting ONNX model and its associated tokenizer configuration are
        saved to a specified directory.

        Args:
            export_path: The path where the ONNX model will be saved. If not
                provided, a default path is constructed in the cache directory.
            optimize: A flag to enable ONNX graph optimizations.
            quantize: A flag to enable model quantization, which can reduce
                model size and speed up inference at the cost of some precision.

        Returns:
            The path to the directory containing the exported ONNX model.

        Raises:
            ModelInferenceError: If the conversion process fails.
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
            logger.error("ONNX conversion failed", error=str(e), error_type=type(e).__name__)
            raise ModelInferenceError(
                message=f"ONNX conversion failed: {str(e)}",
                model_name=self.model_name,
                context={"operation": "onnx_conversion"},
            )


class ONNXSentimentAnalyzer:
    """Performs sentiment analysis using an optimized ONNX model.

    This class leverages ONNX Runtime for high-performance inference. It is
    designed to be a faster alternative to PyTorch-based inference for
    production environments. It also includes an in-memory LRU cache to
    speed up predictions for repeated inputs.

    Attributes:
        settings: The application's configuration settings.
        onnx_model_path: The path to the directory containing the ONNX model.
        tokenizer: The tokenizer for the model.
        model: The loaded ONNX model.
    """

    def __init__(self, onnx_model_path: str):
        """Initializes the ONNX-based sentiment analyzer.

        Args:
            onnx_model_path: The path to the directory containing the ONNX
                model and tokenizer configuration.
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
        """Loads the ONNX model and tokenizer from the specified path.

        This method initializes the ONNX Runtime session and loads the
        tokenizer. It is called during the class's initialization.

        Raises:
            Exception: If the model or tokenizer fails to load.
        """
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
            logger.error("ONNX model loading failed", error=str(e), error_type=type(e).__name__)
            self._is_loaded = False
            raise

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
            return self._prediction_cache[cache_key]
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

        # Add new entry (will be at the end as most recently used)
        self._prediction_cache[cache_key] = result

    def is_ready(self) -> bool:
        """Checks if the model is loaded and ready for inference.

        Returns:
            `True` if the model is loaded, `False` otherwise.
        """
        return self._is_loaded and self.model is not None

    def predict(self, text: str) -> Dict[str, Any]:
        """Performs sentiment analysis on a text using the ONNX model.

        This method first checks the prediction cache for the given text. If
        a cached result is not found, it tokenizes the text, runs inference
        with the ONNX model, and caches the result before returning it.

        Args:
            text: The input text to be analyzed.

        Returns:
            A dictionary containing the prediction results.

        Raises:
            ModelNotLoadedError: If the model is not loaded when this method
                is called.
            ModelInferenceError: If an error occurs during the inference
                process.
            ValueError: If the input text is empty.
        """
        if not self.is_ready():
            raise ModelNotLoadedError(model_name="ONNX Model", context={"operation": "prediction"})

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
            logger.error("ONNX inference failed", error=str(e), error_type=type(e).__name__)
            raise ModelInferenceError(
                message=f"ONNX prediction failed: {str(e)}",
                model_name="ONNX",
                context={"text_length": len(text)},
            )

    def get_model_info(self) -> Dict[str, Any]:
        """Retrieves metadata about the ONNX model.

        Returns:
            A dictionary containing information such as the model's type, path,
            size, and the status of the prediction cache.
        """
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


@lru_cache(maxsize=1)
def get_onnx_sentiment_analyzer(onnx_model_path: str) -> ONNXSentimentAnalyzer:
    """Creates and retrieves a singleton instance of the ONNX sentiment analyzer.

    This factory function uses `@lru_cache(maxsize=1)` to ensure that only one
    instance of the `ONNXSentimentAnalyzer` is created for a given model path.
    This approach provides thread-safe, singleton-like behavior, which is
    efficient for managing a resource-intensive object like a model.

    Args:
        onnx_model_path: The path to the directory containing the ONNX model.

    Returns:
        A singleton instance of `ONNXSentimentAnalyzer`.
    """
    return ONNXSentimentAnalyzer(onnx_model_path)


def reset_onnx_sentiment_analyzer() -> None:
    """Resets the singleton instance of the ONNX sentiment analyzer.

    This function is primarily intended for use in testing scenarios where a
    fresh instance of the analyzer is needed for different test cases. It
    works by clearing the cache of the `get_onnx_sentiment_analyzer` function.
    """
    get_onnx_sentiment_analyzer.cache_clear()
