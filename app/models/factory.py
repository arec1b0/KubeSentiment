"""
Factory for creating model instances.

This module implements the Factory pattern for creating model instances based
on the selected backend. It abstracts the creation logic and provides a unified
interface for obtaining model instances throughout the application.
"""

from typing import Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.base import ModelStrategy
from app.utils.exceptions import UnsupportedBackendError, ModelInitializationError

logger = get_logger(__name__)

# Cache for model instances to ensure singleton behavior
_model_cache: Dict[str, ModelStrategy] = {}


class ModelFactory:
    """Factory class for creating and managing model instances.

    This class provides static methods for creating model instances based on
    the selected backend (PyTorch or ONNX). It implements singleton pattern
    for model instances to avoid loading multiple copies of the same model.
    """

    @staticmethod
    def create_model(backend: str, model_path: Optional[str] = None) -> ModelStrategy:
        """Create a model instance for the specified backend.

        This method creates and returns a model instance based on the backend
        parameter. It uses a cache to ensure that each backend is instantiated
        only once (singleton pattern).

        Args:
            backend: The model backend to use ('pytorch' or 'onnx').
            model_path: Optional path to the model. For ONNX backend, this
                specifies the path to the ONNX model files. If not provided,
                the default path from settings will be used.

        Returns:
            A model instance that implements the ModelStrategy protocol.

        Raises:
            UnsupportedBackendError: If the backend is not supported.
            ModelInitializationError: If model initialization fails.

        Example:
            >>> model = ModelFactory.create_model("pytorch")
            >>> result = model.predict("This is great!")
        """
        settings = get_settings()
        cache_key = f"{backend}:{model_path or 'default'}"

        # Return cached instance if available
        if cache_key in _model_cache:
            logger.info("Returning cached model instance", backend=backend)
            return _model_cache[cache_key]

        logger.info("Creating new model instance", backend=backend)

        try:
            if backend.lower() == "pytorch":
                from app.models.pytorch_sentiment import get_sentiment_analyzer

                model = get_sentiment_analyzer()
                _model_cache[cache_key] = model
                return model

            elif backend.lower() == "onnx":
                from app.models.onnx_sentiment import get_onnx_sentiment_analyzer

                # Use provided path, or fall back to settings
                onnx_path = (
                    model_path or settings.model.onnx_model_path or settings.model.onnx_model_path_default
                )
                model = get_onnx_sentiment_analyzer(onnx_path)
                _model_cache[cache_key] = model
                return model

            else:
                available = ModelFactory.get_available_backends()
                raise UnsupportedBackendError(backend=backend, supported_backends=available)

        except ImportError as e:
            logger.error("Failed to import backend", backend=backend, error=str(e))
            raise ModelInitializationError(
                message=f"Backend '{backend}' is not available. "
                f"Please ensure required dependencies are installed.",
                backend=backend,
            ) from e
        except (UnsupportedBackendError, ModelInitializationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error("Failed to create model", backend=backend, error=str(e))
            raise ModelInitializationError(
                message=f"Failed to initialize model for backend '{backend}': {e}", backend=backend
            ) from e

    @staticmethod
    def get_available_backends() -> List[str]:
        """Get a list of available model backends.

        This method checks which backends are available by attempting to import
        their respective modules. Only backends with satisfied dependencies
        will be included in the returned list.

        Returns:
            A list of available backend names (e.g., ['pytorch', 'onnx']).

        Example:
            >>> backends = ModelFactory.get_available_backends()
            >>> print(backends)
            ['pytorch', 'onnx']
        """
        available = []

        # Check PyTorch backend
        try:
            import app.models.pytorch_sentiment  # noqa: F401

            available.append("pytorch")
        except ImportError:
            logger.debug("PyTorch backend not available")

        # Check ONNX backend
        try:
            import app.models.onnx_sentiment  # noqa: F401

            available.append("onnx")
        except ImportError:
            logger.debug("ONNX backend not available")

        if not available:
            logger.warning("No model backends are available!")

        return available

    @staticmethod
    def reset_models() -> None:
        """Clear the model cache.

        This method removes all cached model instances, forcing them to be
        reloaded on the next request. This is primarily useful for testing
        and for forcing model reloads after configuration changes.

        Note:
            This will not unload models from memory immediately; Python's
            garbage collector will handle that when there are no more
            references to the model instances.

        Example:
            >>> ModelFactory.reset_models()
            >>> model = ModelFactory.create_model("pytorch")  # Creates new instance
        """
        global _model_cache
        logger.info("Clearing model cache", cached_count=len(_model_cache))
        _model_cache.clear()

    @staticmethod
    def get_cached_models() -> Dict[str, ModelStrategy]:
        """Get the current model cache.

        This method returns a copy of the current model cache, primarily
        for debugging and monitoring purposes.

        Returns:
            A dictionary mapping cache keys to model instances.

        Example:
            >>> cached = ModelFactory.get_cached_models()
            >>> print(f"Currently cached: {list(cached.keys())}")
        """
        return _model_cache.copy()
