"""
Interface for Prediction Service

Defines the contract for sentiment prediction services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class IPredictionService(ABC):
    """
    Interface for sentiment prediction services.

    Implementations must provide both single and batch prediction capabilities.
    """

    @abstractmethod
    def predict(self, text: str) -> Dict[str, Any]:
        """
        Perform sentiment prediction on a single text.

        Args:
            text: Input text to analyze

        Returns:
            Dictionary containing:
                - sentiment: Predicted sentiment label
                - confidence: Confidence score
                - probabilities: Class probabilities (optional)
                - metadata: Additional prediction metadata (optional)

        Raises:
            ValueError: If text is invalid or empty
            RuntimeError: If prediction fails
        """
        pass

    @abstractmethod
    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Perform sentiment prediction on a batch of texts.

        Args:
            texts: List of input texts to analyze

        Returns:
            List of prediction dictionaries (same format as predict())

        Raises:
            ValueError: If texts list is invalid
            RuntimeError: If batch prediction fails
        """
        pass
