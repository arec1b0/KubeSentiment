"""
Correlation ID middleware for request tracing.

This middleware automatically generates or extracts correlation IDs from requests
and ensures they are available throughout the request lifecycle.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import (
    clear_correlation_id,
    generate_correlation_id,
    get_logger,
    set_correlation_id,
)

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation IDs for request tracing.

    This middleware:
    1. Extracts correlation ID from request headers or generates a new one
    2. Sets the correlation ID in the logging context
    3. Adds the correlation ID to response headers
    4. Clears the correlation ID after request completion
    """

    def __init__(
        self,
        app,
        header_name: str = "X-Correlation-ID",
        response_header_name: str = "X-Correlation-ID",
    ):
        """
        Initialize the correlation ID middleware.

        Args:
            app: The ASGI application
            header_name: Name of the request header to look for correlation ID
            response_header_name: Name of the response header to set correlation ID
        """
        super().__init__(app)
        self.header_name = header_name
        self.response_header_name = response_header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with correlation ID handling.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response: The response with correlation ID header
        """
        # Extract or generate correlation ID
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = generate_correlation_id()
            logger.debug(
                "Generated new correlation ID",
                correlation_id=correlation_id,
                path=request.url.path,
                method=request.method,
            )
        else:
            logger.debug(
                "Using provided correlation ID",
                correlation_id=correlation_id,
                path=request.url.path,
                method=request.method,
            )

        # Set correlation ID in context
        set_correlation_id(correlation_id)

        try:
            # Process request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers[self.response_header_name] = correlation_id

            return response

        except Exception as e:
            # Log error with correlation ID
            logger.error(
                "Request processing failed",
                correlation_id=correlation_id,
                path=request.url.path,
                method=request.method,
                error=str(e),
                exc_info=True,
            )
            raise

        finally:
            # Clean up correlation ID from context
            clear_correlation_id()


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
        import time

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
