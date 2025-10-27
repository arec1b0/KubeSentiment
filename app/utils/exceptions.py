"""
Custom exception hierarchy for the MLOps sentiment analysis service.

This module defines a set of domain-specific exceptions that are used
throughout the application for consistent and structured error handling. These
exceptions map directly to HTTP error responses, allowing for clear and
predictable error feedback to API clients.
"""

from typing import Any, Optional


class ServiceError(Exception):
    """The base exception class for all custom exceptions in this service.

    This class provides a common structure for all application-specific
    exceptions, including a default HTTP status code, a machine-readable
    error code, and an optional context dictionary for additional details.
    Subclassing from this base ensures that all custom exceptions can be
    caught and handled uniformly.

    Attributes:
        status_code: The default HTTP status code for this type of error.
        code: A string-based error code for programmatic identification.
        context: Optional additional information about the error.
    """

    status_code: int = 500

    def __init__(self, message: str, code: str = "E0000", context: Optional[Any] = None):
        """Initializes the ServiceError.

        Args:
            message: A human-readable message describing the error.
            code: A unique, machine-readable code for the error.
            context: An optional dictionary for providing extra context.
        """
        super().__init__(message)
        self.code = code
        self.context = context


class ValidationError(ServiceError):
    """Raised when input data fails validation checks.

    This exception should be used for all errors related to invalid or
    malformed user input, such as incorrect data types or values that do not
    meet predefined constraints. It corresponds to a 400 Bad Request HTTP status.
    """

    status_code = 400


class AuthenticationError(ServiceError):
    """Raised for authentication or authorization failures.

    This exception is used when a user is not authenticated or does not have
    the necessary permissions to perform an action. It corresponds to a 401
    Unauthorized or 403 Forbidden HTTP status, depending on the context.
    """

    status_code = 401


class NotFoundError(ServiceError):
    """Raised when a requested resource is not found.

    This is used in situations where an entity, such as a specific model or
    data record, does not exist in the system. It corresponds to a 404 Not
    Found HTTP status.
    """

    status_code = 404


class ConflictError(ServiceError):
    """Raised when an operation cannot be completed due to a conflict.

    This can occur, for example, when trying to create a resource that
    already exists. It corresponds to a 409 Conflict HTTP status.
    """

    status_code = 409


class InternalError(ServiceError):
    """Raised for general, unexpected internal server errors.

    This exception is a catch-all for internal issues that are not covered
    by more specific error types. It corresponds to a 500 Internal Server
    Error HTTP status.
    """

    status_code = 500


class ServiceUnavailableError(ServiceError):
    """Raised when the service or one of its dependencies is unavailable.

    This might be due to a dependency being down, the service being in a
    degraded state, or maintenance. It corresponds to a 503 Service
    Unavailable HTTP status.
    """

    status_code = 503


# --- ML-specific exceptions ---


class ModelError(ServiceError):
    """A base class for all exceptions related to ML models."""

    status_code = 500


class ModelNotLoadedError(ModelError):
    """Raised when an attempt is made to use a model that is not loaded.

    This exception indicates that the model is not ready to serve predictions,
    which might be due to a failure during its initialization or loading process.
    """

    status_code = 503

    def __init__(self, model_name: Optional[str] = None, context: Optional[Any] = None):
        """Initializes the ModelNotLoadedError.

        Args:
            model_name: The name of the model that was not loaded.
            context: Optional additional context about the error.
        """
        message = (
            f"Model '{model_name}' is not loaded or unavailable."
            if model_name
            else "Model is not loaded."
        )
        super().__init__(message, code="MODEL_NOT_LOADED", context=context)


class ModelInferenceError(ModelError):
    """Raised when a non-recoverable error occurs during model inference."""

    status_code = 500

    def __init__(
        self, message: str, model_name: Optional[str] = None, context: Optional[Any] = None
    ):
        """Initializes the ModelInferenceError.

        Args:
            message: A human-readable message describing the inference error.
            model_name: The name of the model where the error occurred.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="MODEL_INFERENCE_FAILED", context=context)


class InvalidModelError(ValidationError):
    """Raised when an invalid or unauthorized model name is requested."""

    def __init__(self, model_name: str, allowed_models: list[str], context: Optional[Any] = None):
        """Initializes the InvalidModelError.

        Args:
            model_name: The invalid model name that was requested.
            allowed_models: The list of valid model names.
            context: Optional additional context about the error.
        """
        message = (
            f"Model '{model_name}' is not allowed. Allowed models are: {', '.join(allowed_models)}"
        )
        super().__init__(message, code="INVALID_MODEL_NAME", context=context)


# --- Input validation exceptions ---


class TextValidationError(ValidationError):
    """A base class for errors related to text input validation."""

    def __init__(
        self, message: str, text_length: Optional[int] = None, context: Optional[Any] = None
    ):
        """Initializes the TextValidationError.

        Args:
            message: A human-readable message describing the validation error.
            text_length: The length of the text that caused the error.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="TEXT_VALIDATION_ERROR", context=context)


class TextTooLongError(TextValidationError):
    """Raised when the input text exceeds the maximum allowed length."""

    def __init__(self, text_length: int, max_length: int, context: Optional[Any] = None):
        """Initializes the TextTooLongError.

        Args:
            text_length: The length of the provided input text.
            max_length: The maximum allowed length for the text.
            context: Optional additional context about the error.
        """
        message = f"Text length of {text_length} characters exceeds the maximum of {max_length}."
        super().__init__(message, text_length=text_length, context=context)
        self.code = "TEXT_TOO_LONG"


class TextEmptyError(TextValidationError):
    """Raised when the input text is empty or contains only whitespace."""

    def __init__(self, context: Optional[Any] = None):
        """Initializes the TextEmptyError.

        Args:
            context: Optional additional context about the error.
        """
        message = "The text field is required and cannot be empty or contain only whitespace."
        super().__init__(message, context=context)
        self.code = "TEXT_EMPTY"
