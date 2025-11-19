"""
Response schemas for API endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    """Defines the schema for a sentiment analysis prediction response.

    This model structures the output of a successful prediction request,
    providing the sentiment label, confidence score, and metadata about the
    prediction process. Used for both single predictions and batch results.

    Attributes:
        label: The predicted sentiment label (POSITIVE, NEGATIVE, NEUTRAL).
        score: The confidence score of the prediction (0.0 to 1.0, higher = more confident).
        inference_time_ms: The time taken for the model to make the prediction in milliseconds.
        model_name: The name of the model that was used for inference.
        text_length: The length of the analyzed text in characters.
        backend: The model backend used (onnx or pytorch).
        cached: Whether this result was served from Redis cache (faster response).
        features: Optional advanced text features (available in detailed mode).

    Example:
        ```json
        {
            "label": "POSITIVE",
            "score": 0.9823,
            "inference_time_ms": 145.2,
            "model_name": "distilbert-base-uncased-finetuned-sst-2-english",
            "text_length": 48,
            "backend": "onnx",
            "cached": false,
            "features": null
        }
        ```
    """

    label: str = Field(
        ...,
        description="Predicted sentiment label: POSITIVE, NEGATIVE, or NEUTRAL",
        examples=["POSITIVE", "NEGATIVE", "NEUTRAL"]
    )
    score: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0. Scores closer to 1.0 indicate higher confidence.",
        ge=0.0,
        le=1.0,
        examples=[0.9823, 0.5432, 0.1234]
    )
    inference_time_ms: float = Field(
        ...,
        description="Model inference time in milliseconds. Cached responses typically <50ms, uncached 100-300ms.",
        examples=[145.2, 52.8, 287.5]
    )
    model_name: str = Field(
        ...,
        description="Name of the model used for inference. Multiple models may be supported in different configurations.",
        examples=["distilbert-base-uncased-finetuned-sst-2-english"]
    )
    text_length: int = Field(
        ...,
        description="Length of the analyzed text in characters (after stripping whitespace).",
        examples=[48, 125, 7500]
    )
    backend: str = Field(
        ...,
        description="Model backend used for inference. ONNX is optimized for production (160x faster cold-start), PyTorch for development.",
        examples=["onnx", "pytorch"]
    )
    cached: bool = Field(
        default=False,
        description="Whether this result was served from Redis cache. Cached results have significantly lower latency (<50ms).",
        examples=[True, False]
    )
    features: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional advanced text features (word count, sentiment word density, etc). Only populated in detailed mode.",
        examples=[{"word_count": 8, "avg_word_length": 4.2}]
    )


class HealthResponse(BaseModel):
    """Defines the schema for the service's health check response.

    This model provides a quick health check of the service and its components.
    Use /api/v1/health for quick checks and /api/v1/health/details for comprehensive
    component-level details.

    Attributes:
        status: Overall service health status.
        model_status: Machine learning model availability and readiness.
        version: Application version number.
        backend: Model backend currently in use (onnx or pytorch).
        timestamp: Unix timestamp when health check was performed.
        kafka_status: Optional Kafka integration status (if enabled).
        async_batch_status: Optional async batch service status (if enabled).

    Example:
        ```json
        {
            "status": "healthy",
            "model_status": "loaded",
            "version": "1.0.0",
            "backend": "onnx",
            "timestamp": 1734596400.123,
            "kafka_status": "connected",
            "async_batch_status": "operational"
        }
        ```
    """

    status: str = Field(
        ...,
        description="Overall service status: healthy, degraded, or unhealthy",
        examples=["healthy", "degraded", "unhealthy"]
    )
    model_status: str = Field(
        ...,
        description="Model availability: loaded, loading, unloaded, or error",
        examples=["loaded", "loading"]
    )
    version: str = Field(
        ...,
        description="Application version number",
        examples=["1.0.0", "1.2.3"]
    )
    backend: str = Field(
        ...,
        description="Model backend in use: onnx (production) or pytorch (development)",
        examples=["onnx", "pytorch"]
    )
    timestamp: float = Field(
        ...,
        description="Unix timestamp of when health check was performed",
        examples=[1734596400.123]
    )
    kafka_status: Optional[str] = Field(
        None,
        description="Kafka integration status (if enabled): connected, disconnected, or error",
        examples=["connected", "disconnected"]
    )
    async_batch_status: Optional[str] = Field(
        None,
        description="Async batch service status (if enabled): operational, degraded, or unavailable",
        examples=["operational", "degraded"]
    )


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
    avg_processing_time_ms: float = Field(
        ..., description="Average processing time per message (ms)"
    )
    throughput_tps: float = Field(..., description="Current throughput (TPS)")
    consumer_group_lag: int = Field(..., description="Current consumer group lag")
    running: bool = Field(..., description="Whether consumer is running")
    consumer_threads: int = Field(..., description="Number of consumer threads")
    pending_batches: int = Field(..., description="Number of pending message batches")
    batch_queue_size: int = Field(..., description="Current batch queue size")


class BatchJobResponse(BaseModel):
    """Response for batch job creation.

    Returned immediately after submitting a batch processing request. Contains
    the job ID needed to track progress and retrieve results.

    Attributes:
        job_id: Unique identifier for tracking this batch job throughout its lifecycle.
        status: Current job status (typically 'pending' on creation).
        total_texts: Total number of texts submitted in this batch.
        estimated_completion_seconds: Estimated time until completion in seconds.
        created_at: Unix timestamp when the job was created.
        priority: Processing priority level (low, medium, high).
        progress_percentage: Current processing progress (0-100%).

    Example:
        ```json
        {
            "job_id": "job_550e8400e29b41d4a716446655440000",
            "status": "pending",
            "total_texts": 3,
            "estimated_completion_seconds": 45,
            "created_at": 1734596400.123,
            "priority": "medium",
            "progress_percentage": 0.0
        }
        ```
    """

    job_id: str = Field(
        ...,
        description="Unique batch job identifier. Use this to track progress and retrieve results.",
        examples=["job_550e8400e29b41d4a716446655440000"]
    )
    status: str = Field(
        ...,
        description="Current job status: pending, processing, completed, or failed",
        examples=["pending", "processing", "completed"]
    )
    total_texts: int = Field(
        ...,
        description="Total number of texts submitted in this batch",
        examples=[10, 100, 500]
    )
    estimated_completion_seconds: int = Field(
        ...,
        description="Estimated time until completion in seconds",
        examples=[15, 45, 120]
    )
    created_at: float = Field(
        ...,
        description="Unix timestamp when the job was created",
        examples=[1734596400.123]
    )
    priority: str = Field(
        ...,
        description="Processing priority: low (background), medium (normal), or high (fast)",
        examples=["low", "medium", "high"]
    )
    progress_percentage: float = Field(
        default=0.0,
        description="Current processing progress as percentage (0-100%)",
        examples=[0.0, 50.5, 100.0]
    )


class BatchJobStatus(BaseModel):
    """Detailed status of a batch job.

    Attributes:
        job_id: Unique identifier for the batch job.
        status: Current status (pending, processing, completed, failed).
        total_texts: Total number of texts in the batch.
        processed_texts: Number of texts processed so far.
        failed_texts: Number of texts that failed processing.
        progress_percentage: Processing progress (0-100%).
        created_at: Timestamp when job was created.
        started_at: Timestamp when processing started.
        completed_at: Timestamp when processing completed.
        estimated_completion_seconds: Estimated time for completion.
        priority: Processing priority.
        error: Error message if job failed.
    """

    job_id: str = Field(..., description="Unique batch job identifier")
    status: str = Field(..., description="Current job status")
    total_texts: int = Field(..., description="Total texts in batch")
    processed_texts: int = Field(default=0, description="Texts processed so far")
    failed_texts: int = Field(default=0, description="Texts that failed processing")
    progress_percentage: float = Field(default=0.0, description="Processing progress")
    created_at: float = Field(..., description="Job creation timestamp")
    started_at: Optional[float] = Field(None, description="Processing start timestamp")
    completed_at: Optional[float] = Field(None, description="Processing completion timestamp")
    estimated_completion_seconds: int = Field(..., description="Estimated completion time")
    priority: str = Field(..., description="Processing priority")
    error: Optional[str] = Field(None, description="Error message if failed")


class BatchPredictionResponse(BaseModel):
    """Response for batch prediction results.

    Attributes:
        job_id: Unique identifier for the batch job.
        results: List of prediction results for each text.
        summary: Summary statistics for the batch.
        processing_time_seconds: Total processing time.
        average_inference_time_ms: Average inference time per text.
    """

    job_id: str = Field(..., description="Batch job identifier")
    results: List[PredictionResponse] = Field(..., description="Individual prediction results")
    summary: Dict[str, Any] = Field(..., description="Batch processing summary")
    processing_time_seconds: float = Field(..., description="Total processing time")
    average_inference_time_ms: float = Field(..., description="Average inference time per text")


class BatchPredictionResults(BaseModel):
    """Paginated results for large batch jobs.

    Attributes:
        job_id: Unique identifier for the batch job.
        results: List of prediction results (paginated).
        total_results: Total number of results available.
        page: Current page number.
        page_size: Number of results per page.
        has_more: Whether there are more results available.
        summary: Summary statistics for the batch.
    """

    job_id: str = Field(..., description="Batch job identifier")
    results: List[PredictionResponse] = Field(..., description="Prediction results for this page")
    total_results: int = Field(..., description="Total number of results")
    page: int = Field(..., description="Current page number", ge=1)
    page_size: int = Field(..., description="Results per page", ge=1, le=1000)
    has_more: bool = Field(..., description="Whether more results are available")
    summary: Dict[str, Any] = Field(..., description="Batch processing summary")


class AsyncBatchMetricsResponse(BaseModel):
    """Metrics for async batch processing.

    Attributes:
        total_jobs: Total number of batch jobs created.
        active_jobs: Number of currently active jobs.
        completed_jobs: Number of completed jobs.
        failed_jobs: Number of failed jobs.
        average_processing_time_seconds: Average processing time per job.
        average_throughput_tps: Average throughput in texts per second.
        queue_size: Current size of the batch processing queue.
        average_batch_size: Average size of processed batches.
        processing_efficiency: Processing efficiency percentage.
    """

    total_jobs: int = Field(..., description="Total batch jobs created")
    active_jobs: int = Field(..., description="Currently active jobs")
    completed_jobs: int = Field(..., description="Successfully completed jobs")
    failed_jobs: int = Field(..., description="Failed jobs")
    average_processing_time_seconds: float = Field(..., description="Average processing time")
    average_throughput_tps: float = Field(..., description="Average throughput (TPS)")
    queue_size: int = Field(..., description="Current batch queue size")
    average_batch_size: float = Field(..., description="Average batch size")
    processing_efficiency: float = Field(..., description="Processing efficiency %")


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
    learning model, including its readiness for inference and cache statistics.

    Attributes:
        model_name: Name of the loaded machine learning model.
        model_type: Type of model architecture (transformer, etc.).
        backend: Backend implementation (onnx or pytorch).
        is_loaded: Whether model is loaded into memory.
        is_ready: Whether model is ready for inference requests.
        cache_size: Current number of cached predictions (LRU).
        cache_max_size: Maximum prediction cache capacity.

    Example:
        ```json
        {
            "model_name": "distilbert-base-uncased-finetuned-sst-2-english",
            "model_type": "transformer",
            "backend": "onnx",
            "is_loaded": true,
            "is_ready": true,
            "cache_size": 450,
            "cache_max_size": 1000
        }
        ```
    """

    model_name: str = Field(
        ...,
        description="Name of the loaded machine learning model",
        examples=["distilbert-base-uncased-finetuned-sst-2-english"]
    )
    model_type: str = Field(
        ...,
        description="Model architecture type (e.g., transformer, CNN, RNN)",
        examples=["transformer"]
    )
    backend: str = Field(
        ...,
        description="Backend implementation: onnx (production, 160x faster) or pytorch (development)",
        examples=["onnx", "pytorch"]
    )
    is_loaded: bool = Field(
        ...,
        description="Whether the model is loaded into memory and available for inference",
        examples=[True, False]
    )
    is_ready: bool = Field(
        ...,
        description="Whether the model is fully initialized and ready to process requests",
        examples=[True, False]
    )
    cache_size: int = Field(
        ...,
        description="Current number of predictions stored in Redis cache",
        examples=[450, 0, 1000]
    )
    cache_max_size: int = Field(
        ...,
        description="Maximum capacity of the prediction cache (LRU eviction when full)",
        examples=[1000, 5000]
    )


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
