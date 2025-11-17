"""
Model Explainability and Interpretability for KubeSentiment.

This module provides various explanation methods for sentiment predictions:
- Attention weights visualization
- SHAP values for feature importance
- Word-level contribution scores
- Confidence calibration
- Example-based explanations
"""

import numpy as np
from typing import Dict, Optional, Any
import torch
from transformers import AutoTokenizer

from app.core.logging import get_logger
from app.interfaces.explainability_interface import IExplainabilityEngine

try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

try:
    from captum.attr import LayerIntegratedGradients, TokenReferenceBase

    CAPTUM_AVAILABLE = True
except ImportError:
    CAPTUM_AVAILABLE = False

logger = get_logger(__name__)


class ExplainabilityEngine(IExplainabilityEngine):
    """
    Comprehensive explainability engine for sentiment analysis.

    Features:
    - Attention-based explanations (from transformer attention weights)
    - SHAP values for black-box interpretability
    - Integrated Gradients for gradient-based attribution
    - Word-level importance scores
    - Confidence calibration

    Example:
        >>> explainer = ExplainabilityEngine(model, tokenizer)
        >>> explanation = explainer.explain("This movie was amazing!")
        >>> print(explanation['word_importance'])
    """

    def __init__(
        self,
        model: Any,
        tokenizer: Optional[AutoTokenizer] = None,
        model_name: str = "distilbert-base-uncased-finetuned-sst-2-english",
        enabled: bool = True,
    ):
        """
        Initialize explainability engine.

        Args:
            model: The sentiment analysis model
            tokenizer: Tokenizer for the model
            model_name: Name of the model (for loading tokenizer)
            enabled: Whether explainability is enabled
        """
        self.enabled = enabled
        self.model = model
        self.model_name = model_name

        # Initialize tokenizer
        if tokenizer is None and enabled:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            except Exception as e:
                logger.error("Failed to load tokenizer", error=str(e), exc_info=True)
                self.enabled = False
                return
        else:
            self.tokenizer = tokenizer

        # Check if model is PyTorch-based
        self.is_pytorch = hasattr(model, "eval") and hasattr(model, "forward")

        if not self.is_pytorch:
            logger.warning("Model is not PyTorch-based, some explainability features disabled")

        logger.info("Explainability engine initialized", model_name=model_name)

    def extract_attention_weights(
        self, text: str, normalize: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Extract attention weights from transformer model.

        Args:
            text: Input text
            normalize: Whether to normalize attention scores

        Returns:
            Dictionary with tokens and attention weights
        """
        if not self.enabled or not self.is_pytorch:
            return None

        try:
            # Tokenize input
            inputs = self.tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512, padding=True
            )

            # Get model outputs with attention
            with torch.no_grad():
                outputs = self.model(**inputs, output_attentions=True)

            # Extract attention weights
            # Shape: (batch, num_heads, seq_len, seq_len)
            attentions = outputs.attentions  # Tuple of tensors for each layer

            # Use last layer attention
            last_layer_attention = attentions[-1][0]  # (num_heads, seq_len, seq_len)

            # Average across heads
            avg_attention = last_layer_attention.mean(dim=0)  # (seq_len, seq_len)

            # Get attention from [CLS] token (classification token)
            cls_attention = avg_attention[0, :].numpy()

            # Normalize if requested
            if normalize:
                cls_attention = cls_attention / cls_attention.sum()

            # Get tokens
            tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

            # Create word-level importance (exclude special tokens)
            word_importance = []
            for i, (token, score) in enumerate(zip(tokens, cls_attention)):
                if token not in ["[CLS]", "[SEP]", "[PAD]"]:
                    # Clean up subword tokens (##)
                    clean_token = token.replace("##", "")
                    word_importance.append(
                        {"word": clean_token, "importance": float(score), "position": i}
                    )

            return {
                "tokens": tokens,
                "attention_weights": cls_attention.tolist(),
                "word_importance": word_importance,
            }
        except Exception as e:
            logger.error("Failed to extract attention weights", error=str(e), exc_info=True)
            return None

    def compute_integrated_gradients(
        self, text: str, target_class: int = 1, n_steps: int = 50
    ) -> Optional[Dict[str, Any]]:
        """
        Compute Integrated Gradients for feature attribution.

        Args:
            text: Input text
            target_class: Target class index
            n_steps: Number of steps for IG approximation

        Returns:
            Dictionary with tokens and attribution scores
        """
        if not self.enabled or not self.is_pytorch or not CAPTUM_AVAILABLE:
            return None

        try:
            # Tokenize input
            inputs = self.tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512, padding=True
            )

            # Create baseline (all zeros or PAD tokens)
            baseline_input_ids = torch.zeros_like(inputs["input_ids"])
            baseline_input_ids[:] = self.tokenizer.pad_token_id

            # Create reference token for baseline
            token_reference = TokenReferenceBase(reference_token_idx=self.tokenizer.pad_token_id)

            # Initialize Integrated Gradients
            lig = LayerIntegratedGradients(self._forward_func, self.model.get_input_embeddings())

            # Compute attributions
            attributions = lig.attribute(
                inputs=inputs["input_ids"],
                baselines=baseline_input_ids,
                target=target_class,
                n_steps=n_steps,
            )

            # Sum attributions across embedding dimension
            attributions_sum = attributions.sum(dim=-1).squeeze(0)
            attributions_sum = attributions_sum / torch.norm(attributions_sum)

            # Get tokens
            tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

            # Create word-level attribution
            word_attributions = []
            for i, (token, score) in enumerate(zip(tokens, attributions_sum)):
                if token not in ["[CLS]", "[SEP]", "[PAD]"]:
                    clean_token = token.replace("##", "")
                    word_attributions.append(
                        {"word": clean_token, "attribution": float(score), "position": i}
                    )

            return {
                "tokens": tokens,
                "attributions": attributions_sum.tolist(),
                "word_attributions": word_attributions,
            }
        except Exception as e:
            logger.error("Failed to compute integrated gradients", error=str(e), exc_info=True)
            return None

    def _forward_func(self, input_ids):
        """Forward function wrapper for Captum."""
        attention_mask = (input_ids != self.tokenizer.pad_token_id).long()
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
        return outputs.logits

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
            use_attention: Whether to use attention weights
            use_gradients: Whether to use gradient-based methods

        Returns:
            Dictionary with all available explanations
        """
        if not self.enabled:
            return {"enabled": False}

        explanation = {
            "text": text,
            "prediction": prediction,
            "confidence": confidence,
            "explanation_methods": [],
        }

        # 1. Attention-based explanation
        if use_attention and self.is_pytorch:
            attention_exp = self.extract_attention_weights(text)
            if attention_exp:
                explanation["attention"] = attention_exp
                explanation["explanation_methods"].append("attention")

                # Highlight top contributing words
                top_words = sorted(
                    attention_exp["word_importance"], key=lambda x: x["importance"], reverse=True
                )[:5]
                explanation["top_contributing_words"] = [w["word"] for w in top_words]

        # 2. Integrated Gradients explanation
        if use_gradients and CAPTUM_AVAILABLE and self.is_pytorch:
            # Determine target class
            target_class = 1 if prediction == "POSITIVE" else 0

            ig_exp = self.compute_integrated_gradients(text, target_class=target_class)
            if ig_exp:
                explanation["integrated_gradients"] = ig_exp
                explanation["explanation_methods"].append("integrated_gradients")

        # 3. Confidence calibration
        explanation["confidence_interpretation"] = self._interpret_confidence(confidence)

        # 4. Text features
        explanation["text_features"] = self._extract_text_features(text)

        return explanation

    def _interpret_confidence(self, confidence: float) -> str:
        """
        Interpret confidence score.

        Args:
            confidence: Prediction confidence

        Returns:
            Human-readable interpretation
        """
        if confidence >= 0.95:
            return "Very high confidence - strong signal"
        elif confidence >= 0.80:
            return "High confidence - clear sentiment"
        elif confidence >= 0.60:
            return "Moderate confidence - some ambiguity"
        elif confidence >= 0.50:
            return "Low confidence - uncertain prediction"
        else:
            return "Very low confidence - highly uncertain"

    def _extract_text_features(self, text: str) -> Dict[str, Any]:
        """
        Extract interpretable text features.

        Args:
            text: Input text

        Returns:
            Dictionary of text features
        """
        words = text.split()

        # Positive/negative word indicators
        positive_words = [
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "fantastic",
            "love",
            "best",
        ]
        negative_words = [
            "bad",
            "terrible",
            "awful",
            "horrible",
            "worst",
            "hate",
            "poor",
            "disappointing",
        ]

        text_lower = text.lower()

        return {
            "length": len(text),
            "word_count": len(words),
            "avg_word_length": np.mean([len(w) for w in words]) if words else 0,
            "positive_word_count": sum(1 for w in positive_words if w in text_lower),
            "negative_word_count": sum(1 for w in negative_words if w in text_lower),
            "has_exclamation": "!" in text,
            "has_question": "?" in text,
            "is_uppercase": text.isupper(),
            "capitalized_word_count": sum(1 for w in words if w[0].isupper() if w),
        }

    def generate_html_explanation(self, explanation: Dict[str, Any]) -> str:
        """
        Generate HTML visualization of explanation.

        Args:
            explanation: Explanation dictionary

        Returns:
            HTML string
        """
        if not explanation.get("enabled", True):
            return "<p>Explainability not available</p>"

        html = f"""
        <div class="explanation-container" style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Prediction Explanation</h2>
            <div class="prediction-info">
                <p><strong>Text:</strong> {explanation['text']}</p>
                <p><strong>Prediction:</strong> <span style="color: {'green' if explanation['prediction'] == 'POSITIVE' else 'red'};">{explanation['prediction']}</span></p>
                <p><strong>Confidence:</strong> {explanation['confidence']:.2%}</p>
                <p><strong>Interpretation:</strong> {explanation.get('confidence_interpretation', 'N/A')}</p>
            </div>
        """

        # Add word importance visualization
        if "attention" in explanation:
            html += "<h3>Word Importance (Attention Weights)</h3><div class='word-importance'>"
            for word_info in explanation["attention"]["word_importance"]:
                # Color intensity based on importance
                intensity = int(word_info["importance"] * 255)
                html += f"<span style='background-color: rgba(0, 123, 255, {word_info['importance']:.2f}); padding: 2px 5px; margin: 2px; border-radius: 3px;'>{word_info['word']}</span> "
            html += "</div>"

        # Add top contributing words
        if "top_contributing_words" in explanation:
            html += f"<h3>Top Contributing Words</h3><p>{', '.join(explanation['top_contributing_words'])}</p>"

        # Add text features
        if "text_features" in explanation:
            features = explanation["text_features"]
            html += f"""
            <h3>Text Features</h3>
            <ul>
                <li>Word count: {features['word_count']}</li>
                <li>Positive words: {features['positive_word_count']}</li>
                <li>Negative words: {features['negative_word_count']}</li>
                <li>Has exclamation: {features['has_exclamation']}</li>
            </ul>
            """

        html += "</div>"
        return html


# Global explainability engine instance
_explainability_engine: Optional[ExplainabilityEngine] = None


def get_explainability_engine() -> Optional[ExplainabilityEngine]:
    """Get the global explainability engine instance."""
    return _explainability_engine


def initialize_explainability_engine(
    model: Any,
    tokenizer: Optional[AutoTokenizer] = None,
    model_name: str = "distilbert-base-uncased-finetuned-sst-2-english",
    enabled: bool = True,
) -> ExplainabilityEngine:
    """Initialize the global explainability engine instance."""
    global _explainability_engine
    _explainability_engine = ExplainabilityEngine(
        model=model, tokenizer=tokenizer, model_name=model_name, enabled=enabled
    )
    return _explainability_engine
