"""
Standardized error codes for the MLOps sentiment analysis service.

This module establishes a centralized and consistent error handling framework
for the API. It defines a set of standardized error codes, human-readable
messages, and utility functions for creating and raising structured error
responses, ensuring that API clients receive clear and predictable error information.
"""

from enum import Enum
from typing import Any, Dict, Optional

from fastapi import HTTPException


class ErrorCode(str, Enum):
    """Defines standardized error codes for the application.

    This enumeration centralizes all possible error codes, making them easy to
    manage, reference, and maintain. The codes are categorized by their nature,
    such as input validation, model-related issues, security, and general
    system errors, which helps in diagnosing problems more efficiently.

    Error Code Ranges:
    - 1000-1099: Input validation errors
    - 2000-2099: Model errors
    - 3000-3099: Security and authentication errors
    - 4000-4099: System and service errors
    - 5000-5099: Configuration errors
    - 6000-6099: Feature processing errors
    - 7000-7099: Batch and async processing errors
    """

    # Input validation errors (1000-1099)
    INVALID_INPUT_TEXT = "E1001"
    TEXT_TOO_LONG = "E1002"
    TEXT_EMPTY = "E1003"
    TEXT_INVALID_CHARACTERS = "E1004"
    BATCH_SIZE_EXCEEDED = "E1005"
    EMPTY_BATCH = "E1006"

    # Model errors (2000-2099)
    MODEL_NOT_LOADED = "E2001"
    MODEL_INFERENCE_FAILED = "E2002"
    MODEL_TIMEOUT = "E2003"
    MODEL_LOADING_FAILED = "E2004"
    MODEL_INIT_FAILED = "E2005"
    MODEL_CACHING_FAILED = "E2006"
    MODEL_METADATA_NOT_FOUND = "E2007"
    INVALID_MODEL_PATH = "E2008"
    MODEL_EXPORT_FAILED = "E2009"
    UNSUPPORTED_BACKEND = "E2010"

    # Security and authentication errors (3000-3099)
    INVALID_MODEL_NAME = "E3001"
    UNAUTHORIZED_ACCESS = "E3002"
    VAULT_AUTH_FAILED = "E3003"
    K8S_AUTH_FAILED = "E3004"
    INVALID_SECRETS_CONFIG = "E3005"

    # System and service errors (4000-4099)
    INTERNAL_SERVER_ERROR = "E4001"
    SERVICE_UNAVAILABLE = "E4002"
    RATE_LIMIT_EXCEEDED = "E4003"
    ASYNC_CONTEXT_ERROR = "E4004"
    QUEUE_CAPACITY_EXCEEDED = "E4005"
    SERVICE_NOT_STARTED = "E4006"
    CIRCUIT_BREAKER_OPEN = "E4007"
    HEALTH_CHECK_FAILED = "E4008"
    TRACING_ERROR = "E4009"

    # Configuration errors (5000-5099)
    SECURITY_CONFIG_ERROR = "E5001"
    MODEL_CONFIG_ERROR = "E5002"
    SETTINGS_VALIDATION_ERROR = "E5003"

    # Feature processing errors (6000-6099)
    FEATURE_MISMATCH = "E6001"
    UNFITTED_SCALER = "E6002"
    SCALER_PERSISTENCE_FAILED = "E6003"
    INVALID_SCALER_STATE = "E6004"

    # Batch and async processing errors (7000-7099)
    BATCH_JOB_NOT_FOUND = "E7001"
    BATCH_JOB_NOT_CANCELLABLE = "E7002"
    BATCH_JOB_SUBMISSION_FAILED = "E7003"
    BATCH_RESULTS_NOT_READY = "E7004"
    BATCH_QUEUE_STATUS_ERROR = "E7005"
    BATCH_METRICS_ERROR = "E7006"

    # Monitoring and observability errors (8000-8099)
    MONITORING_FEATURE_DISABLED = "E8001"
    MONITORING_SERVICE_NOT_INITIALIZED = "E8002"
    MONITORING_DATA_INSUFFICIENT = "E8003"
    DRIFT_DETECTION_FAILED = "E8004"
    METRICS_COLLECTION_FAILED = "E8005"
    KPI_CALCULATION_FAILED = "E8006"
    MODEL_REGISTRY_ERROR = "E8007"
    EXPLAINABILITY_ERROR = "E8008"


