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


class BatchSizeExceededError(ValidationError):
    """Raised when batch size exceeds maximum allowed limit."""

    def __init__(self, batch_size: int, max_batch_size: int, context: Optional[Any] = None):
        """Initializes the BatchSizeExceededError.

        Args:
            batch_size: The size of the provided batch.
            max_batch_size: The maximum allowed batch size.
            context: Optional additional context about the error.
        """
        message = f"Batch size of {batch_size} exceeds the maximum of {max_batch_size}."
        super().__init__(message, code="BATCH_SIZE_EXCEEDED", context=context)


class EmptyBatchError(ValidationError):
    """Raised when a batch processing request contains no items."""

    def __init__(self, context: Optional[Any] = None):
        """Initializes the EmptyBatchError.

        Args:
            context: Optional additional context about the error.
        """
        message = "Batch processing request cannot be empty."
        super().__init__(message, code="EMPTY_BATCH", context=context)


# --- Configuration exceptions ---


class ConfigurationError(ValidationError):
    """Base class for all configuration-related errors.

    This exception should be used when there are issues with application
    configuration, whether from environment variables, config files, or
    runtime validation of settings.
    """

    status_code = 500


class SecurityConfigError(ConfigurationError):
    """Raised when security configuration is invalid or missing."""

    def __init__(self, message: str, context: Optional[Any] = None):
        """Initializes the SecurityConfigError.

        Args:
            message: Description of the security configuration issue.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="SECURITY_CONFIG_ERROR", context=context)


class ModelConfigError(ConfigurationError):
    """Raised when model configuration is invalid."""

    def __init__(self, message: str, context: Optional[Any] = None):
        """Initializes the ModelConfigError.

        Args:
            message: Description of the model configuration issue.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="MODEL_CONFIG_ERROR", context=context)


class SettingsValidationError(ConfigurationError):
    """Raised when application settings validation fails."""

    def __init__(self, message: str, context: Optional[Any] = None):
        """Initializes the SettingsValidationError.

        Args:
            message: Description of the settings validation issue.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="SETTINGS_VALIDATION_ERROR", context=context)


# --- Secrets management exceptions ---


class SecretsError(ServiceError):
    """Base class for secrets management errors.

    This exception covers issues related to secrets storage and retrieval,
    including Vault, Kubernetes secrets, and environment variables.
    """

    status_code = 500


class VaultAuthenticationError(AuthenticationError):
    """Raised when authentication with HashiCorp Vault fails."""

    def __init__(self, message: str = "Failed to authenticate with Vault", context: Optional[Any] = None):
        """Initializes the VaultAuthenticationError.

        Args:
            message: Description of the Vault authentication failure.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="VAULT_AUTH_FAILED", context=context)


class KubernetesAuthenticationError(AuthenticationError):
    """Raised when Kubernetes authentication fails."""

    def __init__(self, message: str = "Kubernetes authentication failed", context: Optional[Any] = None):
        """Initializes the KubernetesAuthenticationError.

        Args:
            message: Description of the Kubernetes authentication failure.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="K8S_AUTH_FAILED", context=context)


class InvalidSecretsConfigError(ValidationError):
    """Raised when secrets configuration is invalid."""

    def __init__(self, message: str, context: Optional[Any] = None):
        """Initializes the InvalidSecretsConfigError.

        Args:
            message: Description of the invalid secrets configuration.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="INVALID_SECRETS_CONFIG", context=context)


# --- Extended model exceptions ---


