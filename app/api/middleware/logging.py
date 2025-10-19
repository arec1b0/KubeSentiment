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
    """
    Enhanced request logging middleware with correlation ID support.

    Logs request start, completion, and timing information with correlation IDs.
    """

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with enhanced logging.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response: The processed response
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

