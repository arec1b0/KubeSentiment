"""
Prometheus monitoring and metrics collection.

This module provides Prometheus-compatible metrics for monitoring
the sentiment analysis service performance and health.
"""

import time
from typing import Optional

import torch
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest

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
