"""
Google Cloud Run handler for ONNX sentiment analysis.

This module provides a serverless deployment option for the sentiment
analysis model using Google Cloud Run with ONNX Runtime.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import onnxruntime as ort
from transformers import AutoTokenizer
import torch
import numpy as np
import structlog

# Setup logging
logger = structlog.get_logger()

app = FastAPI(
    title="Sentiment Analysis Cloud Run",
    description="Serverless sentiment analysis using ONNX Runtime on Cloud Run",
    version="1.0.0",
)


class SentimentRequest(BaseModel):
    """Request model for sentiment analysis."""

    text: str = Field(..., min_length=1, max_length=5000)


class SentimentResponse(BaseModel):
    """Response model for sentiment analysis."""

    label: str
    score: float
    inference_time_ms: float
    model_type: str = "ONNX-CloudRun"
    cached: bool = False


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model_loaded: bool


class ONNXCloudRunPredictor:
    """ONNX predictor optimized for Cloud Run."""

    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.tokenizer: Optional[AutoTokenizer] = None
        self.session: Optional[ort.InferenceSession] = None
        self.id2label: Dict[int, str] = {}
        self._prediction_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_max_size = 1000
        self._load_model()

    def _load_model(self):
        """Load ONNX model and tokenizer."""
        try:
            start_time = time.time()

            logger.info("Loading ONNX model", model_path=str(self.model_path))

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)

            # Load ONNX model with optimizations
            onnx_model_file = self.model_path / "model.onnx"

            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )

            # Cloud Run provides multiple CPUs
            sess_options.intra_op_num_threads = int(
                os.environ.get("OMP_NUM_THREADS", "4")
            )
            sess_options.inter_op_num_threads = int(
                os.environ.get("OMP_NUM_THREADS", "4")
            )

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
        """Generate cache key."""
        import hashlib

        return hashlib.sha256(text.encode()).hexdigest()

    def _cache_prediction(self, cache_key: str, result: Dict[str, Any]):
        """Cache prediction result."""
        if len(self._prediction_cache) >= self._cache_max_size:
            # FIFO eviction
            oldest = next(iter(self._prediction_cache))
            del self._prediction_cache[oldest]

        self._prediction_cache[cache_key] = result

    def is_ready(self) -> bool:
        """Check if model is ready."""
        return self.session is not None and self.tokenizer is not None

    def predict(self, text: str) -> Dict[str, Any]:
        """Run inference."""
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
        """Compute softmax."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()


# Global predictor instance
predictor: Optional[ONNXCloudRunPredictor] = None


def get_predictor() -> ONNXCloudRunPredictor:
    """Get or create predictor."""
    global predictor
    if predictor is None:
        model_path = os.environ.get("MODEL_PATH", "/app/model")
        predictor = ONNXCloudRunPredictor(model_path)
    return predictor


@app.on_event("startup")
async def startup_event():
    """Initialize predictor on startup."""
    logger.info("Starting application")
    get_predictor()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Sentiment Analysis Cloud Run",
        "version": "1.0.0",
        "model_type": "ONNX",
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
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
    """Predict sentiment endpoint."""
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
