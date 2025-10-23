"""
Prometheus monitoring and metrics collection.

This module provides Prometheus-compatible metrics for monitoring
the sentiment analysis service performance and health.
"""

import time
from typing import Optional

import torch
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest

from .core.config import get_settings

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
    """
    Centralized metrics collection and management for Prometheus.
    """

    def __init__(self):
        """Initialize metrics with system information."""
        self.settings = get_settings()
        self._initialize_static_metrics()
        # Metrics caching
        self._metrics_cache: Optional[str] = None
        self._metrics_cache_ts: Optional[float] = None

    def _initialize_static_metrics(self):
        """Initialize static metrics that don't change during runtime."""
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
        """Update dynamic system metrics."""
        if torch.cuda.is_available():
            CUDA_MEMORY_ALLOCATED.set(torch.cuda.memory_allocated())
            CUDA_MEMORY_RESERVED.set(torch.cuda.memory_reserved())

    def record_request(self, endpoint: str, method: str, status_code: int):
        """Record a completed request."""
        REQUEST_COUNT.labels(endpoint=endpoint, method=method, status_code=str(status_code)).inc()

    def record_request_duration(self, endpoint: str, method: str, duration: float):
        """Record request duration."""
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(duration)

    def record_inference_duration(self, duration: float):
        """Record model inference duration."""
        INFERENCE_DURATION.observe(duration)

    def record_prediction_metrics(self, score: float, text_length: int):
        """Record prediction-specific metrics."""
        PREDICTION_SCORE.observe(score)
        TEXT_LENGTH.observe(text_length)

    def set_model_status(self, is_loaded: bool):
        """Update model loading status."""
        MODEL_LOADED.set(1 if is_loaded else 0)

    def increment_active_requests(self):
        """Increment active requests counter."""
        ACTIVE_REQUESTS.inc()

    def decrement_active_requests(self):
        """Decrement active requests counter."""
        ACTIVE_REQUESTS.dec()

    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
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
        """Get the correct content type for Prometheus metrics."""
        return CONTENT_TYPE_LATEST


# Global metrics instance
_metrics_instance = None


def get_metrics() -> PrometheusMetrics:
    """
    Get the global metrics instance (singleton pattern).

    Returns:
        PrometheusMetrics: The global metrics instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PrometheusMetrics()
    return _metrics_instance


from starlette.middleware.base import BaseHTTPMiddleware


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect request metrics.
    """

    def __init__(self, app):
        super().__init__(app)
        self.metrics = get_metrics()

    async def dispatch(self, request, call_next):
        """Process request and collect metrics."""
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
