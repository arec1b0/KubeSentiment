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

    # Add correlation ID if available (would be set by middleware)
    import threading

    correlation_id = getattr(threading.current_thread(), "correlation_id", None)
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    return event_dict


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
