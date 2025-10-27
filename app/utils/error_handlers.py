"""
Error handling utilities for the MLOps sentiment analysis service.

This module provides centralized error handling functions to reduce code
duplication and improve maintainability across the API endpoints. These
handlers are designed to catch specific exceptions and convert them into
standardized, user-friendly HTTP responses, ensuring consistent error
reporting throughout the application.
"""

from fastapi import HTTPException

from ..core.logging import get_logger

logger = get_logger(__name__)


def handle_prediction_error(error: Exception, context: str = "prediction") -> None:
    """Handles exceptions that occur during the prediction process.

    This function standardizes error handling for all prediction-related
    endpoints. It logs the error with relevant context and raises an
    appropriate `HTTPException` based on the type of the original exception,
    translating low-level errors into meaningful HTTP status codes and messages.

    Args:
        error: The exception that was caught during the prediction process.
        context: A string providing context about where the error occurred
                 (e.g., 'single_prediction', 'batch_prediction').

    Raises:
        HTTPException: An exception that FastAPI will convert into a structured
                       JSON error response. The status code is 422 for input
                       errors and 500 for runtime or unexpected errors.
    """
    if isinstance(error, ValueError):
        logger.warning(f"Validation error in {context}: {error}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Invalid input: {str(error)}")
    elif isinstance(error, RuntimeError):
        logger.error(f"Runtime error during {context}: {error}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{context.capitalize()} failed: {str(error)}")
    else:
        logger.error(f"Unexpected error during {context}: {error}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected internal server error occurred.")


def handle_metrics_error(error: Exception) -> None:
    """Handles exceptions that occur during the retrieval of JSON metrics.

    This function logs the error and raises a standardized 500 Internal
    Server Error to prevent clients from receiving cryptic error messages
    when the metrics endpoint fails.

    Args:
        error: The exception that was caught.

    Raises:
        HTTPException: A 500 Internal Server Error with a generic message.
    """
    logger.error(f"Error retrieving metrics: {error}", exc_info=True)
    raise HTTPException(status_code=500, detail="Failed to retrieve application metrics.")


def handle_model_info_error(error: Exception) -> None:
    """Handles exceptions that occur during the retrieval of model information.

    This function logs the error and raises a standardized 500 Internal
    Server Error if fetching model metadata fails, ensuring a consistent
    API response.

    Args:
        error: The exception that was caught.

    Raises:
        HTTPException: A 500 Internal Server Error with a generic message.
    """
    logger.error(f"Error retrieving model info: {error}", exc_info=True)
    raise HTTPException(status_code=500, detail="Failed to retrieve model information.")


def handle_prometheus_metrics_error(error: Exception) -> None:
    """Handles exceptions during the retrieval of Prometheus metrics.

    This function logs the error and raises a standardized 500 Internal
    Server Error, which is particularly important for monitoring endpoints
    to ensure they fail gracefully.

    Args:
        error: The exception that was caught.

    Raises:
        HTTPException: A 500 Internal Server Error with a generic message.
    """
    logger.error(f"Error retrieving Prometheus metrics: {error}", exc_info=True)
    raise HTTPException(status_code=500, detail="Failed to retrieve Prometheus metrics.")
