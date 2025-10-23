"""
Standardized error codes for the MLOps sentiment analysis service.

This module defines error codes, messages, and response structures
for consistent error handling across the API.
"""

from enum import Enum
from typing import Any, Dict

from fastapi import HTTPException


class ErrorCode(str, Enum):
    """Defines standardized error codes for the application.

    This enumeration centralizes all error codes, making them easy to manage
    and reference. The codes are categorized by their nature (e.g., input
    validation, model errors).
    """

    # Input validation errors (1000-1099)
    INVALID_INPUT_TEXT = "E1001"
    TEXT_TOO_LONG = "E1002"
    TEXT_EMPTY = "E1003"
    TEXT_INVALID_CHARACTERS = "E1004"

    # Model errors (2000-2099)
    MODEL_NOT_LOADED = "E2001"
    MODEL_INFERENCE_FAILED = "E2002"
    MODEL_TIMEOUT = "E2003"

    # Security errors (3000-3099)
    INVALID_MODEL_NAME = "E3001"
    UNAUTHORIZED_ACCESS = "E3002"

    # System errors (4000-4099)
    INTERNAL_SERVER_ERROR = "E4001"
    SERVICE_UNAVAILABLE = "E4002"
    RATE_LIMIT_EXCEEDED = "E4003"


class ErrorMessages:
    """Provides human-readable messages for each error code.

    This class maps each `ErrorCode` to a descriptive message, which can be
    used in API error responses.
    """

    MESSAGES = {
        ErrorCode.INVALID_INPUT_TEXT: "Invalid input text provided",
        ErrorCode.TEXT_TOO_LONG: "Input text exceeds maximum length limit",
        ErrorCode.TEXT_EMPTY: "Input text cannot be empty or whitespace only",
        ErrorCode.TEXT_INVALID_CHARACTERS: "Input text contains invalid characters",
        ErrorCode.MODEL_NOT_LOADED: "Sentiment analysis model is not loaded",
        ErrorCode.MODEL_INFERENCE_FAILED: "Model inference failed",
        ErrorCode.MODEL_TIMEOUT: "Model inference timed out",
        ErrorCode.INVALID_MODEL_NAME: "Requested model name is not allowed",
        ErrorCode.UNAUTHORIZED_ACCESS: "Unauthorized access to API endpoint",
        ErrorCode.INTERNAL_SERVER_ERROR: "Internal server error occurred",
        ErrorCode.SERVICE_UNAVAILABLE: "Service is temporarily unavailable",
        ErrorCode.RATE_LIMIT_EXCEEDED: "API rate limit exceeded",
    }

    @classmethod
    def get_message(cls, error_code: ErrorCode) -> str:
        """Retrieves the message for a given error code.

        Args:
            error_code: The `ErrorCode` for which to get the message.

        Returns:
            The corresponding error message, or a default message if the
            code is not found.
        """
        return cls.MESSAGES.get(error_code, "Unknown error occurred")


def create_error_response(
    error_code: ErrorCode,
    detail: str = None,
    status_code: int = 400,
    **additional_context,
) -> Dict[str, Any]:
    """Constructs a standardized error response dictionary.

    This function creates a consistent structure for all API error responses,
    including the error code, a message, and any additional context.

    Args:
        error_code: The `ErrorCode` for this error.
        detail: A more specific, human-readable message about the error.
        status_code: The HTTP status code for the response.
        **additional_context: Any extra information to include in the
            'context' field of the response.

    Returns:
        A dictionary representing the standardized error response.
    """
    response = {
        "error_code": error_code.value,
        "error_message": ErrorMessages.get_message(error_code),
        "status_code": status_code,
    }

    if detail:
        response["detail"] = detail

    if additional_context:
        response["context"] = additional_context

    return response


def raise_validation_error(
    error_code: ErrorCode,
    detail: str = None,
    status_code: int = 400,
    **additional_context,
) -> None:
    """Creates a standardized error response and raises it as an `HTTPException`.

    This utility function is a convenient way to raise exceptions that will be
    automatically handled by FastAPI and converted into a JSON error response.

    Args:
        error_code: The `ErrorCode` for this error.
        detail: A more specific, human-readable message about the error.
        status_code: The HTTP status code for the exception.
        **additional_context: Any extra information to include in the
            error response.

    Raises:
        HTTPException: An exception that FastAPI will convert into a
            standardized JSON error response.
    """
    error_response = create_error_response(error_code, detail, status_code, **additional_context)
    raise HTTPException(status_code=status_code, detail=error_response)
