"""
Custom exception hierarchy for the MLOps sentiment analysis service.

Defines domain-specific exceptions that map to HTTP errors and
can be used across the codebase for consistent error handling.
"""

from typing import Any, Optional


class ServiceError(Exception):
    """Base class for all service errors."""

    status_code: int = 500

    def __init__(
        self, message: str, code: str = "E0000", context: Optional[Any] = None
    ):
        super().__init__(message)
        self.code = code
        self.context = context


class ValidationError(ServiceError):
    """Validation error for bad input data."""

    status_code = 400


class AuthenticationError(ServiceError):
    """Authentication/authorization failure."""

    status_code = 401


class NotFoundError(ServiceError):
    """Resource not found error."""

    status_code = 404


class ConflictError(ServiceError):
    """Conflict or duplicate resource error."""

    status_code = 409


class InternalError(ServiceError):
    """Internal server error."""

    status_code = 500


class ServiceUnavailableError(ServiceError):
    """Service temporarily unavailable."""

    status_code = 503


# ML-specific exceptions
class ModelError(ServiceError):
    """Base class for ML model-related errors."""

    status_code = 500


class ModelNotLoadedError(ModelError):
    """Model is not loaded or failed to initialize."""

    status_code = 503

    def __init__(self, model_name: Optional[str] = None, context: Optional[Any] = None):
        message = (
            f"Model '{model_name}' is not loaded"
            if model_name
            else "Model is not loaded"
        )
        super().__init__(message, code="MODEL_NOT_LOADED", context=context)


class ModelInferenceError(ModelError):
    """Model inference/prediction failed."""

    status_code = 500

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        context: Optional[Any] = None,
    ):
        super().__init__(message, code="MODEL_INFERENCE_FAILED", context=context)


class InvalidModelError(ValidationError):
    """Invalid or unauthorized model name."""

    def __init__(
        self, model_name: str, allowed_models: list[str], context: Optional[Any] = None
    ):
        message = f"Model '{model_name}' is not allowed. Allowed models: {', '.join(allowed_models)}"
        super().__init__(message, code="INVALID_MODEL_NAME", context=context)


# Input validation exceptions
class TextValidationError(ValidationError):
    """Text input validation error."""

    def __init__(
        self,
        message: str,
        text_length: Optional[int] = None,
        context: Optional[Any] = None,
    ):
        super().__init__(message, code="TEXT_VALIDATION_ERROR", context=context)


class TextTooLongError(TextValidationError):
    """Text input exceeds maximum length."""

    def __init__(
        self, text_length: int, max_length: int, context: Optional[Any] = None
    ):
        message = (
            f"Text length {text_length} exceeds maximum of {max_length} characters"
        )
        super().__init__(message, text_length=text_length, context=context)
        self.code = "TEXT_TOO_LONG"


class TextEmptyError(TextValidationError):
    """Text input is empty or only whitespace."""

    def __init__(self, context: Optional[Any] = None):
        message = "Text field is required and cannot be empty"
        super().__init__(message, context=context)
        self.code = "TEXT_EMPTY"
