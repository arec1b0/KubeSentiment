"""
Core application components.

This module contains fundamental application components like configuration,
logging, dependency injection, and lifecycle management.
"""

from .config import Settings, get_settings
from .dependencies import get_model_service, get_prediction_service
from .logging import get_contextual_logger, get_logger, setup_logging

__all__ = [
    "Settings",
    "get_settings",
    "setup_logging",
    "get_logger",
    "get_contextual_logger",
    "get_model_service",
    "get_prediction_service",
]

