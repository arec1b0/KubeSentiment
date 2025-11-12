"""
Model implementations for sentiment analysis.

This package contains the model implementations and factory pattern for creating
model instances. It supports multiple backends (PyTorch, ONNX) via the Strategy
pattern, allowing for flexible and interchangeable model implementations.
"""

from app.models.base import ModelStrategy
from app.models.factory import ModelFactory

__all__ = ["ModelStrategy", "ModelFactory"]
