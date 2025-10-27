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
    kafka_status: Optional[str] = Field(None, description="Kafka consumer status (if enabled)")


class KafkaMetricsResponse(BaseModel):
    """Defines the schema for Kafka consumer metrics response.

    This model provides detailed metrics about the Kafka consumer performance,
    including throughput, processing statistics, and health indicators.

    Attributes:
        messages_consumed: Total number of messages consumed from Kafka.
        messages_processed: Total number of messages successfully processed.
        messages_failed: Total number of messages that failed processing.
        messages_retried: Total number of messages that were retried.
        messages_sent_to_dlq: Total number of messages sent to dead letter queue.
        total_processing_time_ms: Total processing time in milliseconds.
        avg_processing_time_ms: Average processing time per message in milliseconds.
        throughput_tps: Current throughput in transactions per second.
        consumer_group_lag: Current consumer group lag.
        running: Whether the Kafka consumer is currently running.
        consumer_threads: Number of consumer threads.
        pending_batches: Number of pending message batches.
        batch_queue_size: Current size of the batch processing queue.
    """

    messages_consumed: int = Field(..., description="Total messages consumed")
    messages_processed: int = Field(..., description="Total messages successfully processed")
    messages_failed: int = Field(..., description="Total messages that failed processing")
    messages_retried: int = Field(..., description="Total messages retried")
    messages_sent_to_dlq: int = Field(..., description="Total messages sent to DLQ")
    total_processing_time_ms: float = Field(..., description="Total processing time (ms)")
    avg_processing_time_ms: float = Field(..., description="Average processing time per message (ms)")
    throughput_tps: float = Field(..., description="Current throughput (TPS)")
    consumer_group_lag: int = Field(..., description="Current consumer group lag")
    running: bool = Field(..., description="Whether consumer is running")
    consumer_threads: int = Field(..., description="Number of consumer threads")
    pending_batches: int = Field(..., description="Number of pending message batches")
    batch_queue_size: int = Field(..., description="Current batch queue size")


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


class HealthDetail(BaseModel):
    """Represents the detailed health status of a component."""

    status: str = Field(..., description="Health status of the component")
    error: str | None = Field(None, description="Error message if component is unhealthy")


class ComponentHealth(BaseModel):
    """Represents the health of a single dependency or component."""

    component_name: str = Field(..., description="Name of the component")
    details: HealthDetail = Field(..., description="Detailed health status")


class DetailedHealthResponse(BaseModel):
    """Defines the schema for a detailed health check response."""

    status: str = Field(..., description="Overall service status")
    version: str = Field(..., description="Application version")
    timestamp: float = Field(..., description="Health check timestamp")
    dependencies: list[ComponentHealth] = Field(
        ..., description="Health status of individual dependencies"
    )
