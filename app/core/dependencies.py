"""
Dependency injection for the MLOps sentiment analysis service.

This module provides centralized dependency injection functions for FastAPI,
following the dependency inversion principle. It allows for a clean separation
of concerns and makes the application more modular, testable, and maintainable
by decoupling the API layer from the concrete implementations of services and
models.

All dependency injection functions now return interface types rather than
concrete implementations, enabling loose coupling and easier testing.
"""

from typing import Any, Callable, Optional, TypeVar

from fastapi import Depends, HTTPException, Query, Request

from app.core.config import Settings, get_settings
from app.core.logging import get_contextual_logger
from app.interfaces import IPredictionService, IDataWriter
from app.utils.error_codes import ErrorCode, raise_validation_error

T = TypeVar("T")


def get_model_backend(
    backend: Optional[str] = Query(None, description="Model backend to use (pytorch/onnx)"),
    settings: Settings = Depends(get_settings),
) -> str:
    """Determines the model backend based on query parameters and settings.

    This dependency function inspects the 'backend' query parameter. If it's
    provided and valid, it will be used. Otherwise, it falls back to the
    default backend, which is 'onnx' if an ONNX model path is configured, and
    'pytorch' otherwise. This allows for dynamic selection of the inference
    backend at request time.

    Args:
        backend: The model backend specified in the query parameter (optional).
        settings: The application's configuration settings, injected as a
            dependency.

    Returns:
        The name of the model backend to use, either 'onnx' or 'pytorch'.
    """
    if backend:
        return backend.lower()
    elif settings.model.onnx_model_path:
        return "onnx"
    else:
        return "pytorch"


def get_model_service(
    backend: str = Depends(get_model_backend),
):
    """Provides a model service instance based on the selected backend.

    This function acts as a factory for the model service. It uses the
    `get_model_backend` dependency to determine which backend to use and then
    creates and returns the appropriate model service instance (e.g., a
    PyTorch model or an ONNX model). This abstracts the model instantiation
    process from the API layer.

    Args:
        backend: The selected model backend, provided by the
            `get_model_backend` dependency.

    Returns:
        An instance of a class that implements the `ModelStrategy` protocol,
        corresponding to the selected backend.
    """
    # Import here to avoid circular imports at startup
    from app.models.factory import ModelFactory

    return ModelFactory.create_model(backend)


def get_prediction_service(
    model=Depends(get_model_service),
    settings: Settings = Depends(get_settings),
    feature_engineer=Depends(get_feature_engineer),
) -> IPredictionService:
    """Provides an instance of the prediction service.

    This dependency injects the appropriate model service, the application
    settings, and the feature engineering service into the `PredictionService`.
    This makes the fully configured service available to the API endpoints,
    encapsulating the business logic for making predictions.

    Args:
        model: The model service instance, provided by `get_model_service`.
        settings: The application's configuration settings, provided by
            `get_settings`.
        feature_engineer: The feature engineering service instance, provided by
            `get_feature_engineer`.

    Returns:
        An instance implementing the `IPredictionService` interface.
    """
    from app.services.prediction import PredictionService

    return PredictionService(model=model, settings=settings, feature_engineer=feature_engineer)


def get_feature_engineer():
    """Provides a singleton instance of the feature engineering service.

    This dependency ensures that the `FeatureEngineer` class, which may have a
    costly initialization process (e.g., downloading NLTK data), is created
    only once and reused across the application.

    Returns:
        The singleton instance of the `FeatureEngineer`.
    """
    from app.features.feature_engineering import get_feature_engineer as get_fe

    return get_fe()


def get_data_writer(settings: Settings = Depends(get_settings)) -> IDataWriter:
    """Provides a singleton instance of the data lake writer service.

    This dependency ensures that the `DataLakeWriter` class is created
    only once and reused across the application for streaming predictions
    to cloud storage.

    Args:
        settings: The application's configuration settings, injected as a
            dependency.

    Returns:
        The singleton instance implementing the `IDataWriter` interface.
    """
    from app.services.data_writer import get_data_writer as get_dw

    return get_dw(settings)


# ============================================================================
# Error Handling Utilities
# ============================================================================


def require_service(
    service: Optional[T],
    error_code: ErrorCode,
    detail: Optional[str] = None,
    **additional_context: Any,
) -> T:
    """Validates that a required service is available, raising a standardized error if not.

    This utility function consolidates the common pattern of checking if a service
    is available and raising an appropriate HTTPException if it is not. It ensures
    consistent error responses across all endpoints that require service availability.

    Args:
        service: The service instance to check. Can be None or any type.
        error_code: The ErrorCode to use if the service is not available.
        detail: Optional detailed error message. If not provided, uses the
            default message for the error_code.
        **additional_context: Additional context to include in the error response.

    Returns:
        The service instance if it is available (not None).

    Raises:
        HTTPException: With status code 503 if the service is not available.

    Example:
        >>> batch_service = require_service(
        ...     request.app.state.async_batch_service,
        ...     ErrorCode.SERVICE_NOT_STARTED,
        ...     detail="Async batch service is not available",
        ...     service_name="async_batch"
        ... )
    """
    if service is None:
        raise_validation_error(
            error_code=error_code,
            detail=detail,
            status_code=503,
            **additional_context,
        )
    return service