class ModelLoadingError(ModelError):
    """Raised when a model fails to load from storage.

    This can occur due to missing files, corrupted model artifacts,
    or incompatible model formats.
    """

    status_code = 500

    def __init__(self, message: str, model_name: Optional[str] = None, context: Optional[Any] = None):
        """Initializes the ModelLoadingError.

        Args:
            message: Description of the model loading failure.
            model_name: The name of the model that failed to load.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="MODEL_LOADING_FAILED", context=context)


class ModelInitializationError(InternalError):
    """Raised when model initialization fails.

    This occurs when the model backend cannot be properly initialized,
    which might be due to missing dependencies, incompatible configurations,
    or resource constraints.
    """

    def __init__(self, message: str, backend: Optional[str] = None, context: Optional[Any] = None):
        """Initializes the ModelInitializationError.

        Args:
            message: Description of the initialization failure.
            backend: The model backend that failed to initialize (e.g., 'pytorch', 'onnx').
            context: Optional additional context about the error.
        """
        super().__init__(message, code="MODEL_INIT_FAILED", context=context)


class ModelCachingError(InternalError):
    """Raised when model caching operations fail.

    This covers failures in saving, loading, or managing cached model artifacts.
    """

    def __init__(self, message: str, context: Optional[Any] = None):
        """Initializes the ModelCachingError.

        Args:
            message: Description of the caching failure.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="MODEL_CACHING_FAILED", context=context)


class ModelMetadataNotFoundError(NotFoundError):
    """Raised when model metadata is not found in cache."""

    def __init__(self, model_identifier: str, context: Optional[Any] = None):
        """Initializes the ModelMetadataNotFoundError.

        Args:
            model_identifier: The identifier of the model whose metadata was not found.
            context: Optional additional context about the error.
        """
        message = f"Model metadata not found for: {model_identifier}"
        super().__init__(message, code="MODEL_METADATA_NOT_FOUND", context=context)


class InvalidModelPathError(ValidationError):
    """Raised when a model path is invalid or does not exist."""

    def __init__(self, path: str, context: Optional[Any] = None):
        """Initializes the InvalidModelPathError.

        Args:
            path: The invalid model path.
            context: Optional additional context about the error.
        """
        message = f"Model path is invalid or does not exist: {path}"
        super().__init__(message, code="INVALID_MODEL_PATH", context=context)


class ModelExportError(InternalError):
    """Raised when model export operations fail.

    This typically occurs when converting models to different formats
    (e.g., PyTorch to ONNX).
    """

    def __init__(self, message: str, source_format: Optional[str] = None, target_format: Optional[str] = None, context: Optional[Any] = None):
        """Initializes the ModelExportError.

        Args:
            message: Description of the export failure.
            source_format: The source model format.
            target_format: The target model format.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="MODEL_EXPORT_FAILED", context=context)


class UnsupportedBackendError(ValidationError):
    """Raised when a requested ML backend is not supported."""

    def __init__(self, backend: str, supported_backends: list[str], context: Optional[Any] = None):
        """Initializes the UnsupportedBackendError.

        Args:
            backend: The requested backend that is not supported.
            supported_backends: List of supported backends.
            context: Optional additional context about the error.
        """
        message = f"Backend '{backend}' is not supported. Supported backends: {', '.join(supported_backends)}"
        super().__init__(message, code="UNSUPPORTED_BACKEND", context=context)


# --- Feature engineering exceptions ---


class FeatureMismatchError(ValidationError):
    """Raised when input features don't match expected configuration.

    This typically occurs when the number or type of features provided
    doesn't match what the model or scaler expects.
    """

    def __init__(self, message: str, expected: Optional[int] = None, received: Optional[int] = None, context: Optional[Any] = None):
        """Initializes the FeatureMismatchError.

        Args:
            message: Description of the feature mismatch.
            expected: Expected number of features.
            received: Received number of features.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="FEATURE_MISMATCH", context=context)


class UnfittedScalerError(ValidationError):
    """Raised when attempting to use an unfitted scaler.

    This occurs when trying to transform data with a scaler that
    hasn't been fitted on training data yet.
    """

    def __init__(self, context: Optional[Any] = None):
        """Initializes the UnfittedScalerError.

        Args:
            context: Optional additional context about the error.
        """
        message = "Cannot transform data with an unfitted scaler. Call fit() first."
        super().__init__(message, code="UNFITTED_SCALER", context=context)


