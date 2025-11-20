"""
ONNX-based sentiment analysis model implementation.

This module provides an ONNX Runtime implementation of the sentiment analysis
model for optimized inference. It implements the ModelStrategy protocol and
provides similar functionality to the PyTorch implementation but with improved
performance characteristics.
"""

from functools import lru_cache
from pathlib import Path
import time
from typing import Any

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

from app.core.config import Settings, get_settings
from app.core.logging import get_contextual_logger, get_logger
from app.models.base import BaseModelMetrics
from app.utils.exceptions import ModelInferenceError, ModelNotLoadedError, TextEmptyError

logger = get_logger(__name__)

# Singleton instance cache
_onnx_analyzer_instances: dict[str, "ONNXSentimentAnalyzer"] = {}


class ONNXSentimentAnalyzer(BaseModelMetrics):
    """ONNX Runtime-based sentiment analysis model.

    This class provides sentiment analysis using ONNX Runtime for optimized
    inference. It implements the ModelStrategy protocol and includes features
    like prediction caching, performance metrics tracking, and batch prediction.

    Inherits from BaseModelMetrics for shared metrics tracking functionality.

    Attributes:
        settings: Application configuration settings.
        model_path: Path to the ONNX model directory.
        _session: ONNX Runtime inference session.
        _tokenizer: Hugging Face tokenizer for text preprocessing.
        _is_loaded: Flag indicating whether the model is loaded.
        _providers: List of execution providers for ONNX Runtime.
    """

    def __init__(self, model_path: str, settings: Settings | None = None):
        """Initialize the ONNX sentiment analyzer.

        Args:
            model_path: Path to the directory containing the ONNX model files.
            settings: Optional settings instance. If not provided, will use
                the default settings from get_settings().

        Raises:
            ValueError: If the model path does not exist.
        """
        super().__init__()  # Initialize BaseModelMetrics
        self.settings = settings or get_settings()
        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise ValueError(f"Model path does not exist: {model_path}")

        self._session: ort.InferenceSession | None = None
        self._tokenizer = None
        self._is_loaded = False
        self._providers = self._determine_providers()

        # Initialize the model
        self._load_model()

    def _determine_providers(self) -> list[str]:
        """Determine the best available execution providers for ONNX Runtime.

        Returns:
            List of execution provider names in priority order.
        """
        available_providers = ort.get_available_providers()
        providers = []

        # Prioritize GPU providers
        if "CUDAExecutionProvider" in available_providers:
            providers.append("CUDAExecutionProvider")
            logger.info("Using CUDA execution provider")

        if "TensorrtExecutionProvider" in available_providers:
            providers.append("TensorrtExecutionProvider")
            logger.info("Using TensorRT execution provider")

        # Always include CPU as fallback
        providers.append("CPUExecutionProvider")

        if len(providers) == 1:
            logger.info("Using CPU execution provider")

        return providers

    def _load_model(self) -> None:
        """Load the ONNX model and tokenizer.

        Raises:
            RuntimeError: If model loading fails.
        """
        try:
            logger.info(f"Loading ONNX model from: {self.model_path}")
            start_time = time.time()

            # Find the ONNX model file
            onnx_files = list(self.model_path.glob("*.onnx"))
            if not onnx_files:
                raise FileNotFoundError(f"No ONNX model file found in {self.model_path}")

            model_file = onnx_files[0]
            logger.info(f"Using ONNX model file: {model_file}")

            # Create ONNX Runtime session
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self._session = ort.InferenceSession(
                str(model_file),
                sess_options=sess_options,
                providers=self._providers,
            )

            # Load tokenizer
            # Try to load from model directory first, fall back to model name
            if (self.model_path / "tokenizer_config.json").exists():
                self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
                logger.info("Loaded tokenizer from model directory")
            else:
                # Fall back to downloading tokenizer for the model
                self._tokenizer = AutoTokenizer.from_pretrained(
                    self.settings.model_name,
                    cache_dir=self.settings.model_cache_dir,
                )
                logger.info(f"Loaded tokenizer for {self.settings.model_name}")

            load_time = time.time() - start_time
            self._is_loaded = True

            logger.info(
                f"ONNX model loaded successfully in {load_time:.2f} seconds",
                extra={"providers": self._session.get_providers()},
            )

        except Exception as e:
            logger.error(f"Failed to load ONNX model from {self.model_path}: {e}")
            self._is_loaded = False
            raise RuntimeError(f"Failed to load ONNX model: {e}") from e

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready for inference.

        Returns:
            True if the model is loaded, False otherwise.
        """
        return self._is_loaded and self._session is not None and self._tokenizer is not None

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
            raise ModelNotLoadedError(f"ONNX model at {self.model_path}")

        if not text or not text.strip():
            ctx_logger.error("Empty text provided")
            raise TextEmptyError()

    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        """Apply softmax to convert logits to probabilities.

        Args:
            logits: Raw model outputs (logits).

        Returns:
            Probabilities after applying softmax.
        """
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        return exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

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
            # Tokenize input
            inputs = self._tokenizer(
                text[: self.settings.max_text_length],
                padding=True,
                truncation=True,
                max_length=self.settings.max_text_length,
                return_tensors="np",
            )

            # Run inference
            ort_inputs = {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64),
            }

            ort_outputs = self._session.run(None, ort_inputs)
            logits = ort_outputs[0]

            # Apply softmax to get probabilities
            probabilities = self._softmax(logits)

            # Get prediction
            predicted_class = int(np.argmax(probabilities, axis=1)[0])
            confidence = float(probabilities[0][predicted_class])

            # Map to sentiment labels (assuming binary classification)
            # 0 = NEGATIVE, 1 = POSITIVE
            label = "POSITIVE" if predicted_class == 1 else "NEGATIVE"

            return (label, confidence)

        except Exception as e:
            logger.error(f"ONNX inference failed: {e}")
            raise ModelInferenceError(f"ONNX model inference failed: {e}") from e

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
        ctx_logger.info("Starting ONNX prediction", extra={"text_length": len(text)})

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
            "ONNX prediction completed",
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

        Args:
            texts: A list of input texts to analyze.

        Returns:
            A list of dictionaries containing prediction results for each text.

        Raises:
            ModelNotLoadedError: If the model is not loaded.
            ModelInferenceError: If batch inference fails.
        """
        ctx_logger = get_contextual_logger(logger)
        ctx_logger.info("Starting ONNX batch prediction", extra={"batch_size": len(texts)})

        if not self.is_ready():
            raise ModelNotLoadedError(f"ONNX model at {self.model_path}")

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
                # Tokenize all texts
                inputs = self._tokenizer(
                    valid_texts,
                    padding=True,
                    truncation=True,
                    max_length=self.settings.max_text_length,
                    return_tensors="np",
                )

                # Run batch inference
                ort_inputs = {
                    "input_ids": inputs["input_ids"].astype(np.int64),
                    "attention_mask": inputs["attention_mask"].astype(np.int64),
                }

                ort_outputs = self._session.run(None, ort_inputs)
                logits = ort_outputs[0]

                # Apply softmax to get probabilities
                probabilities = self._softmax(logits)

                # Get predictions
                predicted_classes = np.argmax(probabilities, axis=1)
                confidences = probabilities[np.arange(len(predicted_classes)), predicted_classes]

                raw_results = []
                for pred_class, conf in zip(predicted_classes, confidences):
                    label = "POSITIVE" if pred_class == 1 else "NEGATIVE"
                    raw_results.append({"label": label, "score": float(conf)})
            else:
                raw_results = []

        except Exception as e:
            ctx_logger.error("ONNX batch prediction failed", extra={"error": str(e)})
            raise ModelInferenceError(f"ONNX batch inference failed: {e}") from e

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
            "ONNX batch prediction completed",
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
            "backend": "onnx",
            "model_path": str(self.model_path),
            "execution_providers": self._session.get_providers() if self._session else [],
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
        logger.info("ONNX prediction cache cleared")


