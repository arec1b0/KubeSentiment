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
    """Manages correlation IDs for distributed tracing and request tracking.

    This middleware is responsible for ensuring that every request has a unique
    correlation ID. It checks for an existing ID in the request headers; if one
    is not found, it generates a new one. This ID is then available throughout
    the request's lifecycle via a context variable and is included in the
    response headers.

    Attributes:
        header_name: The name of the request header for the correlation ID.
        response_header_name: The name of the response header for the
            correlation ID.
    """

    def __init__(
        self,
        app,
        header_name: str = "X-Correlation-ID",
        response_header_name: str = "X-Correlation-ID",
    ):
        """Initializes the correlation ID middleware.

        Args:
            app: The ASGI application instance.
            header_name: The name of the request header to check for the
                correlation ID.
            response_header_name: The name of the response header to which the
                correlation ID will be added.
        """
        super().__init__(app)
        self.header_name = header_name
        self.response_header_name = response_header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Processes a request to manage the correlation ID.

        This method extracts or generates a correlation ID, sets it in the
        current context, and ensures it is cleared after the request is
        complete. It also adds the correlation ID to the response headers.

        Args:
            request: The incoming `Request` object.
            call_next: A function to call to pass the request to the next
                middleware or the application.

        Returns:
            The `Response` from the application, with the correlation ID header
            added.
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
