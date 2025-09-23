"""
Custom exception hierarchy for the service.

Defines domain-specific exceptions that map to HTTP errors and
can be used across the codebase for consistent error handling.
"""

from typing import Any


class ServiceError(Exception):
    """Base class for service errors."""

    def __init__(self, message: str, code: str = "E0000", context: Any = None):
        super().__init__(message)
        self.code = code
        self.context = context


class ValidationError(ServiceError):
    """Validation error (bad input)."""

    status_code = 400


class AuthenticationError(ServiceError):
    """Authentication/authorization failure."""

    status_code = 401


class NotFoundError(ServiceError):
    """Resource not found."""

    status_code = 404


class ConflictError(ServiceError):
    """Conflict or duplicate resource."""

    status_code = 409


class InternalError(ServiceError):
    """Internal server error."""

    status_code = 500


class ServiceUnavailableError(ServiceError):
    """Service temporarily unavailable."""

    status_code = 503
