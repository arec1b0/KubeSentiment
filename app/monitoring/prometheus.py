"""
Prometheus monitoring and metrics collection.

This module provides Prometheus-compatible metrics for monitoring
the sentiment analysis service performance and health.
"""

import time
from typing import Optional

import torch
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

from app.core.config import get_settings

# Prometheus metrics
REQUEST_COUNT = Counter(
    "sentiment_requests_total",
    "Total number of sentiment analysis requests",
    ["endpoint", "method", "status_code"],
)

REQUEST_DURATION = Histogram(
    "sentiment_request_duration_seconds",
    "Request duration in seconds",
    ["endpoint", "method"],
)

INFERENCE_DURATION = Histogram(
    "sentiment_inference_duration_seconds", "Model inference duration in seconds"
)

ACTIVE_REQUESTS = Gauge("sentiment_active_requests", "Number of active requests being processed")

MODEL_LOADED = Gauge(
    "sentiment_model_loaded", "Whether the sentiment model is loaded (1) or not (0)"
)

TORCH_VERSION = Info("sentiment_torch_version", "PyTorch version information")

CUDA_AVAILABLE = Gauge("sentiment_cuda_available", "Whether CUDA is available (1) or not (0)")

CUDA_MEMORY_ALLOCATED = Gauge(
    "sentiment_cuda_memory_allocated_bytes", "CUDA memory allocated in bytes"
)

CUDA_MEMORY_RESERVED = Gauge(
    "sentiment_cuda_memory_reserved_bytes", "CUDA memory reserved in bytes"
)

CUDA_DEVICE_COUNT = Gauge("sentiment_cuda_device_count", "Number of CUDA devices available")

PREDICTION_SCORE = Histogram(
    "sentiment_prediction_score",
    "Distribution of prediction confidence scores",
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0],
)

TEXT_LENGTH = Histogram(
    "sentiment_text_length_characters",
    "Distribution of input text lengths",
    buckets=[10, 50, 100, 200, 500, 1000, 2000],
)

# Kafka consumer metrics
KAFKA_MESSAGES_CONSUMED = Counter(
    "kafka_messages_consumed_total",
    "Total number of Kafka messages consumed",
    ["topic", "consumer_group", "partition"],
)

KAFKA_MESSAGES_PROCESSED = Counter(
    "kafka_messages_processed_total",
    "Total number of Kafka messages successfully processed",
    ["topic", "consumer_group"],
)

KAFKA_MESSAGES_FAILED = Counter(
    "kafka_messages_failed_total",
    "Total number of Kafka messages that failed processing",
    ["topic", "consumer_group", "error_type"],
)

KAFKA_MESSAGES_RETRIED = Counter(
    "kafka_messages_retried_total",
    "Total number of Kafka messages retried",
    ["topic", "consumer_group"],
)

KAFKA_MESSAGES_DLQ = Counter(
    "kafka_messages_dlq_total",
    "Total number of Kafka messages sent to dead letter queue",
    ["topic", "consumer_group", "dlq_topic"],
)

