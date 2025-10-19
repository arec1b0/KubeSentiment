"""
Utility modules.

This module contains utility functions, exceptions, error codes,
and error handlers.
"""

from app.utils.error_codes import ErrorCode, ErrorMessages
from app.utils.error_handlers import (
    handle_metrics_error,
    handle_model_info_error,
    handle_prediction_error,
    handle_prometheus_metrics_error,
)
from app.utils.exceptions import (
    ModelInferenceError,
    ModelNotLoadedError,
    ServiceError,
    TextEmptyError,
    TextTooLongError,
    ValidationError,
)

__all__ = [
    "ServiceError",
    "ValidationError",
    "ModelNotLoadedError",
    "ModelInferenceError",
    "TextEmptyError",
    "TextTooLongError",
    "ErrorCode",
    "ErrorMessages",
    "handle_prediction_error",
    "handle_metrics_error",
    "handle_model_info_error",
    "handle_prometheus_metrics_error",
]

