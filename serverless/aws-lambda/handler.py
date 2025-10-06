"""
AWS Lambda handler for ONNX sentiment analysis.

This module provides a serverless deployment option for the sentiment
analysis model using AWS Lambda with ONNX Runtime for fast cold starts.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from mangum import Mangum
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ONNX Runtime imports
import onnxruntime as ort
from transformers import AutoTokenizer
import torch
import numpy as np

app = FastAPI(
    title="Sentiment Analysis Lambda",
    description="Serverless sentiment analysis using ONNX Runtime",
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
    model_type: str = "ONNX-Lambda"


class ONNXLambdaPredictor:
    """Lightweight ONNX predictor for Lambda."""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.session = None
        self._load_model()

    def _load_model(self):
        """Load ONNX model and tokenizer from Lambda storage."""
        model_path = os.environ.get("MODEL_PATH", "/opt/ml/model")

        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)

            # Load ONNX model
            onnx_model_path = os.path.join(model_path, "model.onnx")

            # Create ONNX Runtime session with optimizations
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )
            sess_options.intra_op_num_threads = 1  # Lambda has limited CPU

            self.session = ort.InferenceSession(
                onnx_model_path, sess_options, providers=["CPUExecutionProvider"]
            )

            print(f"Model loaded successfully from {model_path}")

        except Exception as e:
            print(f"Error loading model: {e}")
            raise

    def predict(self, text: str) -> Dict[str, Any]:
        """Run inference on input text."""
        import time

        start_time = time.time()

        try:
            # Tokenize
            inputs = self.tokenizer(
                text, return_tensors="np", truncation=True, max_length=512, padding=True
            )

            # Prepare inputs for ONNX Runtime
            ort_inputs = {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64),
            }

            # Run inference
            outputs = self.session.run(None, ort_inputs)
            logits = outputs[0]

            # Get prediction
            probs = self._softmax(logits[0])
            predicted_class = np.argmax(probs)
            confidence = float(probs[predicted_class])

            # Map to label (assuming binary classification)
            label = "POSITIVE" if predicted_class == 1 else "NEGATIVE"

            inference_time = (time.time() - start_time) * 1000

            return {
                "label": label,
                "score": confidence,
                "inference_time_ms": round(inference_time, 2),
                "model_type": "ONNX-Lambda",
            }

        except Exception as e:
            print(f"Prediction error: {e}")
            raise

    @staticmethod
    def _softmax(x):
        """Compute softmax values."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()


# Global predictor instance (reused across invocations)
predictor = None


def get_predictor() -> ONNXLambdaPredictor:
    """Get or create predictor instance."""
    global predictor
    if predictor is None:
        predictor = ONNXLambdaPredictor()
    return predictor


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Sentiment Analysis Lambda",
        "version": "1.0.0",
        "model_type": "ONNX",
    }


@app.get("/health")
async def health():
    """Health check."""
    try:
        pred = get_predictor()
        return {"status": "healthy", "model_loaded": pred.session is not None}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/predict", response_model=SentimentResponse)
async def predict(request: SentimentRequest):
    """Predict sentiment."""
    try:
        pred = get_predictor()
        result = pred.predict(request.text)
        return SentimentResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mangum handler for AWS Lambda
handler = Mangum(app, lifespan="off")


# Direct Lambda handler (alternative to Mangum)
def lambda_handler(event, context):
    """AWS Lambda entry point."""
    try:
        # Parse request
        body = json.loads(event.get("body", "{}"))
        text = body.get("text", "")

        if not text:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Text is required"}),
            }

        # Get prediction
        pred = get_predictor()
        result = pred.predict(text)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
