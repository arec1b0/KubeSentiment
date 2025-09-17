"""
Error handling utilities for the MLOps sentiment analysis service.

This module provides centralized error handling functions to reduce code duplication
and improve maintainability across API endpoints.
"""

from ..logging_config import get_logger
from fastapi import HTTPException

logger = get_logger(__name__)


def handle_prediction_error(error: Exception, context: str = "prediction") -> None:
    """
    Handle errors that occur during sentiment prediction.

    Args:
        error: The exception that occurred
        context: Context string for logging

    Raises:
        HTTPException: With appropriate status code and message
    """
    if isinstance(error, ValueError):
        raise HTTPException(status_code=422, detail=f"Invalid input: {str(error)}")
    elif isinstance(error, RuntimeError):
        logger.error(f"{context} error: {error}")
        raise HTTPException(
            status_code=500, detail=f"{context.capitalize()} failed: {str(error)}"
        )
    else:
        logger.error(f"Unexpected error during {context}: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


def handle_metrics_error(error: Exception) -> None:
    """
    Handle errors that occur during metrics retrieval.

    Args:
        error: The exception that occurred

    Raises:
        HTTPException: With appropriate status code and message
    """
    logger.error(f"Error retrieving metrics: {error}")
    raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


def handle_model_info_error(error: Exception) -> None:
    """
    Handle errors that occur during model information retrieval.

    Args:
        error: The exception that occurred

    Raises:
        HTTPException: With appropriate status code and message
    """
    logger.error(f"Error retrieving model info: {error}")
    raise HTTPException(status_code=500, detail="Failed to retrieve model information")


def handle_prometheus_metrics_error(error: Exception) -> None:
    """
    Handle errors that occur during Prometheus metrics retrieval.

    Args:
        error: The exception that occurred

    Raises:
        HTTPException: With appropriate status code and message
    """
    logger.error(f"Error retrieving Prometheus metrics: {error}")
    raise HTTPException(status_code=500, detail="Failed to retrieve metrics")
