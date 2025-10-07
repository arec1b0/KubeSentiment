"""
Model strategy pattern for supporting multiple inference backends.

This module defines the strategy interface and concrete implementations
for different model backends (PyTorch, ONNX) to enable a unified API.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Protocol


class ModelStrategy(Protocol):
    """
    Protocol defining the interface for model inference strategies.

    This allows different model backends (PyTorch, ONNX) to be used
    interchangeably through dependency injection.
    """

    def is_ready(self) -> bool:
        """Check if the model is ready for inference."""
        ...

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Perform prediction on input text.

        Args:
            text: Input text to analyze

        Returns:
            Dict containing prediction results
        """
        ...

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        ...

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the model."""
        ...


class ModelBackend:
    """Enum-like class for model backend types."""

    PYTORCH = "pytorch"
    ONNX = "onnx"