def handle_operation_error(
    error: Exception,
    error_code: ErrorCode,
    operation: str,
    logger_name: str,
    detail: Optional[str] = None,
    status_code: int = 500,
    **log_context: Any,
) -> None:
    """Handles an operation error by logging and raising a standardized exception.

    This utility function consolidates the common error handling pattern of:
    1. Logging the error with structured context
    2. Raising a standardized HTTPException with error codes

    It ensures that all errors are logged consistently and that API clients
    receive standardized error responses.

    Args:
        error: The exception that occurred.
        error_code: The ErrorCode to use in the error response.
        operation: A description of the operation that failed (for logging).
        logger_name: The name of the logger to use (typically __name__).
        detail: Optional detailed error message. If not provided, uses the
            exception message.
        status_code: HTTP status code for the error response. Defaults to 500.
        **log_context: Additional context to include in the log message.

    Raises:
        HTTPException: Always raises with the specified error_code and status_code.

    Example:
        >>> try:
        ...     result = await process_batch()
        ... except Exception as e:
        ...     handle_operation_error(
        ...         error=e,
        ...         error_code=ErrorCode.BATCH_JOB_SUBMISSION_FAILED,
        ...         operation="batch_submit",
        ...         logger_name=__name__,
        ...         job_id=job_id,
        ...     )
    """
    logger = get_contextual_logger(logger_name, operation=operation, **log_context)

    logger.error(
        f"Operation failed: {operation}",
        error=str(error),
        error_type=type(error).__name__,
        exc_info=True,
        **log_context,
    )

    error_detail = detail or str(error)
    raise_validation_error(
        error_code=error_code,
        detail=error_detail,
        status_code=status_code,
        operation=operation,
        error_type=type(error).__name__,
    )


def require_feature_enabled(
    enabled: bool,
    feature_name: str,
    error_code: ErrorCode = ErrorCode.MONITORING_FEATURE_DISABLED,
    detail: Optional[str] = None,
) -> None:
    """Validates that a feature is enabled, raising a standardized error if not.

    This utility function consolidates the common pattern of checking if a
    feature is enabled and raising an appropriate HTTPException if it is not.

    Args:
        enabled: Whether the feature is enabled.
        feature_name: The name of the feature being checked.
        error_code: The ErrorCode to use if the feature is disabled.
            Defaults to MONITORING_FEATURE_DISABLED.
        detail: Optional detailed error message. If not provided, generates
            a default message with the feature name.

    Raises:
        HTTPException: With status code 503 if the feature is disabled.

    Example:
        >>> require_feature_enabled(
        ...     enabled=settings.drift_detection_enabled,
        ...     feature_name="drift_detection",
        ...     error_code=ErrorCode.MONITORING_FEATURE_DISABLED,
        ... )
    """
    if not enabled:
        error_detail = detail or f"The {feature_name} feature is not enabled"
        raise_validation_error(
            error_code=error_code,
            detail=error_detail,
            status_code=503,
            feature_name=feature_name,
        )


def require_initialized(
    service: Optional[Any],
    service_name: str,
    error_code: ErrorCode = ErrorCode.MONITORING_SERVICE_NOT_INITIALIZED,
    detail: Optional[str] = None,
) -> Any:
    """Validates that a service is initialized, raising a standardized error if not.

    This utility function is similar to require_service but specifically for
    checking if a service has been properly initialized (not just available).

    Args:
        service: The service instance to check.
        service_name: The name of the service being checked.
        error_code: The ErrorCode to use if the service is not initialized.
            Defaults to MONITORING_SERVICE_NOT_INITIALIZED.
        detail: Optional detailed error message. If not provided, generates
            a default message with the service name.

    Returns:
        The service instance if it is initialized.

    Raises:
        HTTPException: With status code 503 if the service is not initialized.

    Example:
        >>> drift_detector = require_initialized(
        ...     app.state.drift_detector,
        ...     service_name="drift_detector",
        ... )
    """
    if service is None:
        error_detail = detail or f"The {service_name} service is not initialized"
        raise_validation_error(
            error_code=error_code,
            detail=error_detail,
            status_code=503,
            service_name=service_name,
        )
    return service