def get_onnx_sentiment_analyzer(model_path: str) -> ONNXSentimentAnalyzer:
    """Get an instance of the ONNX sentiment analyzer.

    This function implements a singleton pattern per model path, ensuring that
    only one instance per model path is created and reused.

    Args:
        model_path: Path to the ONNX model directory.

    Returns:
        An ONNXSentimentAnalyzer instance for the specified model path.

    Example:
        >>> analyzer = get_onnx_sentiment_analyzer("./onnx_models/my-model")
        >>> result = analyzer.predict("This is amazing!")
        >>> print(result['label'])
        'POSITIVE'
    """
    global _onnx_analyzer_instances

    if model_path not in _onnx_analyzer_instances:
        logger.info(f"Creating new ONNXSentimentAnalyzer instance for: {model_path}")
        _onnx_analyzer_instances[model_path] = ONNXSentimentAnalyzer(model_path)
    else:
        logger.debug(f"Returning existing ONNXSentimentAnalyzer instance for: {model_path}")

    return _onnx_analyzer_instances[model_path]


class ONNXModelOptimizer:
    """Utility class for converting PyTorch models to ONNX format.

    This class provides methods to export trained PyTorch models to ONNX
    format for optimized inference.
    """

    @staticmethod
    def export_model(
        model_name: str,
        output_path: str,
        opset_version: int = 14,
    ) -> None:
        """Export a Hugging Face model to ONNX format.

        Args:
            model_name: The Hugging Face model identifier.
            output_path: Directory path where the ONNX model will be saved.
            opset_version: ONNX opset version to use (default: 14).

        Raises:
            RuntimeError: If export fails.
        """
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            logger.info(f"Exporting model {model_name} to ONNX format")

            # Load model and tokenizer
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            tokenizer = AutoTokenizer.from_pretrained(model_name)

            # Create output directory
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save tokenizer
            tokenizer.save_pretrained(str(output_dir))

            # Create dummy input
            dummy_text = "This is a sample text for export."
            inputs = tokenizer(
                dummy_text,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )

            # Export to ONNX
            onnx_path = output_dir / "model.onnx"
            torch.onnx.export(
                model,
                (inputs["input_ids"], inputs["attention_mask"]),
                str(onnx_path),
                input_names=["input_ids", "attention_mask"],
                output_names=["logits"],
                dynamic_axes={
                    "input_ids": {0: "batch_size", 1: "sequence_length"},
                    "attention_mask": {0: "batch_size", 1: "sequence_length"},
                    "logits": {0: "batch_size"},
                },
                opset_version=opset_version,
            )

            logger.info(f"Model exported successfully to {onnx_path}")

        except Exception as e:
            logger.error(f"Failed to export model to ONNX: {e}")
            raise RuntimeError(f"ONNX export failed: {e}") from e
