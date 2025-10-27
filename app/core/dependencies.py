"""
Dependency injection for the MLOps sentiment analysis service.

This module provides centralized dependency injection functions for FastAPI,
following the dependency inversion principle. It allows for a clean separation
of concerns and makes the application more modular, testable, and maintainable
by decoupling the API layer from the concrete implementations of services and
models.
"""

from typing import Optional

from fastapi import Depends, Query

from app.core.config import Settings, get_settings


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
):
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
        An instance of the `PredictionService`.
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
