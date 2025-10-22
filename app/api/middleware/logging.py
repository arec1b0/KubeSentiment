"""
Request logging middleware.

This middleware logs request start, completion, and timing information
with correlation IDs.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs detailed information about each incoming HTTP request.

    This middleware provides structured logging for every request, capturing
    details such as the method, path, duration, and status code. It ensures
    that request processing is observable and that failures are logged with
    sufficient context for debugging.
    """

    def __init__(self, app):
        """Initializes the request logging middleware.

        Args:
            app: The ASGI application instance.
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Logs the start and completion of a request.

        This method records the start time of a request, forwards it to the
        application, and then logs the completion details, including the total
        duration and response status.

        Args:
            request: The incoming `Request` object.
            call_next: A function to call to pass the request to the next
                middleware or the application.

        Returns:
            The `Response` from the application.
        """
        start_time = time.time()

        # Log request start
        logger.info(
            "Request started",
            http_method=request.method,
            http_path=request.url.path,
            http_query=str(request.query_params) if request.query_params else None,
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None,
            request_type="http_request",
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log request completion
            logger.info(
                "Request completed",
                http_method=request.method,
                http_path=request.url.path,
                http_status=response.status_code,
                duration_ms=round(duration_ms, 2),
                response_size=response.headers.get("content-length"),
                request_type="http_request",
            )

            return response

        except Exception as e:
            # Calculate duration for failed request
            duration_ms = (time.time() - start_time) * 1000

            # Log request failure
            logger.error(
                "Request failed",
                http_method=request.method,
                http_path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error=str(e),
                error_type=type(e).__name__,
                request_type="http_request",
                exc_info=True,
            )

            raise