class ScalerStatePersistenceError(InternalError):
    """Raised when scaler state persistence operations fail."""

    def __init__(self, message: str, context: Optional[Any] = None):
        """Initializes the ScalerStatePersistenceError.

        Args:
            message: Description of the persistence failure.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="SCALER_PERSISTENCE_FAILED", context=context)


class InvalidScalerStateError(ValidationError):
    """Raised when a scaler state file is corrupted or invalid."""

    def __init__(self, message: str, context: Optional[Any] = None):
        """Initializes the InvalidScalerStateError.

        Args:
            message: Description of the invalid state.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="INVALID_SCALER_STATE", context=context)


# --- Service and async processing exceptions ---


class AsyncContextError(InternalError):
    """Raised when there are issues with async context or event loop."""

    def __init__(self, message: str, context: Optional[Any] = None):
        """Initializes the AsyncContextError.

        Args:
            message: Description of the async context issue.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="ASYNC_CONTEXT_ERROR", context=context)


class QueueCapacityExceededError(ServiceUnavailableError):
    """Raised when a service queue is at capacity.

    This indicates that the service is under heavy load and cannot
    accept additional requests at this time.
    """

    def __init__(self, queue_name: str = "processing", current_size: Optional[int] = None, max_size: Optional[int] = None, context: Optional[Any] = None):
        """Initializes the QueueCapacityExceededError.

        Args:
            queue_name: Name of the queue that is full.
            current_size: Current size of the queue.
            max_size: Maximum capacity of the queue.
            context: Optional additional context about the error.
        """
        message = f"Queue '{queue_name}' is at capacity"
        if current_size is not None and max_size is not None:
            message += f" ({current_size}/{max_size})"
        super().__init__(message, code="QUEUE_CAPACITY_EXCEEDED", context=context)


class ServiceNotStartedError(InternalError):
    """Raised when attempting to use a service that hasn't been started."""

    def __init__(self, service_name: str, context: Optional[Any] = None):
        """Initializes the ServiceNotStartedError.

        Args:
            service_name: Name of the service that hasn't been started.
            context: Optional additional context about the error.
        """
        message = f"Service '{service_name}' has not been started. Call start() first."
        super().__init__(message, code="SERVICE_NOT_STARTED", context=context)


class CircuitBreakerOpenError(ServiceUnavailableError):
    """Raised when circuit breaker is open and blocking requests.

    The circuit breaker pattern is used to prevent cascading failures
    by temporarily blocking requests to a failing service.
    """

    def __init__(self, service_name: str, retry_after: Optional[int] = None, context: Optional[Any] = None):
        """Initializes the CircuitBreakerOpenError.

        Args:
            service_name: Name of the service with open circuit breaker.
            retry_after: Suggested time in seconds to wait before retrying.
            context: Optional additional context about the error.
        """
        message = f"Circuit breaker is open for service '{service_name}'"
        if retry_after:
            message += f". Retry after {retry_after} seconds."
        super().__init__(message, code="CIRCUIT_BREAKER_OPEN", context=context)


# --- Health check and monitoring exceptions ---


class HealthCheckError(InternalError):
    """Raised when health check operations fail."""

    def __init__(self, component: str, message: str, context: Optional[Any] = None):
        """Initializes the HealthCheckError.

        Args:
            component: The component that failed the health check.
            message: Description of the health check failure.
            context: Optional additional context about the error.
        """
        full_message = f"Health check failed for {component}: {message}"
        super().__init__(full_message, code="HEALTH_CHECK_FAILED", context=context)


class TracingError(InternalError):
    """Raised when distributed tracing operations fail."""

    def __init__(self, message: str, context: Optional[Any] = None):
        """Initializes the TracingError.

        Args:
            message: Description of the tracing failure.
            context: Optional additional context about the error.
        """
        super().__init__(message, code="TRACING_ERROR", context=context)
