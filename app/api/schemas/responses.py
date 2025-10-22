"""
Response schemas for API endpoints.
"""

from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    """Defines the schema for a sentiment analysis prediction response.

    This model structures the output of a successful prediction request,
    providing the sentiment label, confidence score, and metadata about the
    prediction process.

    Attributes:
        label: The predicted sentiment label (e.g., 'POSITIVE').
        score: The confidence score of the prediction, from 0.0 to 1.0.
        inference_time_ms: The time taken for the model to make the prediction.
        model_name: The name of the model that was used.
        text_length: The length of the text that was analyzed.
        backend: The model backend that was used (e.g., 'pytorch', 'onnx').
        cached: A flag indicating if the result was served from the cache.
    """

    label: str = Field(..., description="Predicted sentiment label")
    score: float = Field(..., description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0)
    inference_time_ms: float = Field(..., description="Model inference time in milliseconds")
    model_name: str = Field(..., description="Name of the model used")
    text_length: int = Field(..., description="Length of processed text")
    backend: str = Field(..., description="Model backend used (pytorch/onnx)")
    cached: bool = Field(default=False, description="Whether result was cached")


class HealthResponse(BaseModel):
    """Defines the schema for the service's health check response.

    This model provides a structured response for the health check endpoint,
    indicating the status of the service and its components.

    Attributes:
        status: The overall status of the service (e.g., 'healthy').
        model_status: The status of the machine learning model.
        version: The version of the application.
        backend: The model backend currently in use.
        timestamp: The timestamp of when the health check was performed.
    """

    status: str = Field(..., description="Service status")
    model_status: str = Field(..., description="Model availability status")
    version: str = Field(..., description="Application version")
    backend: str = Field(..., description="Model backend in use")
    timestamp: float = Field(..., description="Health check timestamp")


class MetricsResponse(BaseModel):
    """Defines the schema for the service's JSON metrics response.

    This model structures the performance and system metrics that are exposed
    via the JSON metrics endpoint.

    Attributes:
        torch_version: The version of PyTorch being used.
        cuda_available: A flag indicating if CUDA is available.
        cuda_memory_allocated_mb: The amount of CUDA memory currently allocated.
        cuda_memory_reserved_mb: The amount of CUDA memory currently reserved.
        cuda_device_count: The number of available CUDA devices.
    """

    torch_version: str = Field(..., description="PyTorch version")
    cuda_available: bool = Field(..., description="CUDA availability")
    cuda_memory_allocated_mb: float = Field(..., description="CUDA memory allocated in MB")
    cuda_memory_reserved_mb: float = Field(..., description="CUDA memory reserved in MB")
    cuda_device_count: int = Field(..., description="Number of CUDA devices")


class ModelInfoResponse(BaseModel):
    """Defines the schema for the model information response.

    This model provides detailed metadata about the currently loaded machine
    learning model.

    Attributes:
        model_name: The name of the model.
        model_type: The type of the model (e.g., 'pytorch', 'onnx').
        backend: The backend currently in use for the model.
        is_loaded: A flag indicating if the model has been loaded into memory.
        is_ready: A flag indicating if the model is ready for inference.
        cache_size: The current number of items in the prediction cache.
        cache_max_size: The maximum capacity of the prediction cache.
    """

    model_name: str = Field(..., description="Model name")
    model_type: str = Field(..., description="Model type (pytorch/onnx)")
    backend: str = Field(..., description="Backend in use")
    is_loaded: bool = Field(..., description="Whether model is loaded")
    is_ready: bool = Field(..., description="Whether model is ready for inference")
    cache_size: int = Field(..., description="Current prediction cache size")
    cache_max_size: int = Field(..., description="Maximum cache size")
