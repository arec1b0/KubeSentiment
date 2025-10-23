"""
Structured logging configuration for the MLOps sentiment analysis service.

This module provides structured logging setup using structlog for better
log parsing, correlation, and monitoring with correlation ID support.
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

import structlog

from app.core.config import get_settings

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def setup_structured_logging() -> None:
    """Configures structured, JSON-formatted logging for the application.

    This function sets up `structlog` to produce structured logs in JSON
    format, which is ideal for log management systems. It configures a chain
    of processors to add contextual information, such as timestamps, log levels,
    and correlation IDs, to every log entry.
    """
    settings = get_settings()

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    # Configure structlog
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _add_request_context,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=shared_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _add_request_context(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Adds service and request context to log entries.

    This `structlog` processor enriches log entries with contextual information,
    such as the service name, version, and the current correlation ID. This
    data is crucial for filtering and analyzing logs in a microservices
    environment.

    Args:
        logger: The standard library logger instance.
        method_name: The name of the logging method (e.g., 'info', 'error').
        event_dict: The dictionary representing the log entry.

    Returns:
        The enriched log entry dictionary.
    """
    # Add service context
    event_dict.setdefault("service", "sentiment-analysis")
    event_dict.setdefault("version", get_settings().app_version)
    event_dict.setdefault("component", logger.name if hasattr(logger, "name") else "unknown")

    # Add correlation ID from context variable
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    # Add trace context for distributed tracing
    event_dict.setdefault("trace_id", correlation_id)

    # Standardize error context
    if method_name in ("error", "exception", "critical"):
        event_dict.setdefault("error_type", "application_error")
        if "exc_info" not in event_dict and method_name == "exception":
            event_dict["error_type"] = "exception"

    return event_dict


def log_api_request(logger, method: str, path: str, duration_ms: float, status_code: int) -> None:
    """Logs a standardized message for an API request.

    This function ensures that all API requests are logged in a consistent
    format, including the HTTP method, path, status code, and duration.
    This standardization simplifies log parsing and monitoring.

    Args:
        logger: The `structlog` logger instance to use.
        method: The HTTP method of the request (e.g., 'GET', 'POST').
        path: The path of the request.
        duration_ms: The duration of the request in milliseconds.
        status_code: The HTTP status code of the response.
    """
    logger.info(
        "API request completed",
        http_method=method,
        http_path=path,
        http_status=status_code,
        duration_ms=duration_ms,
        request_type="api",
    )


def log_model_operation(
    logger,
    operation: str,
    model_name: str,
    duration_ms: Optional[float] = None,
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    """Logs a standardized message for a model operation.

    This function provides a consistent format for logging machine learning
    model operations, such as loading a model or making a prediction. It
    captures the operation type, model name, duration, and success status.

    Args:
        logger: The `structlog` logger instance to use.
        operation: The type of model operation (e.g., 'load', 'predict').
        model_name: The name of the model involved in the operation.
        duration_ms: The duration of the operation in milliseconds.
        success: A boolean indicating whether the operation was successful.
        error: An error message if the operation failed.
    """
    log_data = {
        "operation": operation,
        "model_name": model_name,
        "operation_type": "model",
        "success": success,
    }

    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms

    if error:
        log_data["error"] = error
        logger.error("Model operation failed", **log_data)
    else:
        logger.info("Model operation completed", **log_data)


def log_security_event(logger, event_type: str, details: Dict[str, Any]) -> None:
    """Logs a standardized message for a security-related event.

    This function should be used to log events that may have security
    implications, such as failed authentication attempts. It ensures that
    security events are easily identifiable in the logs.

    Args:
        logger: The `structlog` logger instance to use.
        event_type: The type of security event (e.g., 'invalid_api_key').
        details: A dictionary containing additional details about the event.
    """
    logger.warning("Security event detected", event_type=event_type, security_alert=True, **details)


def set_correlation_id(correlation_id: str) -> None:
    """Sets the correlation ID for the current asynchronous context.

    The correlation ID is stored in a `ContextVar`, which makes it accessible
    throughout the execution of a single request or task without needing to

    pass it explicitly through function arguments.

    Args:
        correlation_id: The correlation ID to set for the current context.
    """
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Retrieves the correlation ID from the current asynchronous context.

    Returns:
        The current correlation ID, or `None` if it has not been set.
    """
    return correlation_id_var.get()


def generate_correlation_id() -> str:
    """Generates a new, unique correlation ID.

    This function creates a new UUID version 4 and returns it as a string.

    Returns:
        A new, unique correlation ID.
    """
    return str(uuid.uuid4())


def clear_correlation_id() -> None:
    """Clears the correlation ID from the current context."""
    correlation_id_var.set(None)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retrieves a `structlog` logger instance.

    This is the primary function for obtaining a logger in the application.
    It returns a `structlog` logger that is configured with the processors
    defined in `setup_structured_logging`.

    Args:
        name: The name of the logger, typically the module's `__name__`.

    Returns:
        A configured `structlog` logger instance.
    """
    return structlog.get_logger(name)


def get_contextual_logger(name: str, **extra_context) -> structlog.stdlib.BoundLogger:
    """Retrievess a logger with additional, permanently bound context.

    This function is useful when you want to create a logger that will include
    specific context in every message it logs. For example, you might bind a
    `user_id` to a logger that handles user-specific operations.

    Args:
        name: The name of the logger, typically the module's `__name__`.
        **extra_context: Keyword arguments to be bound to the logger.

    Returns:
        A `structlog` logger with the specified context bound to it.
    """
    logger = structlog.get_logger(name)

    # Add correlation ID if available
    correlation_id = get_correlation_id()
    if correlation_id:
        extra_context["correlation_id"] = correlation_id

    return logger.bind(**extra_context) if extra_context else logger


# Global logger instance for convenience
logger = get_logger(__name__)
