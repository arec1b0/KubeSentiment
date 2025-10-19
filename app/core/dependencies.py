"""
Dependency injection for the application.

This module provides centralized dependency injection functions for FastAPI.
"""

from functools import lru_cache
from typing import Optional

from fastapi import Depends, Query

from app.core.config import Settings, get_settings


def get_model_backend(
    backend: Optional[str] = Query(
        None, description="Model backend to use (pytorch/onnx)"
    ),
    settings: Settings = Depends(get_settings),
) -> str:
    """
    Determine which model backend to use.

    Args:
        backend: Optional backend override from query parameter
        settings: Application settings

    Returns:
        Backend name to use (pytorch or onnx)
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
    """
    Get the appropriate model service based on backend selection.

    Args:
        backend: The selected backend

    Returns:
        Model service instance
    """
    # Import here to avoid circular imports
    from app.models.factory import ModelFactory

    return ModelFactory.create_model(backend)


def get_prediction_service(
    model=Depends(get_model_service),
    settings: Settings = Depends(get_settings),
):
    """
    Get the prediction service with injected dependencies.

    Args:
        model: Model service instance
        settings: Application settings

    Returns:
        Prediction service instance
    """
    from app.services.prediction import PredictionService

    return PredictionService(model=model, settings=settings)

