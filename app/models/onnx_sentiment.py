"""
ONNX-based sentiment analysis model implementation.

This module provides an ONNX Runtime implementation of the sentiment analysis
model for optimized inference. It implements the ModelStrategy protocol and
provides similar functionality to the PyTorch implementation but with improved
performance characteristics.
"""

import time
from pathlib import Path
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
        self._loaded_model_file: Path | None = None

        # Initialize the model
        self._load_model()

        # Initialize cache based on settings
        self._init_cache()

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

    def _find_best_model_file(self) -> Path | None:
        """Find the best available ONNX model file.

        Prioritizes quantized models for better CPU performance:
        1. model.quantized.onnx (INT8 quantized - ~4x smaller, 2-3x faster on CPU)
        2. model_quantized.onnx (legacy name; still supported)
        2. model_optimized.onnx (graph optimized)
        3. model.onnx (base model)
        4. Any other .onnx file

        Returns:
            Path to the best available model file, or None if no model found.
        """
        # Priority order for model files
        priority_files = [
            "model.quantized.onnx",
            "model_quantized.onnx",
            "model_optimized.onnx",
            "model.onnx",
        ]

        for filename in priority_files:
            model_file = self.model_path / filename
            if model_file.exists():
                logger.debug(
                    "Found prioritized model file",
                    filename=filename,
                    is_quantized="quantized" in filename,
                )
                return model_file

        # Fallback: find any .onnx file
        onnx_files = list(self.model_path.glob("*.onnx"))
        if onnx_files:
            logger.debug("Using fallback ONNX file", filename=onnx_files[0].name)
            return onnx_files[0]

        return None

    def _load_model(self) -> None:
        """Load the ONNX model and tokenizer.

        Prioritizes quantized models for better performance:
        1. model.quantized.onnx (INT8 quantized - fastest on CPU)
        2. model_quantized.onnx (legacy name; still supported)
        2. model_optimized.onnx (graph optimized)
        3. model.onnx (base model)
        4. Any other .onnx file

        Raises:
            RuntimeError: If model loading fails.
        """
        try:
            logger.info("Loading ONNX model", model_path=str(self.model_path))
            start_time = time.time()

            # Find the ONNX model file - prefer quantized > optimized > base
            model_file = self._find_best_model_file()
            if model_file is None:
                raise FileNotFoundError(f"No ONNX model file found in {self.model_path}")

            self._loaded_model_file = model_file
            logger.info("Using ONNX model file", model_file=str(model_file))

            # Create ONNX Runtime session with tuned thread settings
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            # Apply thread settings from config
            # For microservices, single-threaded (1) lets Uvicorn handle parallelism
            sess_options.intra_op_num_threads = self.settings.model.onnx_intra_op_num_threads
            sess_options.inter_op_num_threads = self.settings.model.onnx_inter_op_num_threads

            # Set execution mode
            if self.settings.model.onnx_execution_mode == "parallel":
                sess_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
            else:
                sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

            logger.info(
                "ONNX session options configured",
                intra_op_threads=self.settings.model.onnx_intra_op_num_threads,
                inter_op_threads=self.settings.model.onnx_inter_op_num_threads,
                execution_mode=self.settings.model.onnx_execution_mode,
            )

            self._session = ort.InferenceSession(
                str(model_file),
                sess_options=sess_options,
                providers=self._providers,
            )

            # Load tokenizer with explicit FastTokenizer (Rust-based) preference
            # FastTokenizer is 3-10x faster than Python-based tokenizers
            if (self.model_path / "tokenizer_config.json").exists():
                self._tokenizer = AutoTokenizer.from_pretrained(
                    str(self.model_path),
                    use_fast=True,
                )
                logger.info("Loaded tokenizer from model directory")
            else:
                # Fall back to downloading tokenizer for the model
                self._tokenizer = AutoTokenizer.from_pretrained(
                    self.settings.model.model_name,
                    cache_dir=self.settings.model.model_cache_dir,
                    use_fast=True,
                )
                logger.info("Loaded tokenizer for model", model_name=self.settings.model.model_name)

            # Log FastTokenizer status
            if self._tokenizer.is_fast:
                logger.info("Using FastTokenizer (Rust-based)")
            else:
                logger.warning(
                    "FastTokenizer not available, using slow Python tokenizer",
                    hint="Ensure tokenizer.json is present in model directory",
                )

            load_time = time.time() - start_time
            self._is_loaded = True

            logger.info(
                "ONNX model loaded successfully",
                load_time_seconds=load_time,
                providers=self._session.get_providers(),
            )

        except Exception as e:
            logger.error("Failed to load ONNX model", model_path=str(self.model_path), error=str(e))
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

    def _init_cache(self) -> None:
        """Initialize the prediction cache based on configuration.

        Uses the base class method to set up caching uniformly.
        """
        super()._init_cache(
            self._predict_internal,
            self.settings.model.prediction_cache_enabled,
            self.settings.model.prediction_cache_max_size,
        )

    def _predict_internal(self, text: str) -> tuple:
        """Internal prediction method (may be cached or not based on config).

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
                text[: self.settings.model.max_text_length],
                padding=True,
                truncation=True,
                max_length=self.settings.model.max_text_length,
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
            logger.error("ONNX inference failed", error=str(e))
            raise ModelInferenceError(f"ONNX model inference failed: {e}") from e

    def _get_cache_info(self) -> Any:
        """Get cache info, returning a mock object if cache is disabled.

        Uses the base class method for uniform cache info handling.

        Returns:
            CacheInfo object (real if cache enabled, mock if disabled).
        """
        return super()._get_cache_info(self.settings.model.prediction_cache_enabled)

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
        original_length = len(text.strip())
        cleaned_text = self._preprocess_text(text, self.settings.model.max_text_length)
        if len(cleaned_text) < original_length:
            ctx_logger.warning(
                "Text truncated",
                extra={
                    "original_length": original_length,
                    "max_length": self.settings.model.max_text_length,
                },
            )

        # Perform prediction with timing
        start_time = time.time()

        # Check if result is cached (only if cache is enabled)
        cache_info_before = self._get_cache_info()

        try:
            label, score = self._cached_predict(cleaned_text)
        except Exception as e:
            ctx_logger.error("Prediction failed", extra={"error": str(e)})
            raise

        inference_time = time.time() - start_time
        inference_time_ms = inference_time * 1000

        # Update cache statistics (only if cache is enabled)
        cache_info_after = self._get_cache_info()
        is_cache_hit = self._track_cache_stats(cache_info_before, cache_info_after)
        if self.settings.model.prediction_cache_enabled:
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

        # Preprocess texts
        valid_texts, valid_indices = self._preprocess_batch_texts(
            texts, self.settings.model.max_text_length
        )

        # Perform batch prediction
        start_time = time.time()

        try:
            if valid_texts:
                # Tokenize all texts
                inputs = self._tokenizer(
                    valid_texts,
                    padding=True,
                    truncation=True,
                    max_length=self.settings.model.max_text_length,
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
        results = self._build_batch_results(
            raw_results, valid_indices, len(texts), inference_time_ms
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
            A dictionary containing model metadata including quantization status.
        """
        cache_info = self._get_cache_info()

        # Determine model optimization level from loaded file
        model_file_name = self._loaded_model_file.name if self._loaded_model_file else None
        is_quantized = model_file_name is not None and "quantized" in model_file_name
        is_optimized = model_file_name is not None and (
            "optimized" in model_file_name or is_quantized
        )

        return {
            "model_name": self.settings.model.model_name,
            "backend": "onnx",
            "model_path": str(self.model_path),
            "model_file": model_file_name,
            "execution_providers": self._session.get_providers() if self._session else [],
            "is_loaded": self._is_loaded,
            "is_quantized": is_quantized,
            "is_optimized": is_optimized,
            "max_text_length": self.settings.model.max_text_length,
            "cache_enabled": self.settings.model.prediction_cache_enabled,
            "cache_size": (
                cache_info.currsize if self.settings.model.prediction_cache_enabled else 0
            ),
            "cache_maxsize": (
                cache_info.maxsize if self.settings.model.prediction_cache_enabled else 0
            ),
            # ONNX Runtime thread settings
            "onnx_intra_op_threads": self.settings.model.onnx_intra_op_num_threads,
            "onnx_inter_op_threads": self.settings.model.onnx_inter_op_num_threads,
            "onnx_execution_mode": self.settings.model.onnx_execution_mode,
            # Tokenizer info
            "tokenizer_is_fast": self._tokenizer.is_fast if self._tokenizer else None,
        }

    def clear_cache(self) -> None:
        """Clear the prediction cache.

        This method clears the LRU cache, forcing all subsequent predictions
        to be recomputed. Extends the base class method to add logging.
        If cache is disabled, this is a no-op.
        """
        if self.settings.model.prediction_cache_enabled:
            super().clear_cache()
            logger.info("ONNX prediction cache cleared")
        else:
            logger.debug("Cache clear called but cache is disabled")


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
        logger.info("Creating new ONNXSentimentAnalyzer instance", model_path=model_path)
        _onnx_analyzer_instances[model_path] = ONNXSentimentAnalyzer(model_path)
    else:
        logger.debug("Returning existing ONNXSentimentAnalyzer instance", model_path=model_path)

    return _onnx_analyzer_instances[model_path]