class ErrorMessages:
    """Provides human-readable messages for each defined error code.

    This class maps each `ErrorCode` to a descriptive, user-friendly message.
    This separation of codes and messages facilitates easier management and
    potential internationalization of error responses in the future.
    """

    MESSAGES = {
        # Input validation errors
        ErrorCode.INVALID_INPUT_TEXT: "Invalid input text provided. The text may be malformed or of an unsupported type.",
        ErrorCode.TEXT_TOO_LONG: "The provided input text exceeds the maximum allowed length limit.",
        ErrorCode.TEXT_EMPTY: "Input text cannot be empty or consist only of whitespace.",
        ErrorCode.TEXT_INVALID_CHARACTERS: "The input text contains invalid or unsupported characters.",
        ErrorCode.BATCH_SIZE_EXCEEDED: "The batch size exceeds the maximum allowed limit.",
        ErrorCode.EMPTY_BATCH: "Batch processing request cannot be empty.",
        # Model errors
        ErrorCode.MODEL_NOT_LOADED: "The sentiment analysis model is currently not loaded or unavailable.",
        ErrorCode.MODEL_INFERENCE_FAILED: "An unexpected error occurred during the model inference process.",
        ErrorCode.MODEL_TIMEOUT: "The model inference process timed out before a result could be returned.",
        ErrorCode.MODEL_LOADING_FAILED: "Failed to load the model from storage. The model file may be corrupted or missing.",
        ErrorCode.MODEL_INIT_FAILED: "Model initialization failed. Check model configuration and dependencies.",
        ErrorCode.MODEL_CACHING_FAILED: "Failed to cache the model. There may be insufficient storage or permissions issues.",
        ErrorCode.MODEL_METADATA_NOT_FOUND: "Model metadata not found in cache. The model may need to be reloaded.",
        ErrorCode.INVALID_MODEL_PATH: "The specified model path is invalid or does not exist.",
        ErrorCode.MODEL_EXPORT_FAILED: "Failed to export the model to the requested format.",
        ErrorCode.UNSUPPORTED_BACKEND: "The requested ML backend is not supported by this service.",
        # Security and authentication errors
        ErrorCode.INVALID_MODEL_NAME: "The requested model name is invalid, not found, or not permitted.",
        ErrorCode.UNAUTHORIZED_ACCESS: "Unauthorized access. A valid authentication token is required.",
        ErrorCode.VAULT_AUTH_FAILED: "Failed to authenticate with HashiCorp Vault. Check credentials and configuration.",
        ErrorCode.K8S_AUTH_FAILED: "Kubernetes authentication failed. Check service account and RBAC permissions.",
        ErrorCode.INVALID_SECRETS_CONFIG: "Secrets configuration is invalid or missing required parameters.",
        # System and service errors
        ErrorCode.INTERNAL_SERVER_ERROR: "An unexpected internal server error occurred.",
        ErrorCode.SERVICE_UNAVAILABLE: "The service is temporarily unavailable. Please try again later.",
        ErrorCode.RATE_LIMIT_EXCEEDED: "You have exceeded the API rate limit. Please wait before making new requests.",
        ErrorCode.ASYNC_CONTEXT_ERROR: "Invalid async context or event loop error. This is an internal service issue.",
        ErrorCode.QUEUE_CAPACITY_EXCEEDED: "The processing queue is at capacity. The service is under heavy load.",
        ErrorCode.SERVICE_NOT_STARTED: "The requested service has not been started or initialized.",
        ErrorCode.CIRCUIT_BREAKER_OPEN: "Circuit breaker is open. The service is temporarily unavailable due to detected failures.",
        ErrorCode.HEALTH_CHECK_FAILED: "Health check failed for one or more service components.",
        ErrorCode.TRACING_ERROR: "Distributed tracing operation failed. This should not affect service functionality.",
        # Configuration errors
        ErrorCode.SECURITY_CONFIG_ERROR: "Security configuration is invalid or missing required settings.",
        ErrorCode.MODEL_CONFIG_ERROR: "Model configuration is invalid or contains unsupported parameters.",
        ErrorCode.SETTINGS_VALIDATION_ERROR: "Application settings validation failed. Check environment variables and config files.",
        # Feature processing errors
        ErrorCode.FEATURE_MISMATCH: "Input features don't match the expected configuration or dimensions.",
        ErrorCode.UNFITTED_SCALER: "Cannot use an unfitted scaler. The scaler must be fitted on training data first.",
        ErrorCode.SCALER_PERSISTENCE_FAILED: "Failed to persist scaler state to storage.",
        ErrorCode.INVALID_SCALER_STATE: "Scaler state file is corrupted or invalid. Cannot restore scaler.",
        # Batch and async processing errors
        ErrorCode.BATCH_JOB_NOT_FOUND: "The requested batch job was not found. It may have expired or been deleted.",
        ErrorCode.BATCH_JOB_NOT_CANCELLABLE: "The batch job cannot be cancelled in its current state. Only pending or processing jobs can be cancelled.",
        ErrorCode.BATCH_JOB_SUBMISSION_FAILED: "Failed to submit the batch job for processing. The service may be under heavy load.",
        ErrorCode.BATCH_RESULTS_NOT_READY: "The batch job results are not yet available. The job may still be processing or may have failed.",
        ErrorCode.BATCH_QUEUE_STATUS_ERROR: "Failed to retrieve the current batch queue status.",
        ErrorCode.BATCH_METRICS_ERROR: "Failed to retrieve batch processing metrics.",
        # Monitoring and observability errors
        ErrorCode.MONITORING_FEATURE_DISABLED: "The requested monitoring feature is not enabled in the current configuration.",
        ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED: "The monitoring service has not been initialized or is not available.",
        ErrorCode.MONITORING_DATA_INSUFFICIENT: "Insufficient data available for the requested monitoring operation.",
        ErrorCode.DRIFT_DETECTION_FAILED: "Failed to perform drift detection analysis.",
        ErrorCode.METRICS_COLLECTION_FAILED: "Failed to collect the requested metrics.",
        ErrorCode.KPI_CALCULATION_FAILED: "Failed to calculate key performance indicators.",
        ErrorCode.MODEL_REGISTRY_ERROR: "Failed to access or update the model registry.",
        ErrorCode.EXPLAINABILITY_ERROR: "Failed to generate model explainability insights.",
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
    detail: Optional[str] = None,
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
    response: Dict[str, Any] = {
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
    detail: Optional[str] = None,
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
