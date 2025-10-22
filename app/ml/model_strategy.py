"""
Model strategy pattern for supporting multiple inference backends.

This module defines the strategy interface and concrete implementations
for different model backends (PyTorch, ONNX) to enable a unified API.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol


class ModelStrategy(Protocol):
    """Defines the common interface for all model inference strategies.

    This protocol ensures that any class implementing a model backend (like
    PyTorch or ONNX) adheres to a consistent interface. This allows different
    backends to be used interchangeably throughout the application.
    """

    def is_ready(self) -> bool:
        """Checks if the model is loaded and ready for inference.

        Returns:
            `True` if the model is ready, `False` otherwise.
        """
        ...

    def predict(self, text: str) -> Dict[str, Any]:
        """Performs sentiment analysis on a given text.

        Args:
            text: The input text to be analyzed.

        Returns:
            A dictionary containing the prediction results, including the
            sentiment label and confidence score.
        """
        ...

    def get_model_info(self) -> Dict[str, Any]:
        """Retrieves metadata and information about the loaded model.

        Returns:
            A dictionary containing details about the model, such as its name
            and configuration.
        """
        ...

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Retrieves performance metrics related to the model.

        This may include information about the underlying hardware, such as
        CUDA memory usage if applicable.

        Returns:
            A dictionary of performance metrics.
        """
        ...


class ModelBackend:
    """Provides constants for identifying model backend types.

    This class centralizes the string identifiers for the supported model
    backends, preventing the use of magic strings throughout the codebase.

    Attributes:
        PYTORCH: The identifier for the PyTorch backend.
        ONNX: The identifier for the ONNX backend.
    """

    PYTORCH = "pytorch"
    ONNX = "onnx"
