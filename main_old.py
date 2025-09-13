import time
import logging
from fastapi import FastAPI, Request, Response, HTTPException
from pydantic import BaseModel
from transformers import pipeline
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Application Setup ---
app = FastAPI(
    title="ML Model Serving API",
    description="A FastAPI service for sentiment analysis using a Hugging Face transformer model.",
    version="1.0.0",
)

# --- Model Loading ---
# Load the sentiment analysis model once at application startup to optimize performance.
# This avoids reloading the model on every incoming request.
try:
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english"
    )
    logger.info("Sentiment analysis model loaded successfully.")
except Exception as e:
    # If model loading fails, log the error and set the pipeline to None.
    # The service will run in a degraded state.
    logger.error(f"Failed to load sentiment analysis model: {e}")
    sentiment_pipeline = None

# --- Pydantic Models ---
class TextIn(BaseModel):
    """Defines the input schema for a single text payload."""
    text: str

class PredictionOut(BaseModel):
    """Defines the output schema for a sentiment prediction."""
    label: str
    score: float

# --- API Endpoints ---
@app.post("/predict", response_model=PredictionOut)
def predict(payload: TextIn, response: Response):
    """
    Performs sentiment analysis on the input text.

    - **payload**: The input text for analysis.
    - **returns**: The predicted sentiment label and its confidence score.
    """
    if not sentiment_pipeline:
        raise HTTPException(
            status_code=503,
            detail="Service Unavailable: Model is not loaded."
        )

    start_time = time.time()
    result = sentiment_pipeline(payload.text)[0]
    inference_time = (time.time() - start_time) * 1000

    # Add custom header with model inference time in milliseconds
    response.headers["X-Inference-Time-MS"] = f"{inference_time:.2f}"

    return PredictionOut(label=result["label"], score=result["score"])


@app.get("/health")
def health_check():
    """
    Provides a health check endpoint for monitoring service status.
    """
    model_status = "available" if sentiment_pipeline else "unavailable"
    return {"status": "ok", "model_status": model_status}


@app.get("/metrics")
def get_metrics():
    """
    Returns basic service metrics, such as PyTorch version and CUDA memory usage.
    In a production environment, this would typically be exposed via a dedicated
    metrics library like Prometheus.
    """
    if torch.cuda.is_available():
        cuda_memory_allocated = f"{torch.cuda.memory_allocated() / 1e6:.2f} MB"
    else:
        cuda_memory_allocated = "N/A (CUDA not available)"

    return {
        "torch_version": torch.__version__,
        "cuda_memory_allocated": cuda_memory_allocated
    }

# --- Middleware ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Middleware to calculate and add the total request processing time
    to the response headers.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time-MS"] = f"{process_time:.2f}"
    return response
