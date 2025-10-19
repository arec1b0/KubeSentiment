"""
Metrics collection middleware.

This middleware automatically collects Prometheus metrics for all requests.
"""

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect request metrics.
    """

    def __init__(self, app):
        super().__init__(app)
        from app.monitoring.prometheus import get_metrics

        self.metrics = get_metrics()

    async def dispatch(self, request: Request, call_next) -> Response:
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

