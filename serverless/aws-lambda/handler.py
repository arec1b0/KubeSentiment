"""AWS Lambda handler for ONNX sentiment analysis.

This module provides a serverless deployment option for the sentiment
analysis model using AWS Lambda with ONNX Runtime for fast cold starts. It can
be deployed using either Mangum for full FastAPI compatibility or as a direct
Lambda handler for a lightweight alternative.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np

# ONNX Runtime imports
import onnxruntime as ort
import torch
from fastapi import FastAPI, HTTPException
from mangum import Mangum
from pydantic import BaseModel, Field
from transformers import AutoTokenizer

app = FastAPI(
    title="Sentiment Analysis Lambda",
    description="Serverless sentiment analysis using ONNX Runtime",
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
        inference_time_ms: The time taken for the model inference.
        model_type: The type of the model used.
    """

    label: str
    score: float
    inference_time_ms: float
    model_type: str = "ONNX-Lambda"


class ONNXLambdaPredictor:
    """A lightweight ONNX predictor optimized for AWS Lambda.

    This class handles loading the ONNX model and tokenizer, and provides a
    `predict` method to run inference. It's designed to be initialized once
    and reused across multiple Lambda invocations to leverage execution
    context reuse.

    Attributes:
        model: The loaded ONNX model.
        tokenizer: The tokenizer for preprocessing text.
        session: The ONNX Runtime inference session.
    """

    def __init__(self):
        """Initializes the `ONNXLambdaPredictor`."""
        self.model = None
        self.tokenizer = None
        self.session = None
        self._load_model()

    def _load_model(self):
        """Loads the ONNX model and tokenizer from the Lambda environment.

        The model is expected to be located at the path specified by the
        `MODEL_PATH` environment variable. This is typically `/opt/ml/model`
        when using Lambda layers or a mounted EFS.

        Raises:
            Exception: If the model or tokenizer cannot be loaded.
        """
        model_path = os.environ.get("MODEL_PATH", "/opt/ml/model")

        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)

            # Load ONNX model
            onnx_model_path = os.path.join(model_path, "model.onnx")

            # Create ONNX Runtime session with optimizations
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = 1  # Lambda has limited CPU

            self.session = ort.InferenceSession(
                onnx_model_path, sess_options, providers=["CPUExecutionProvider"]
            )

            print(f"Model loaded successfully from {model_path}")

        except Exception as e:
            print(f"Error loading model: {e}")
            raise

    def predict(self, text: str) -> Dict[str, Any]:
        """Runs sentiment analysis inference on the given text.

        Args:
            text: The input string to be analyzed.

        Returns:
            A dictionary containing the prediction label, score, and
            inference time.

        Raises:
            Exception: If an error occurs during inference.
        """
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
    def _softmax(x: np.ndarray) -> np.ndarray:
        """Computes softmax values for a given array of scores.

        Args:
            x: A numpy array of scores.

        Returns:
            A numpy array with the computed softmax values.
        """
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()


# Global predictor instance (reused across invocations)
predictor = None


def get_predictor() -> ONNXLambdaPredictor:
    """Returns a singleton instance of the ONNX predictor.

    This function ensures that the `ONNXLambdaPredictor` is initialized only
    once per Lambda container, allowing for model reuse across invocations.

    Returns:
        An instance of `ONNXLambdaPredictor`.
    """
    global predictor
    if predictor is None:
        predictor = ONNXLambdaPredictor()
    return predictor


@app.get("/")
async def root():
    """Provides a simple root endpoint to confirm the service is running.

    Returns:
        A dictionary with a welcome message and service version.
    """
    return {
        "message": "Sentiment Analysis Lambda",
        "version": "1.0.0",
        "model_type": "ONNX",
    }


@app.get("/health")
async def health():
    """Performs a health check of the Lambda function.

    This endpoint verifies that the model has been loaded successfully.

    Returns:
        A dictionary indicating the health status.
    """
    try:
        pred = get_predictor()
        return {"status": "healthy", "model_loaded": pred.session is not None}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/predict", response_model=SentimentResponse)
async def predict(request: SentimentRequest):
    """Handles sentiment prediction requests.

    This endpoint takes a `SentimentRequest` with text and returns a
    `SentimentResponse` with the prediction.

    Args:
        request: The request body containing the text to be analyzed.

    Returns:
        A `SentimentResponse` with the prediction result.

    Raises:
        HTTPException: If an error occurs during prediction.
    """
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
    """Provides a direct AWS Lambda entry point.

    This handler can be used as an alternative to `Mangum` for a more
    lightweight setup. It manually parses the request from the Lambda
    event and returns a standard Lambda proxy response.

    Args:
        event: The AWS Lambda event dictionary.
        context: The AWS Lambda context object.

    Returns:
        A dictionary formatted as an API Gateway proxy response.
    """
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
