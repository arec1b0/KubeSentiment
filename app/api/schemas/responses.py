"""
Response schemas for API endpoints.
"""

from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    """Response schema for sentiment predictions."""

    label: str = Field(..., description="Predicted sentiment label")
    score: float = Field(..., description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0)
    inference_time_ms: float = Field(
        ..., description="Model inference time in milliseconds"
    )
    model_name: str = Field(..., description="Name of the model used")
    text_length: int = Field(..., description="Length of processed text")
    backend: str = Field(..., description="Model backend used (pytorch/onnx)")
    cached: bool = Field(default=False, description="Whether result was cached")


class HealthResponse(BaseModel):
    """Response schema for health checks."""

    status: str = Field(..., description="Service status")
    model_status: str = Field(..., description="Model availability status")
    version: str = Field(..., description="Application version")
    backend: str = Field(..., description="Model backend in use")
    timestamp: float = Field(..., description="Health check timestamp")


class MetricsResponse(BaseModel):
    """Response schema for service metrics."""

    torch_version: str = Field(..., description="PyTorch version")
    cuda_available: bool = Field(..., description="CUDA availability")
    cuda_memory_allocated_mb: float = Field(
        ..., description="CUDA memory allocated in MB"
    )
    cuda_memory_reserved_mb: float = Field(
        ..., description="CUDA memory reserved in MB"
    )
    cuda_device_count: int = Field(..., description="Number of CUDA devices")


class ModelInfoResponse(BaseModel):
    """Response schema for model information."""

    model_name: str = Field(..., description="Model name")
    model_type: str = Field(..., description="Model type (pytorch/onnx)")
    backend: str = Field(..., description="Backend in use")
    is_loaded: bool = Field(..., description="Whether model is loaded")
    is_ready: bool = Field(..., description="Whether model is ready for inference")
    cache_size: int = Field(..., description="Current prediction cache size")
    cache_max_size: int = Field(..., description="Maximum cache size")

