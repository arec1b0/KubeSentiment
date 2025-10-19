"""
Comprehensive input validation tests for the MLOps sentiment analysis service.

Tests cover text input validation, model validation, and edge cases
to ensure proper error handling and security.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.schemas.requests import TextInput
from app.core.config import Settings
from app.main import create_app
from app.utils.exceptions import (
    InvalidModelError,
    ModelInferenceError,
    ModelNotLoadedError,
    TextEmptyError,
    TextTooLongError,
)


class TestTextInputValidation:
    """Test text input validation in Pydantic models and endpoints."""

    def test_valid_text_input(self):
        """Test that valid text input passes validation."""
        valid_input = TextInput(text="This is a valid text input for sentiment analysis.")
        assert valid_input.text == "This is a valid text input for sentiment analysis."

    def test_empty_string_raises_error(self):
        """Test that empty string raises TextEmptyError."""
        with pytest.raises(TextEmptyError) as exc_info:
            TextInput(text="")

        assert exc_info.value.code == "TEXT_EMPTY"
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_only_raises_error(self):
        """Test that whitespace-only string raises TextEmptyError."""
        with pytest.raises(TextEmptyError) as exc_info:
            TextInput(text="   \n\t  ")

        assert exc_info.value.code == "TEXT_EMPTY"

    def test_none_raises_error(self):
        """Test that None value raises appropriate error."""
        with pytest.raises(Exception):  # Pydantic validation error
            TextInput(text=None)

    @patch("app.api.get_settings")
    def test_text_too_long_raises_error(self, mock_get_settings):
        """Test that text exceeding max length raises TextTooLongError."""
        # Mock settings with small max length for testing
        mock_settings = Mock()
        mock_settings.max_text_length = 10
        mock_get_settings.return_value = mock_settings

        long_text = "This text is definitely longer than 10 characters and should fail validation"

        with pytest.raises(TextTooLongError) as exc_info:
            TextInput(text=long_text)

        assert exc_info.value.code == "TEXT_TOO_LONG"
        assert "exceeds maximum" in str(exc_info.value)

    def test_text_with_special_characters(self):
        """Test that text with special characters is handled properly."""
        special_text = "Hello! 🎉 This has émojis & special chars: <script>alert('xss')</script>"
        valid_input = TextInput(text=special_text)

        # Text should be stripped but special characters preserved
        assert valid_input.text == special_text

    def test_text_gets_stripped(self):
        """Test that leading/trailing whitespace is stripped."""
        padded_text = "  \t\n  Valid text with padding  \n\t  "
        valid_input = TextInput(text=padded_text)

        assert valid_input.text == "Valid text with padding"

    @patch("app.api.get_settings")
    def test_edge_case_exact_max_length(self, mock_get_settings):
        """Test text that is exactly at the max length limit."""
        mock_settings = Mock()
        mock_settings.max_text_length = 10
        mock_get_settings.return_value = mock_settings

        exact_length_text = "1234567890"  # Exactly 10 characters
        valid_input = TextInput(text=exact_length_text)

        assert valid_input.text == exact_length_text


class TestModelValidation:
    """Test model name validation and security checks."""

    @patch("app.models.pytorch_sentiment.get_settings")
    def test_invalid_model_name_raises_error(self, mock_get_settings):
        """Test that unauthorized model names raise InvalidModelError."""
        from app.models.pytorch_sentiment import SentimentAnalyzer

        mock_settings = Mock()
        mock_settings.allowed_models = ["model1", "model2"]
        mock_settings.model_name = "unauthorized-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_get_settings.return_value = mock_settings

        with pytest.raises(InvalidModelError) as exc_info:
            analyzer = SentimentAnalyzer()

        assert exc_info.value.code == "INVALID_MODEL_NAME"
        assert "unauthorized-model" in str(exc_info.value)
        assert "not allowed" in str(exc_info.value)

    @patch("app.models.pytorch_sentiment.get_settings")
    @patch("app.models.pytorch_sentiment.pipeline")
    def test_valid_model_name_passes(self, mock_pipeline, mock_get_settings):
        """Test that valid model names pass validation."""
        from app.models.pytorch_sentiment import SentimentAnalyzer

        mock_settings = Mock()
        mock_settings.allowed_models = ["valid-model"]
        mock_settings.model_name = "valid-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_settings.model_cache_dir = None
        mock_get_settings.return_value = mock_settings

        mock_pipeline.return_value = Mock()

        # Should not raise an exception
        analyzer = SentimentAnalyzer()
        assert analyzer is not None


class TestAPIEndpointValidation:
    """Test input validation through API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(create_app())

    @pytest.fixture
    def mock_analyzer(self):
        """Create mock analyzer."""
        with patch("app.api.get_sentiment_analyzer") as mock:
            analyzer = Mock()
            analyzer.is_ready.return_value = True
            analyzer.predict.return_value = {
                "label": "POSITIVE",
                "score": 0.95,
                "inference_time_ms": 10.5,
                "model_name": "test-model",
                "text_length": 10,
                "cached": False,
            }
            mock.return_value = analyzer
            yield analyzer

    def test_predict_endpoint_empty_text(self, client, mock_analyzer):
        """Test prediction endpoint with empty text."""
        response = client.post("/predict", json={"text": ""})

        assert response.status_code == 400
        assert "TEXT_EMPTY" in response.json()["error_code"]

    def test_predict_endpoint_missing_text_field(self, client, mock_analyzer):
        """Test prediction endpoint with missing text field."""
        response = client.post("/predict", json={})

        assert response.status_code == 422  # Pydantic validation error

    @patch("app.config.Settings.max_text_length", 20)
    def test_predict_endpoint_text_too_long(self, client, mock_analyzer):
        """Test prediction endpoint with text that's too long."""
        long_text = "This text is definitely much longer than 20 characters and should fail"
        response = client.post("/predict", json={"text": long_text})

        assert response.status_code == 400
        assert "TEXT_TOO_LONG" in response.json()["error_code"]

    def test_predict_endpoint_valid_text(self, client, mock_analyzer):
        """Test prediction endpoint with valid text."""
        response = client.post("/predict", json={"text": "This is valid text"})

        assert response.status_code == 200
        data = response.json()
        assert "label" in data
        assert "score" in data
        assert "inference_time_ms" in data

    def test_predict_endpoint_model_not_loaded(self, client):
        """Test prediction endpoint when model is not loaded."""
        with patch("app.api.get_sentiment_analyzer") as mock:
            analyzer = Mock()
            analyzer.is_ready.return_value = False
            mock.return_value = analyzer

            response = client.post("/predict", json={"text": "Test text"})

            assert response.status_code == 503
            assert "MODEL_NOT_LOADED" in response.json()["error_code"]


