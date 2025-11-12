"""Fallback logging adapters for environments without structlog."""

from __future__ import annotations

import logging
from typing import Any, Dict


class StdLibLoggerAdapter:
    """Lightweight adapter that emulates the structlog interface with stdlib logging."""

    __slots__ = ("_logger",)

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _render(self, message: str, **extra: Any) -> str:
        payload: Dict[str, Any] = {k: v for k, v in extra.items() if k != "exc_info"}
        if payload:
            formatted = ", ".join(f"{key}={value!r}" for key, value in payload.items())
            return f"{message} | {formatted}"
        return message

    def _log(self, level: int, message: str, *args: Any, **kwargs: Any) -> None:
        exc_info = kwargs.pop("exc_info", None)
        self._logger.log(level, self._render(message, **kwargs), *args, exc_info=exc_info)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("exc_info", True)
        self.error(message, *args, **kwargs)


def get_fallback_logger(name: str) -> StdLibLoggerAdapter:
    """Return a standard-library logger adapter when structlog is unavailable."""

    return StdLibLoggerAdapter(name)


def get_fallback_contextual_logger(name: str, **_: Any) -> StdLibLoggerAdapter:
    """Return a contextual logger adapter compatible with structlog-based callers."""

    return StdLibLoggerAdapter(name)


__all__ = [
    "StdLibLoggerAdapter",
    "get_fallback_logger",
    "get_fallback_contextual_logger",
]
