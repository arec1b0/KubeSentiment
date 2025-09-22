"""
Structured logging configuration for the MLOps sentiment analysis service.

This module provides structured logging setup using structlog for better
log parsing, correlation, and monitoring.
"""

import sys
import logging
from typing import Any, Dict
import structlog

from .config import get_settings


def setup_structured_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up structlog with JSON formatting, request correlation,
    and appropriate log levels.
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
    """
    Add request context to log entries.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The log event dictionary

    Returns:
        Dict[str, Any]: Updated event dictionary with request context
    """
    # Add service context
    event_dict.setdefault("service", "sentiment-analysis")
    event_dict.setdefault("version", get_settings().app_version)
    event_dict.setdefault(
        "component", logger.name if hasattr(logger, "name") else "unknown"
    )

    # Add correlation ID if available (would be set by middleware)
    import threading

    correlation_id = getattr(threading.current_thread(), "correlation_id", None)
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    # Standardize error context
    if method_name in ("error", "exception", "critical"):
        event_dict.setdefault("error_type", "application_error")
        if "exc_info" not in event_dict and method_name == "exception":
            event_dict["error_type"] = "exception"

    return event_dict


def log_api_request(
    logger, method: str, path: str, duration_ms: float, status_code: int
) -> None:
    """
    Standardized API request logging.

    Args:
        logger: The logger instance
        method: HTTP method
        path: Request path
        duration_ms: Request duration in milliseconds
        status_code: HTTP status code
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
    duration_ms: float = None,
    success: bool = True,
    error: str = None,
) -> None:
    """
    Standardized model operation logging.

    Args:
        logger: The logger instance
        operation: The operation type (load, predict, cache_hit, etc.)
        model_name: Name of the model
        duration_ms: Operation duration in milliseconds
        success: Whether the operation succeeded
        error: Error message if operation failed
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
    """
    Standardized security event logging.

    Args:
        logger: The logger instance
        event_type: Type of security event
        details: Additional event details
    """
    logger.warning(
        "Security event detected", event_type=event_type, security_alert=True, **details
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: The logger name (usually __name__)

    Returns:
        structlog.stdlib.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


# Global logger instance for convenience
logger = get_logger(__name__)
