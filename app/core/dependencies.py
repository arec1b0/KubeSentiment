"""
Dependency injection for the application.

This module provides centralized dependency injection functions for FastAPI.
"""

from functools import lru_cache
from typing import Optional

from fastapi import Depends, Query

from app.core.config import Settings, get_settings


def get_model_backend(
    backend: Optional[str] = Query(None, description="Model backend to use (pytorch/onnx)"),
    settings: Settings = Depends(get_settings),
) -> str:
    """Determines the model backend based on query parameters and settings.

    This dependency function inspects the 'backend' query parameter. If it's
    provided, it will be used. Otherwise, it checks if an ONNX model path is
    configured in the settings. If so, 'onnx' is returned; otherwise, it
    defaults to 'pytorch'.

    Args:
        backend: The model backend specified in the query parameter.
        settings: The application's configuration settings.

    Returns:
        The name of the model backend to use, either 'onnx' or 'pytorch'.
    """
    if backend:
        return backend.lower()
    elif settings.onnx_model_path:
        return "onnx"
    else:
        return "pytorch"


def get_model_service(
    backend: str = Depends(get_model_backend),
):
    """Provides a model service instance based on the selected backend.

    This function acts as a factory for the model service. It uses the
    `get_model_backend` dependency to determine which backend to use and then
    creates the appropriate model service instance.

    Args:
        backend: The selected model backend, provided by `get_model_backend`.

    Returns:
        An instance of the model service corresponding to the backend.
    """
    # Import here to avoid circular imports
    from app.models.factory import ModelFactory

    return ModelFactory.create_model(backend)


def get_prediction_service(
    model=Depends(get_model_service),
    settings: Settings = Depends(get_settings),
):
    """Provides an instance of the prediction service.

    This dependency injects the appropriate model service and the application
    settings into the `PredictionService`, making it available to the API
    endpoints.

    Args:
        model: The model service instance from `get_model_service`.
        settings: The application's configuration settings.

    Returns:
        An instance of the `PredictionService`.
    """
    from app.services.prediction import PredictionService

    return PredictionService(model=model, settings=settings)
