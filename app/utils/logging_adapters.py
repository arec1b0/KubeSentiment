"""Fallback logging adapters for environments without structlog."""

from __future__ import annotations

import logging
from typing import Any, Dict


class StdLibLoggerAdapter:
    """Lightweight adapter that emulates the structlog interface with stdlib logging."""

    __slots__ = ("_logger",)

    def __init__(self, name: str):
        """Initializes the standard library logger adapter.

        Args:
            name: The name of the logger to retrieve.
        """
        self._logger = logging.getLogger(name)

    def _render(self, message: str, **extra: Any) -> str:
        """Formats the log message with extra context.

        Args:
            message: The main log message.
            **extra: Additional context key-value pairs.

        Returns:
            The formatted log message string.
        """
        payload: Dict[str, Any] = {k: v for k, v in extra.items() if k != "exc_info"}
        if payload:
            formatted = ", ".join(f"{key}={value!r}" for key, value in payload.items())
            return f"{message} | {formatted}"
        return message

    def _log(self, level: int, message: str, *args: Any, **kwargs: Any) -> None:
        """Internal helper to log a message at a specific level.

        Args:
            level: The numeric logging level.
            message: The log message.
            *args: Positional arguments for the logger.
            **kwargs: Keyword arguments, including 'exc_info' and extra context.
        """
        exc_info = kwargs.pop("exc_info", None)
        self._logger.log(level, self._render(message, **kwargs), *args, exc_info=exc_info)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs a debug message.

        Args:
            message: The log message.
            *args: Positional arguments for the logger.
            **kwargs: Keyword arguments, including extra context.
        """
        self._log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs an info message.

        Args:
            message: The log message.
            *args: Positional arguments for the logger.
            **kwargs: Keyword arguments, including extra context.
        """
        self._log(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs a warning message.

        Args:
            message: The log message.
            *args: Positional arguments for the logger.
            **kwargs: Keyword arguments, including extra context.
        """
        self._log(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs an error message.

        Args:
            message: The log message.
            *args: Positional arguments for the logger.
            **kwargs: Keyword arguments, including extra context.
        """
        self._log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs a critical message.

        Args:
            message: The log message.
            *args: Positional arguments for the logger.
            **kwargs: Keyword arguments, including extra context.
        """
        self._log(logging.CRITICAL, message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs an error message with exception information.

        Args:
            message: The log message.
            *args: Positional arguments for the logger.
            **kwargs: Keyword arguments, including extra context.
        """
        kwargs.setdefault("exc_info", True)
        self.error(message, *args, **kwargs)


def get_fallback_logger(name: str) -> StdLibLoggerAdapter:
    """Return a standard-library logger adapter when structlog is unavailable.

    Args:
        name: The name of the logger.

    Returns:
        An instance of StdLibLoggerAdapter.
    """
    return StdLibLoggerAdapter(name)


def get_fallback_contextual_logger(name: str, **_: Any) -> StdLibLoggerAdapter:
    """Return a contextual logger adapter compatible with structlog-based callers.

    Args:
        name: The name of the logger.
        **_: Additional keyword arguments (ignored).

    Returns:
        An instance of StdLibLoggerAdapter.
    """
    return StdLibLoggerAdapter(name)


__all__ = [
    "StdLibLoggerAdapter",
    "get_fallback_logger",
    "get_fallback_contextual_logger",
]