class TestSecurityInputValidation:
    """Test security-related input validation."""

    def test_potential_xss_in_text_input(self):
        """Test that potential XSS content is handled safely."""
        xss_text = "<script>alert('XSS')</script>"
        valid_input = TextInput(text=xss_text)

        # Input should be preserved as-is (not escaped at input level)
        # Escaping should happen at output/logging level
        assert valid_input.text == xss_text

    def test_sql_injection_like_content(self):
        """Test handling of SQL injection-like content."""
        sql_text = "'; DROP TABLE users; --"
        valid_input = TextInput(text=sql_text)

        assert valid_input.text == sql_text

    def test_unicode_and_emoji_handling(self):
        """Test proper handling of Unicode and emoji characters."""
        unicode_text = "Hello 世界! 🌍🚀 Testing üñíçødé"
        valid_input = TextInput(text=unicode_text)

        assert valid_input.text == unicode_text

    def test_very_long_single_word(self):
        """Test handling of extremely long single words."""
        long_word = "a" * 1000

        with pytest.raises(TextTooLongError):
            TextInput(text=long_word)

    def test_newlines_and_control_characters(self):
        """Test handling of newlines and control characters."""
        text_with_controls = "Line 1\nLine 2\r\nLine 3\tTabbed\x00\x01\x02"
        valid_input = TextInput(text=text_with_controls)

        # Should preserve the text as-is
        assert valid_input.text == text_with_controls


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_length_after_strip(self):
        """Test text that becomes zero length after stripping."""
        with pytest.raises(TextEmptyError):
            TextInput(text="   \n\t\r   ")

    @patch("app.api.get_settings")
    def test_settings_mock_error_handling(self, mock_get_settings):
        """Test graceful handling when settings access fails."""
        # Simulate settings access error
        mock_get_settings.side_effect = Exception("Settings error")

        # Should fall back to default behavior
        valid_input = TextInput(text="Test text")
        assert valid_input.text == "Test text"

    def test_international_characters(self):
        """Test various international character sets."""
        international_texts = [
            "こんにちは",  # Japanese
            "مرحبا",  # Arabic
            "Здравствуйте",  # Russian
            "नमस्ते",  # Hindi
            "🇺🇸🇬🇧🇫🇷",  # Flag emojis
        ]

        for text in international_texts:
            valid_input = TextInput(text=text)
            assert valid_input.text == text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
