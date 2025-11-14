"""
Interface for Explainability Engine

Defines the contract for model explainability and interpretability services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IExplainabilityEngine(ABC):
    """
    Interface for model explainability services.

    Provides various methods for explaining model predictions.
    """

    @abstractmethod
    def extract_attention_weights(
        self, text: str, normalize: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extract attention weights from transformer model.

        Args:
            text: Input text to analyze
            normalize: Whether to normalize attention weights

        Returns:
            List of dictionaries with token and attention score pairs

        Raises:
            RuntimeError: If model doesn't support attention extraction
        """
        pass

    @abstractmethod
    def compute_integrated_gradients(
        self, text: str, target_class: Optional[int] = None, n_steps: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Compute integrated gradients for feature attribution.

        Args:
            text: Input text to analyze
            target_class: Target class for attribution (None for predicted class)
            n_steps: Number of integration steps

        Returns:
            List of dictionaries with token and attribution score pairs

        Raises:
            RuntimeError: If gradient computation fails
        """
        pass

    @abstractmethod
    def explain_prediction(
        self,
        text: str,
        prediction: str,
        confidence: float,
        use_attention: bool = True,
        use_gradients: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive explanation for a prediction.

        Args:
            text: Input text
            prediction: Predicted label
            confidence: Prediction confidence
            use_attention: Whether to include attention-based explanations
            use_gradients: Whether to include gradient-based explanations

        Returns:
            Dictionary containing:
                - text: Original text
                - prediction: Predicted label
                - confidence: Confidence score
                - word_importance: Word-level importance scores
                - attention_weights: Attention-based explanations (optional)
                - gradients: Gradient-based explanations (optional)
                - metadata: Additional explanation metadata

        Raises:
            ValueError: If inputs are invalid
        """
        pass

    @abstractmethod
    def generate_html_explanation(self, explanation: Dict[str, Any]) -> str:
        """
        Generate HTML visualization of explanation.

        Args:
            explanation: Explanation dictionary from explain_prediction()

        Returns:
            HTML string with visualization

        Raises:
            ValueError: If explanation format is invalid
        """
        pass
