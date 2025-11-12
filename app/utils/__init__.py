"""Utility package with lazy exports to avoid heavy import side effects."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple

_LAZY_IMPORTS: Dict[str, Tuple[str, str]] = {
    # Exceptions
    "ServiceError": ("app.utils.exceptions", "ServiceError"),
    "ValidationError": ("app.utils.exceptions", "ValidationError"),
    "ModelNotLoadedError": ("app.utils.exceptions", "ModelNotLoadedError"),
    "ModelInferenceError": ("app.utils.exceptions", "ModelInferenceError"),
    "TextEmptyError": ("app.utils.exceptions", "TextEmptyError"),
    "TextTooLongError": ("app.utils.exceptions", "TextTooLongError"),
    # Error codes/helpers
    "ErrorCode": ("app.utils.error_codes", "ErrorCode"),
    "ErrorMessages": ("app.utils.error_codes", "ErrorMessages"),
    "handle_prediction_error": ("app.utils.error_handlers", "handle_prediction_error"),
    "handle_metrics_error": ("app.utils.error_handlers", "handle_metrics_error"),
    "handle_model_info_error": ("app.utils.error_handlers", "handle_model_info_error"),
    "handle_prometheus_metrics_error": (
        "app.utils.error_handlers",
        "handle_prometheus_metrics_error",
    ),
    # Logging adapters
    "StdLibLoggerAdapter": ("app.utils.logging_adapters", "StdLibLoggerAdapter"),
    "get_fallback_logger": ("app.utils.logging_adapters", "get_fallback_logger"),
    "get_fallback_contextual_logger": (
        "app.utils.logging_adapters",
        "get_fallback_contextual_logger",
    ),
}

__all__ = sorted(_LAZY_IMPORTS)


def __getattr__(name: str) -> Any:
    """Dynamically import requested attributes on first access."""

    try:
        module_name, attr_name = _LAZY_IMPORTS[name]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return sorted attributes for IDE support."""

    return sorted(__all__)
