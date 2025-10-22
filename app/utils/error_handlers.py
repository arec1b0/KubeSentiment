"""
Error handling utilities for the MLOps sentiment analysis service.

This module provides centralized error handling functions to reduce code duplication
and improve maintainability across API endpoints.
"""

from fastapi import HTTPException

from ..logging_config import get_logger

logger = get_logger(__name__)


def handle_prediction_error(error: Exception, context: str = "prediction") -> None:
    """Handles exceptions that occur during the prediction process.

    This function standardizes error handling for prediction endpoints. It
    logs the error and raises an appropriate `HTTPException` based on the type
    of the original exception.

    Args:
        error: The exception that was caught.
        context: A string providing context about where the error occurred.

    Raises:
        HTTPException: An exception that FastAPI will convert into a JSON
            error response.
    """
    if isinstance(error, ValueError):
        raise HTTPException(status_code=422, detail=f"Invalid input: {str(error)}")
    elif isinstance(error, RuntimeError):
        logger.error(f"{context} error: {error}")
        raise HTTPException(status_code=500, detail=f"{context.capitalize()} failed: {str(error)}")
    else:
        logger.error(f"Unexpected error during {context}: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


def handle_metrics_error(error: Exception) -> None:
    """Handles exceptions that occur during the retrieval of JSON metrics.

    Args:
        error: The exception that was caught.

    Raises:
        HTTPException: A 500 Internal Server Error.
    """
    logger.error(f"Error retrieving metrics: {error}")
    raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


def handle_model_info_error(error: Exception) -> None:
    """Handles exceptions that occur during the retrieval of model information.

    Args:
        error: The exception that was caught.

    Raises:
        HTTPException: A 500 Internal Server Error.
    """
    logger.error(f"Error retrieving model info: {error}")
    raise HTTPException(status_code=500, detail="Failed to retrieve model information")


def handle_prometheus_metrics_error(error: Exception) -> None:
    """Handles exceptions that occur during the retrieval of Prometheus metrics.

    Args:
        error: The exception that was caught.

    Raises:
        HTTPException: A 500 Internal Server Error.
    """
    logger.error(f"Error retrieving Prometheus metrics: {error}")
    raise HTTPException(status_code=500, detail="Failed to retrieve metrics")
    raise HTTPException(status_code=500, detail="Failed to retrieve metrics")
