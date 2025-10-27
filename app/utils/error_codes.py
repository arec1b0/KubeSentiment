"""
Standardized error codes for the MLOps sentiment analysis service.

This module establishes a centralized and consistent error handling framework
for the API. It defines a set of standardized error codes, human-readable
messages, and utility functions for creating and raising structured error
responses, ensuring that API clients receive clear and predictable error information.
"""

from enum import Enum
from typing import Any, Dict

from fastapi import HTTPException


class ErrorCode(str, Enum):
    """Defines standardized error codes for the application.

    This enumeration centralizes all possible error codes, making them easy to
    manage, reference, and maintain. The codes are categorized by their nature,
    such as input validation, model-related issues, security, and general
    system errors, which helps in diagnosing problems more efficiently.
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
    """Provides human-readable messages for each defined error code.

    This class maps each `ErrorCode` to a descriptive, user-friendly message.
    This separation of codes and messages facilitates easier management and
    potential internationalization of error responses in the future.
    """

    MESSAGES = {
        ErrorCode.INVALID_INPUT_TEXT: "Invalid input text provided. The text may be malformed or of an unsupported type.",
        ErrorCode.TEXT_TOO_LONG: "The provided input text exceeds the maximum allowed length limit.",
        ErrorCode.TEXT_EMPTY: "Input text cannot be empty or consist only of whitespace.",
        ErrorCode.TEXT_INVALID_CHARACTERS: "The input text contains invalid or unsupported characters.",
        ErrorCode.MODEL_NOT_LOADED: "The sentiment analysis model is currently not loaded or unavailable.",
        ErrorCode.MODEL_INFERENCE_FAILED: "An unexpected error occurred during the model inference process.",
        ErrorCode.MODEL_TIMEOUT: "The model inference process timed out before a result could be returned.",
        ErrorCode.INVALID_MODEL_NAME: "The requested model name is invalid, not found, or not permitted.",
        ErrorCode.UNAUTHORIZED_ACCESS: "Unauthorized access. A valid authentication token is required.",
        ErrorCode.INTERNAL_SERVER_ERROR: "An unexpected internal server error occurred.",
        ErrorCode.SERVICE_UNAVAILABLE: "The service is temporarily unavailable. Please try again later.",
        ErrorCode.RATE_LIMIT_EXCEEDED: "You have exceeded the API rate limit. Please wait before making new requests.",
    }

    @classmethod
    def get_message(cls, error_code: ErrorCode) -> str:
        """Retrieves the message for a given error code.

        If the error code is not found in the map, a default message is returned
        to ensure that a response can always be generated.

        Args:
            error_code: The `ErrorCode` for which to retrieve the message.

        Returns:
            The corresponding error message as a string.
        """
        return cls.MESSAGES.get(error_code, "An unknown error occurred.")


def create_error_response(
    error_code: ErrorCode,
    detail: str = None,
    status_code: int = 400,
    **additional_context,
) -> Dict[str, Any]:
    """Constructs a standardized dictionary for an error response.

    This function creates a consistent structure for all API error responses,
    including the error code, a standard message, a detailed message, and any
    additional context that might be useful for debugging.

    Args:
        error_code: The `ErrorCode` enum member for this error.
        detail: An optional, more specific, human-readable message about the
                error. If not provided, the default message is used.
        status_code: The HTTP status code for the response.
        **additional_context: Any extra key-value pairs to include in the
                               'context' field of the response.

    Returns:
        A dictionary representing the standardized error response, suitable for
        JSON serialization.
    """
    error_message = ErrorMessages.get_message(error_code)
    response = {
        "error_code": error_code.value,
        "error_message": error_message,
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

    This utility function is a convenient wrapper that simplifies raising
    exceptions that FastAPI can automatically handle and convert into a
    JSON error response. It is the preferred way to generate errors from
    within the application's business logic.

    Args:
        error_code: The `ErrorCode` enum member for this error.
        detail: An optional, more specific, human-readable message about the
                error.
        status_code: The HTTP status code to be used for the exception.
        **additional_context: Any extra information to include in the error
                               response.

    Raises:
        HTTPException: An exception that FastAPI will catch and convert into a
                       standardized JSON error response.
    """
    error_response = create_error_response(error_code, detail, status_code, **additional_context)
    raise HTTPException(status_code=status_code, detail=error_response)
