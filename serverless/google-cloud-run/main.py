"""Google Cloud Run handler for ONNX sentiment analysis.

This module provides a serverless deployment option for the sentiment
analysis model using Google Cloud Run with ONNX Runtime. It includes a
FastAPI application, a lightweight ONNX predictor, and an in-memory cache.
"""

import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import onnxruntime as ort
import structlog
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoTokenizer

# Setup logging
logger = structlog.get_logger()

app = FastAPI(
    title="Sentiment Analysis Cloud Run",
    description="Serverless sentiment analysis using ONNX Runtime on Cloud Run",
    version="1.0.0",
)


class SentimentRequest(BaseModel):
    """Request model for sentiment analysis.

    Attributes:
        text: The input text to be analyzed.
    """

    text: str = Field(..., min_length=1, max_length=5000)


class SentimentResponse(BaseModel):
    """Response model for sentiment analysis.

    Attributes:
        label: The predicted sentiment label (e.g., "POSITIVE").
        score: The confidence score of the prediction.
        inference_time_ms: The time taken for model inference.
        model_type: The type of the model used.
        cached: A flag indicating if the response was served from cache.
    """

    label: str
    score: float
    inference_time_ms: float
    model_type: str = "ONNX-CloudRun"
    cached: bool = False


class HealthResponse(BaseModel):
    """Health check response model.

    Attributes:
        status: The health status of the service ("healthy" or "unhealthy").
        model_loaded: A flag indicating if the model is loaded and ready.
    """

    status: str
    model_loaded: bool


class ONNXCloudRunPredictor:
    """An ONNX predictor optimized for Google Cloud Run.

    This class handles loading the ONNX model and tokenizer, runs inference,
    and includes a simple in-memory LRU cache to speed up responses for
    frequently seen inputs.

    Attributes:
        model_path: The path to the directory containing the model.
        tokenizer: The loaded Hugging Face tokenizer.
        session: The ONNX Runtime inference session.
        id2label: A dictionary mapping class IDs to their string labels.
    """

    def __init__(self, model_path: str):
        """Initializes the `ONNXCloudRunPredictor`.

        Args:
            model_path: The path to the directory containing the model files.
        """
        self.model_path = Path(model_path)
        self.tokenizer: Optional[AutoTokenizer] = None
        self.session: Optional[ort.InferenceSession] = None
        self.id2label: Dict[int, str] = {}
        self._prediction_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_max_size = 1000
        self._load_model()

    def _load_model(self):
        """Loads the ONNX model, tokenizer, and configuration.

        Raises:
            Exception: If the model or tokenizer fails to load.
        """
        try:
            start_time = time.time()

            logger.info("Loading ONNX model", model_path=str(self.model_path))

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)

            # Load ONNX model with optimizations
            onnx_model_file = self.model_path / "model.onnx"

            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            # Cloud Run provides multiple CPUs
            sess_options.intra_op_num_threads = int(os.environ.get("OMP_NUM_THREADS", "4"))
            sess_options.inter_op_num_threads = int(os.environ.get("OMP_NUM_THREADS", "4"))

            self.session = ort.InferenceSession(
                str(onnx_model_file), sess_options, providers=["CPUExecutionProvider"]
            )

            # Load label mapping from config
            from transformers import AutoConfig

            config = AutoConfig.from_pretrained(self.model_path)
            self.id2label = config.id2label

            duration = (time.time() - start_time) * 1000

            logger.info(
                "Model loaded successfully",
                duration_ms=duration,
                model_path=str(self.model_path),
            )

        except Exception as e:
            logger.error("Failed to load model", error=str(e))
            raise

    def _get_cache_key(self, text: str) -> str:
        """Generates a SHA256 hash for the input text to use as a cache key.

        Args:
            text: The input text.

        Returns:
            The SHA256 hash of the text.
        """
        import hashlib

        return hashlib.sha256(text.encode()).hexdigest()

    def _cache_prediction(self, cache_key: str, result: Dict[str, Any]):
        """Caches a prediction result.

        Implements a simple FIFO (First-In, First-Out) eviction strategy
        when the cache reaches its maximum size.

        Args:
            cache_key: The key for the cached item.
            result: The prediction result dictionary to cache.
        """
        if len(self._prediction_cache) >= self._cache_max_size:
            # FIFO eviction
            oldest = next(iter(self._prediction_cache))
            del self._prediction_cache[oldest]

        self._prediction_cache[cache_key] = result

    def is_ready(self) -> bool:
        """Checks if the model and tokenizer are loaded and ready for inference.

        Returns:
            `True` if the model is ready, `False` otherwise.
        """
        return self.session is not None and self.tokenizer is not None

    def predict(self, text: str) -> Dict[str, Any]:
        """Runs sentiment analysis inference on the given text.

        This method first checks the in-memory cache for a result. If not
        found, it preprocesses the text, runs it through the ONNX model,
        post-processes the output, and caches the result before returning it.

        Args:
            text: The input string to be analyzed.

        Returns:
            A dictionary containing the prediction details, including the
            label, score, and whether the result was from the cache.

        Raises:
            Exception: If an error occurs during inference.
        """
        # Check cache
        cache_key = self._get_cache_key(text)
        if cache_key in self._prediction_cache:
            cached = self._prediction_cache[cache_key].copy()
            cached["cached"] = True
            logger.info("Cache hit", cache_key_prefix=cache_key[:8])
            return cached

        start_time = time.time()

        try:
            # Tokenize
            inputs = self.tokenizer(
                text, return_tensors="np", truncation=True, max_length=512, padding=True
            )

            # Prepare ONNX inputs
            ort_inputs = {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64),
            }

            # Run inference
            outputs = self.session.run(None, ort_inputs)
            logits = outputs[0]

            # Get prediction
            probs = self._softmax(logits[0])
            predicted_class = int(np.argmax(probs))
            confidence = float(probs[predicted_class])

            # Map to label
            label = self.id2label.get(predicted_class, f"LABEL_{predicted_class}")

            inference_time = (time.time() - start_time) * 1000

            result = {
                "label": label,
                "score": confidence,
                "inference_time_ms": round(inference_time, 2),
                "model_type": "ONNX-CloudRun",
                "cached": False,
            }

            # Cache result
            self._cache_prediction(cache_key, result)

            logger.info(
                "Prediction completed",
                label=label,
                score=confidence,
                inference_time_ms=round(inference_time, 2),
            )

            return result

        except Exception as e:
            logger.error("Prediction failed", error=str(e))
            raise

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        """Computes softmax values for a given array of scores.

        Args:
            x: A numpy array of scores.

        Returns:
            A numpy array with the computed softmax values.
        """
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()


