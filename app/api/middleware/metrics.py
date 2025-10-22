"""
Metrics collection middleware.

This middleware automatically collects Prometheus metrics for all requests.
"""

import time

from fastapi import Request, Response
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
        from app.monitoring.prometheus import get_metrics

        self.metrics = get_metrics()

    async def dispatch(self, request: Request, call_next) -> Response:
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
