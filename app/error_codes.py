"""
Standardized error codes for the MLOps sentiment analysis service.

This module defines error codes, messages, and response structures
for consistent error handling across the API.
"""

from enum import Enum
from typing import Dict, Any
from fastapi import HTTPException


class ErrorCode(str, Enum):
    """Standardized error codes for the service."""

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
    """Error messages corresponding to error codes."""

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
        """Get the message for an error code."""
        return cls.MESSAGES.get(error_code, "Unknown error occurred")


def create_error_response(
    error_code: ErrorCode,
    detail: str = None,
    status_code: int = 400,
    **additional_context,
) -> Dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        error_code: The error code
        detail: Additional detail message
        status_code: HTTP status code
        **additional_context: Additional context data

    Returns:
        Dict[str, Any]: Standardized error response
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
    """
    Raise a validation error with standardized format.

    Args:
        error_code: The error code
        detail: Additional detail message
        status_code: HTTP status code
        **additional_context: Additional context data

    Raises:
        HTTPException: Formatted validation error
    """
    error_response = create_error_response(
        error_code, detail, status_code, **additional_context
    )
    raise HTTPException(status_code=status_code, detail=error_response)