# Global predictor instance
predictor: Optional[ONNXCloudRunPredictor] = None


def get_predictor() -> ONNXCloudRunPredictor:
    """Returns a singleton instance of the ONNX predictor.

    This function ensures that the `ONNXCloudRunPredictor` is initialized
    only once per container instance, allowing for model and cache reuse
    across multiple requests.

    Returns:
        An instance of `ONNXCloudRunPredictor`.
    """
    global predictor
    if predictor is None:
        model_path = os.environ.get("MODEL_PATH", "/app/model")
        predictor = ONNXCloudRunPredictor(model_path)
    return predictor


@app.on_event("startup")
async def startup_event():
    """Initializes the predictor singleton when the application starts.

    This leverages FastAPI's startup event to preload the model, ensuring it
    is ready before the first request arrives.
    """
    logger.info("Starting application")
    get_predictor()


@app.get("/")
async def root():
    """Provides a simple root endpoint to confirm the service is running.

    Returns:
        A dictionary with a welcome message and service version.
    """
    return {
        "service": "Sentiment Analysis Cloud Run",
        "version": "1.0.0",
        "model_type": "ONNX",
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Performs a health check of the Cloud Run service.

    This endpoint verifies that the model has been loaded successfully and
    the service is ready to accept prediction requests.

    Returns:
        A `HealthResponse` object indicating the health status.
    """
    try:
        pred = get_predictor()
        return HealthResponse(
            status="healthy" if pred.is_ready() else "unhealthy",
            model_loaded=pred.is_ready(),
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(status="unhealthy", model_loaded=False)


@app.post("/predict", response_model=SentimentResponse)
async def predict(request: SentimentRequest):
    """Handles sentiment prediction requests.

    This endpoint takes a `SentimentRequest` with text and returns a
    `SentimentResponse` with the prediction. It will return a 503 error if
    the model is not yet ready.

    Args:
        request: The request body containing the text to be analyzed.

    Returns:
        A `SentimentResponse` with the prediction result.

    Raises:
        HTTPException: If the model is not ready or an error occurs.
    """
    try:
        pred = get_predictor()

        if not pred.is_ready():
            raise HTTPException(status_code=503, detail="Model not ready")

        result = pred.predict(request.text)
        return SentimentResponse(**result)

    except Exception as e:
        logger.error("Prediction endpoint failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