KAFKA_PROCESSING_DURATION = Histogram(
    "kafka_message_processing_duration_seconds",
    "Time taken to process Kafka messages",
    ["topic", "consumer_group"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)

KAFKA_THROUGHPUT_TPS = Gauge(
    "kafka_consumer_throughput_tps",
    "Kafka consumer throughput in transactions per second",
    ["topic", "consumer_group"],
)

KAFKA_BATCH_SIZE = Histogram(
    "kafka_batch_size",
    "Distribution of Kafka batch sizes",
    ["topic", "consumer_group"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)

KAFKA_CONSUMER_LAG = Gauge(
    "kafka_consumer_lag",
    "Kafka consumer lag per partition",
    ["topic", "consumer_group", "partition"],
)

KAFKA_CONSUMER_GROUP_LAG = Gauge(
    "kafka_consumer_group_lag",
    "Total Kafka consumer group lag",
    ["consumer_group"],
)

KAFKA_BATCH_QUEUE_SIZE = Gauge(
    "kafka_batch_queue_size",
    "Current size of Kafka batch processing queue",
    ["topic", "consumer_group"],
)

KAFKA_ACTIVE_BATCHES = Gauge(
    "kafka_active_batches",
    "Number of active message batches being processed",
    ["topic", "consumer_group"],
)

# Async batch processing metrics
ASYNC_BATCH_JOBS_TOTAL = Counter(
    "async_batch_jobs_total",
    "Total number of async batch jobs created",
    ["priority"],
)

ASYNC_BATCH_JOBS_ACTIVE = Gauge(
    "async_batch_jobs_active",
    "Number of currently active async batch jobs",
)

ASYNC_BATCH_JOBS_COMPLETED_GAUGE = Gauge(
    "async_batch_jobs_completed_gauge",
    "Total number of completed async batch jobs",
)

ASYNC_BATCH_JOBS_FAILED_GAUGE = Gauge(
    "async_batch_jobs_failed_gauge",
    "Total number of failed async batch jobs",
)

ASYNC_BATCH_JOBS_COMPLETED = Counter(
    "async_batch_jobs_completed_total",
    "Total number of completed async batch jobs",
    ["priority", "status"],
)

ASYNC_BATCH_JOBS_FAILED = Counter(
    "async_batch_jobs_failed_total",
    "Total number of failed async batch jobs",
    ["priority"],
)

ASYNC_BATCH_PROCESSING_TIME = Histogram(
    "async_batch_processing_time_seconds",
    "Time taken to process async batch jobs",
    ["priority"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

ASYNC_BATCH_THROUGHPUT_TPS = Gauge(
    "async_batch_throughput_tps",
    "Async batch processing throughput in texts per second",
)

ASYNC_BATCH_QUEUE_SIZE = Gauge(
    "async_batch_queue_size",
    "Current size of async batch processing queue",
)

ASYNC_BATCH_SIZE = Histogram(
    "async_batch_size",
    "Distribution of async batch sizes",
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)

ASYNC_BATCH_CACHE_HITS = Counter(
    "async_batch_cache_hits_total",
    "Total number of async batch cache hits",
)

ASYNC_BATCH_CACHE_MISSES = Counter(
    "async_batch_cache_misses_total",
    "Total number of async batch cache misses",
)

# Anomaly buffer metrics
ANOMALY_DETECTED = Counter(
    "anomaly_detected_total",
    "Total number of anomalies detected",
    ["anomaly_type"],
)

ANOMALY_BUFFER_SIZE = Gauge(
    "anomaly_buffer_size",
    "Current size of the anomaly buffer",
)

ANOMALY_BUFFER_EVICTIONS = Counter(
    "anomaly_buffer_evictions_total",
    "Total number of anomaly buffer evictions",
    ["eviction_reason"],
)

# Redis cache metrics
REDIS_CACHE_HITS = Counter(
    "redis_cache_hits_total",
    "Total number of Redis cache hits",
    ["cache_type"],
)

REDIS_CACHE_MISSES = Counter(
    "redis_cache_misses_total",
    "Total number of Redis cache misses",
    ["cache_type"],
)

REDIS_CACHE_ERRORS = Counter(
    "redis_cache_errors_total",
    "Total number of Redis cache errors",
    ["operation", "error_type"],
)

REDIS_OPERATION_DURATION = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0],
)

REDIS_CONNECTIONS_ACTIVE = Gauge(
    "redis_connections_active",
    "Number of active Redis connections",
)

REDIS_CACHE_SIZE = Gauge(
    "redis_cache_size_bytes",
    "Approximate size of Redis cache in bytes",
    ["cache_type"],
)


class PrometheusMetrics:
    """Manages the collection and exposure of Prometheus metrics.

    This class centralizes all Prometheus metrics for the application, providing
    a single point of control for initializing, updating, and serving them. It
    includes caching for the metrics payload to reduce the overhead of
    generating the metrics on every scrape.

    Attributes:
        settings: The application's configuration settings.
    """

    def __init__(self):
        """Initializes the metrics collectors and sets static metric values."""
        self.settings = get_settings()
        self._initialize_static_metrics()
        # Metrics caching
        self._metrics_cache: Optional[str] = None
        self._metrics_cache_ts: Optional[float] = None

    def _initialize_static_metrics(self):
        """Initializes static metrics that do not change during runtime.

        This includes metrics like the PyTorch version and CUDA availability,
        which are set once at startup.
        """
        # Set torch version info
        TORCH_VERSION.info(
            {
                "version": torch.__version__,
                "cuda_version": torch.version.cuda if torch.cuda.is_available() else "N/A",
            }
        )

        # Set CUDA availability
        CUDA_AVAILABLE.set(1 if torch.cuda.is_available() else 0)
        CUDA_DEVICE_COUNT.set(torch.cuda.device_count() if torch.cuda.is_available() else 0)

    def update_system_metrics(self):
        """Updates dynamic system metrics, such as CUDA memory usage."""
        if torch.cuda.is_available():
            CUDA_MEMORY_ALLOCATED.set(torch.cuda.memory_allocated())
            CUDA_MEMORY_RESERVED.set(torch.cuda.memory_reserved())

    def record_request(self, endpoint: str, method: str, status_code: int):
        """Increments the counter for completed requests.

        Args:
            endpoint: The request's endpoint path.
            method: The HTTP method of the request.
            status_code: The HTTP status code of the response.
        """
        REQUEST_COUNT.labels(endpoint=endpoint, method=method, status_code=str(status_code)).inc()

    def record_request_duration(self, endpoint: str, method: str, duration: float):
        """Records the duration of a request in a histogram.

        Args:
            endpoint: The request's endpoint path.
            method: The HTTP method of the request.
            duration: The duration of the request in seconds.
        """
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(duration)

    def record_inference_duration(self, duration: float):
        """Records the duration of a model inference operation.

        Args:
            duration: The inference duration in seconds.
        """
        INFERENCE_DURATION.observe(duration)

    def record_prediction_metrics(self, score: float, text_length: int):
        """Records metrics specific to a prediction.

        This includes the prediction's confidence score and the length of the
        input text.

        Args:
            score: The confidence score of the prediction.
            text_length: The length of the input text.
        """
        PREDICTION_SCORE.observe(score)
        TEXT_LENGTH.observe(text_length)

    def set_model_status(self, is_loaded: bool):
        """Sets the gauge for the model's loading status.

        Args:
            is_loaded: `True` if the model is loaded, `False` otherwise.
        """
        MODEL_LOADED.set(1 if is_loaded else 0)

    def increment_active_requests(self):
        """Increments the gauge for the number of active requests."""
        ACTIVE_REQUESTS.inc()

    def decrement_active_requests(self):
        """Decrements the gauge for the number of active requests."""
        ACTIVE_REQUESTS.dec()

    def record_kafka_message_consumed(self, topic: str, consumer_group: str, partition: int):
        """Records a consumed Kafka message."""
        KAFKA_MESSAGES_CONSUMED.labels(
            topic=topic, consumer_group=consumer_group, partition=str(partition)
        ).inc()

    def record_kafka_message_processed(self, topic: str, consumer_group: str, count: int = 1):
        """Records successfully processed Kafka messages."""
        KAFKA_MESSAGES_PROCESSED.labels(topic=topic, consumer_group=consumer_group).inc(count)

    def record_kafka_message_failed(self, topic: str, consumer_group: str, error_type: str):
        """Records a failed Kafka message."""
        KAFKA_MESSAGES_FAILED.labels(
            topic=topic, consumer_group=consumer_group, error_type=error_type
        ).inc()

    def record_kafka_message_retried(self, topic: str, consumer_group: str):
        """Records a retried Kafka message."""
        KAFKA_MESSAGES_RETRIED.labels(topic=topic, consumer_group=consumer_group).inc()

    def record_kafka_message_dlq(self, topic: str, consumer_group: str, dlq_topic: str):
        """Records a Kafka message sent to dead letter queue."""
        KAFKA_MESSAGES_DLQ.labels(
            topic=topic, consumer_group=consumer_group, dlq_topic=dlq_topic
        ).inc()

    def record_kafka_processing_duration(self, topic: str, consumer_group: str, duration: float):
        """Records Kafka message processing duration."""
        KAFKA_PROCESSING_DURATION.labels(topic=topic, consumer_group=consumer_group).observe(
            duration
        )

    def set_kafka_throughput_tps(self, topic: str, consumer_group: str, throughput: float):
        """Sets the current Kafka consumer throughput in TPS."""
        KAFKA_THROUGHPUT_TPS.labels(topic=topic, consumer_group=consumer_group).set(throughput)

    def record_kafka_batch_size(self, topic: str, consumer_group: str, batch_size: int):
        """Records Kafka batch size."""
        KAFKA_BATCH_SIZE.labels(topic=topic, consumer_group=consumer_group).observe(batch_size)

    def set_kafka_consumer_lag(self, topic: str, consumer_group: str, partition: int, lag: int):
        """Sets Kafka consumer lag per partition."""
        KAFKA_CONSUMER_LAG.labels(
            topic=topic, consumer_group=consumer_group, partition=str(partition)
        ).set(lag)

    def set_kafka_consumer_group_lag(self, consumer_group: str, lag: int):
        """Sets total Kafka consumer group lag."""
        KAFKA_CONSUMER_GROUP_LAG.labels(consumer_group=consumer_group).set(lag)

    def set_kafka_batch_queue_size(self, topic: str, consumer_group: str, queue_size: int):
        """Sets current Kafka batch queue size."""
        KAFKA_BATCH_QUEUE_SIZE.labels(topic=topic, consumer_group=consumer_group).set(queue_size)

    def set_kafka_active_batches(self, topic: str, consumer_group: str, active_batches: int):
        """Sets number of active Kafka batches."""
        KAFKA_ACTIVE_BATCHES.labels(topic=topic, consumer_group=consumer_group).set(active_batches)

    def record_batch_job_submitted(self, priority: str, batch_size: int):
        """Records a batch job submission."""
        ASYNC_BATCH_JOBS_TOTAL.labels(priority=priority).inc()
        ASYNC_BATCH_SIZE.observe(batch_size)

    def set_async_batch_jobs_total(self, total_jobs: int):
        """Sets total number of async batch jobs."""
        # Note: This is a gauge, not a counter, so we don't use inc()

    def set_async_batch_jobs_active(self, active_jobs: int):
        """Sets number of active async batch jobs."""
        ASYNC_BATCH_JOBS_ACTIVE.set(active_jobs)

    def set_async_batch_jobs_completed(self, completed_jobs: int):
        """Sets total number of completed async batch jobs."""
        ASYNC_BATCH_JOBS_COMPLETED_GAUGE.set(completed_jobs)

    def set_async_batch_jobs_failed(self, failed_jobs: int):
        """Sets total number of failed async batch jobs."""
        ASYNC_BATCH_JOBS_FAILED_GAUGE.set(failed_jobs)

    def record_batch_job_completed(self, priority: str, batch_size: int, processing_time: float):
        """Records a completed batch job."""
        ASYNC_BATCH_JOBS_COMPLETED.labels(priority=priority, status="success").inc()
        ASYNC_BATCH_PROCESSING_TIME.labels(priority=priority).observe(processing_time)

    def record_batch_job_failed(self, priority: str, batch_size: int):
        """Records a failed batch job."""
        ASYNC_BATCH_JOBS_FAILED.labels(priority=priority).inc()

    def set_async_batch_throughput_tps(self, throughput: float):
        """Sets async batch processing throughput."""
        ASYNC_BATCH_THROUGHPUT_TPS.set(throughput)

    def set_async_batch_queue_size(self, queue_size: int):
        """Sets async batch queue size."""
        ASYNC_BATCH_QUEUE_SIZE.set(queue_size)

    def record_async_batch_cache_hit(self):
        """Records an async batch cache hit."""
        ASYNC_BATCH_CACHE_HITS.inc()

    def record_async_batch_cache_miss(self):
        """Records an async batch cache miss."""
        ASYNC_BATCH_CACHE_MISSES.inc()

    def get_metrics(self) -> str:
        """Generates and returns the metrics in Prometheus text format.

        This method includes a caching mechanism to avoid regenerating the
        metrics payload on every call, which can be important under high
        scrape frequencies.

        Returns:
            A string containing the metrics in Prometheus format.
        """
        # Serve cached metrics when TTL hasn't expired
        now = time.time()
        ttl = getattr(self.settings, "metrics_cache_ttl", 5)
        if self._metrics_cache and self._metrics_cache_ts and (now - self._metrics_cache_ts) < ttl:
            return self._metrics_cache

        # Update dynamic metrics before export and refresh cache
        self.update_system_metrics()
        payload = generate_latest().decode("utf-8")
        self._metrics_cache = payload
        self._metrics_cache_ts = now
        return payload

    def get_metrics_content_type(self) -> str:
        """Returns the appropriate content type for Prometheus metrics.

        Returns:
            The content type string for Prometheus metrics.
        """
        return CONTENT_TYPE_LATEST


# Global metrics instance
_metrics_instance = None


def get_metrics() -> PrometheusMetrics:
    """Retrieves a singleton instance of the `PrometheusMetrics` class.

    This factory function ensures that only one instance of the `PrometheusMetrics`
    class is created and used throughout the application, providing a single,
    consistent source for all metrics.

    Returns:
        The singleton instance of `PrometheusMetrics`.
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PrometheusMetrics()
    return _metrics_instance


from starlette.middleware.base import BaseHTTPMiddleware


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collects and exposes Prometheus metrics for HTTP requests.

    This middleware intercepts incoming requests to record several key metrics,
    including:
    - A counter for the total number of requests.
    - A histogram of request latencies.
    - A gauge for the number of currently active requests.

    These metrics are exposed via the `/metrics` endpoint, which is typically
    scraped by a Prometheus server.

    Attributes:
        metrics: An instance of the `PrometheusMetrics` class used to
            record metrics.
    """

    def __init__(self, app):
        """Initializes the metrics middleware.

        Args:
            app: The ASGI application instance.
        """
        super().__init__(app)
        self.metrics = get_metrics()

    async def dispatch(self, request, call_next):
        """Processes a request and records its metrics.

        This method wraps the request processing to measure its duration and
        capture its outcome (i.e., status code). It also increments and
        decrements the active request gauge. The `/metrics` endpoint itself is
        exempted from this process.

        Args:
            request: The incoming `Request` object.
            call_next: A function to call to pass the request to the next
                middleware or the application.

        Returns:
            The `Response` from the application.
        """
        # Skip metrics collection for the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()
        self.metrics.increment_active_requests()

        try:
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time
            self.metrics.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
            )
            self.metrics.record_request_duration(
                endpoint=request.url.path, method=request.method, duration=duration
            )

            return response

        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            self.metrics.record_request(
                endpoint=request.url.path, method=request.method, status_code=500
            )
            self.metrics.record_request_duration(
                endpoint=request.url.path, method=request.method, duration=duration
            )
            raise e

        finally:
            self.metrics.decrement_active_requests()


# Helper functions for anomaly buffer metrics
def record_anomaly_detected(anomaly_type: str):
    """Record an anomaly detection event."""
    ANOMALY_DETECTED.labels(anomaly_type=anomaly_type).inc()


def record_anomaly_buffer_size(size: int):
    """Record the current size of the anomaly buffer."""
    ANOMALY_BUFFER_SIZE.set(size)


def record_anomaly_buffer_eviction(eviction_reason: str):
    """Record an anomaly buffer eviction event."""
    ANOMALY_BUFFER_EVICTIONS.labels(eviction_reason=eviction_reason).inc()


# Helper functions for Redis cache metrics
def record_redis_cache_hit(cache_type: str = "prediction"):
    """Record a Redis cache hit."""
    REDIS_CACHE_HITS.labels(cache_type=cache_type).inc()


def record_redis_cache_miss(cache_type: str = "prediction"):
    """Record a Redis cache miss."""
    REDIS_CACHE_MISSES.labels(cache_type=cache_type).inc()


def record_redis_cache_error(operation: str, error_type: str):
    """Record a Redis cache error."""
    REDIS_CACHE_ERRORS.labels(operation=operation, error_type=error_type).inc()


def record_redis_operation_duration(operation: str, duration: float):
    """Record Redis operation duration."""
    REDIS_OPERATION_DURATION.labels(operation=operation).observe(duration)


def set_redis_connections_active(count: int):
    """Set the number of active Redis connections."""
    REDIS_CONNECTIONS_ACTIVE.set(count)


def set_redis_cache_size(cache_type: str, size_bytes: int):
    """Set the Redis cache size in bytes."""
    REDIS_CACHE_SIZE.labels(cache_type=cache_type).set(size_bytes)
