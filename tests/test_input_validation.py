"""Comprehensive input validation tests for the sentiment analysis service.

This module contains extensive test cases for input validation at different
layers of the application, including Pydantic schema validation, model name
security checks, API endpoint handling of invalid data, and various edge cases
to ensure robust error handling and security.
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
from pydantic import ValidationError as PydanticValidationError


class TestTextInputValidation:
    """A test suite for the `TextInput` Pydantic model validation.

    These tests cover various scenarios for the text input field, ensuring
    that validation logic for empty strings, length limits, and whitespace
    stripping is working correctly.
    """

    def test_valid_text_input(self):
        """Tests that a standard, valid text input passes validation."""
        valid_input = TextInput(text="This is a valid text input for sentiment analysis.")
        assert valid_input.text == "This is a valid text input for sentiment analysis."

    def test_empty_string_raises_error(self):
        """Tests that an empty string "" raises a validation error."""
        with pytest.raises(PydanticValidationError) as exc_info:
            TextInput(text="")

        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_only_raises_error(self):
        """Tests that a string containing only whitespace raises a validation error."""
        with pytest.raises(PydanticValidationError) as exc_info:
            TextInput(text="   \n\t  ")

        assert "cannot be empty" in str(exc_info.value)

    def test_none_raises_error(self):
        """Tests that a `None` value for the text field raises a validation error."""
        with pytest.raises(Exception):  # Pydantic validation error
            TextInput(text=None)

    @patch("app.api.schemas.requests.get_settings")
    def test_text_too_long_raises_error(self, mock_get_settings):
        """Tests that text exceeding the configured max length raises a validation error."""
        # Mock settings with small max length for testing
        mock_settings = Mock()
        mock_settings.max_text_length = 10
        mock_get_settings.return_value = mock_settings

        long_text = "This text is definitely longer than 10 characters and should fail validation"

        with pytest.raises(PydanticValidationError) as exc_info:
            TextInput(text=long_text)

        assert "exceeds" in str(exc_info.value)

    def test_text_with_special_characters(self):
        """Tests that text containing special characters and emojis is handled correctly."""
        special_text = "Hello! 🎉 This has émojis & special chars: <script>alert('xss')</script>"
        valid_input = TextInput(text=special_text)

        # Text should be stripped but special characters preserved
        assert valid_input.text == special_text

    def test_text_gets_stripped(self):
        """Tests that leading and trailing whitespace is stripped from the input text."""
        padded_text = "  \t\n  Valid text with padding  \n\t  "
        valid_input = TextInput(text=padded_text)

        assert valid_input.text == "Valid text with padding"

    @patch("app.api.schemas.requests.get_settings")
    def test_edge_case_exact_max_length(self, mock_get_settings):
        """Tests that text with a length exactly equal to the max limit passes."""
        mock_settings = Mock()
        mock_settings.max_text_length = 10
        mock_get_settings.return_value = mock_settings

        exact_length_text = "1234567890"  # Exactly 10 characters
        valid_input = TextInput(text=exact_length_text)

        assert valid_input.text == exact_length_text


class TestModelValidation:
    """A test suite for model name validation and security checks.

    These tests ensure that the application only allows loading of models
    that are explicitly listed in the configuration, preventing unauthorized
    model loading.
    """

    @patch("app.models.pytorch_sentiment.get_settings")
    def test_invalid_model_name_raises_error(self, mock_get_settings):
        """Tests that using an unauthorized model name raises an `InvalidModelError`."""
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
        """Tests that a valid, allowed model name passes validation and initializes."""
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
    """A test suite for input validation at the API endpoint layer.

    These tests use a `TestClient` to make requests to the API and verify
    that the endpoints correctly handle invalid inputs, such as empty text or
    text that is too long, returning the appropriate HTTP status codes and
    error messages.
    """

    @pytest.fixture
    def client(self):
        """Creates a FastAPI `TestClient` for the application."""
        return TestClient(create_app())

    @pytest.fixture
    def mock_analyzer(self):
        """Mocks the sentiment analyzer dependency for API tests.

        Yields:
            A `Mock` object simulating the sentiment analyzer.
        """
        with patch("app.api.routes.predictions.get_prediction_service") as mock:
            analyzer = Mock()
            analyzer.get_model_status.return_value = {"is_ready": True}
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
        """Tests that the `/predict` endpoint returns a 422 error for empty text."""
        response = client.post("/predict", json={"text": ""})

        assert response.status_code == 422
        assert "validation" in response.json()["error_message"].lower()

    def test_predict_endpoint_missing_text_field(self, client, mock_analyzer):
        """Tests that the `/predict` endpoint returns a 422 error if the 'text' field is missing."""
        response = client.post("/predict", json={})

        assert response.status_code == 422  # Pydantic validation error

    @patch("app.core.config.Settings.max_text_length", 20)
    def test_predict_endpoint_text_too_long(self, client, mock_analyzer):
        """Tests that the `/predict` endpoint returns a 422 error for text that is too long."""
        long_text = "This text is definitely much longer than 20 characters and should fail"
        response = client.post("/predict", json={"text": long_text})

        assert response.status_code == 422
        assert "validation" in response.json()["error_message"].lower()

    def test_predict_endpoint_valid_text(self, client, mock_analyzer):
        """Tests that the `/predict` endpoint returns a 200 OK for valid text."""
        response = client.post("/predict", json={"text": "This is valid text"})

        assert response.status_code == 200
        data = response.json()
        assert "sentiment" in data and "label" in data["sentiment"]
        assert "score" in data["sentiment"]
        assert "inference_time_ms" in data

    def test_predict_endpoint_model_not_loaded(self, client):
        """Tests that the `/predict` endpoint returns a 503 error if the model is not loaded."""
        with patch("app.api.routes.predictions.get_prediction_service") as mock:
            analyzer = Mock()
            analyzer.get_model_status.return_value = {"is_ready": False}
            mock.return_value = analyzer

            response = client.post("/predict", json={"text": "Test text"})

            assert response.status_code == 503
            assert "MODEL_NOT_LOADED" in response.json()["error_code"]


class TestSecurityInputValidation:
    """A test suite for security-related input validation.

    These tests ensure that potentially malicious inputs, such as XSS or SQL
    injection payloads, are handled safely without being executed or
    sanitized at the input validation layer.
    """

    def test_potential_xss_in_text_input(self):
        """Tests that text containing potential XSS payloads is accepted as-is."""
        xss_text = "<script>alert('XSS')</script>"
        valid_input = TextInput(text=xss_text)

        # Input should be preserved as-is (not escaped at input level)
        # Escaping should happen at output/logging level
        assert valid_input.text == xss_text

    def test_sql_injection_like_content(self):
        """Tests that text resembling SQL injection attacks is accepted as-is."""
        sql_text = "'; DROP TABLE users; --"
        valid_input = TextInput(text=sql_text)

        assert valid_input.text == sql_text

    def test_unicode_and_emoji_handling(self):
        """Tests that Unicode characters and emojis are handled correctly."""
        unicode_text = "Hello 世界! 🌍🚀 Testing üñíçødé"
        valid_input = TextInput(text=unicode_text)

        assert valid_input.text == unicode_text

    def test_very_long_single_word(self):
        """Tests that a single, extremely long word is correctly validated against the max length."""
        long_word = "a" * 10000

        with pytest.raises(PydanticValidationError):
            TextInput(text=long_word)

    def test_newlines_and_control_characters(self):
        """Tests that newline and other control characters are preserved in the input."""
        text_with_controls = "Line 1\nLine 2\r\nLine 3\tTabbed\x00\x01\x02"
        valid_input = TextInput(text=text_with_controls)

        # Should preserve the text as-is
        assert valid_input.text == text_with_controls


class TestEdgeCases:
    """A test suite for various edge cases and boundary conditions.

    These tests cover scenarios like text that becomes empty after stripping,
    graceful handling of configuration errors, and validation of diverse

    international character sets.
    """

    def test_zero_length_after_strip(self):
        """Tests that text that becomes empty after whitespace stripping is rejected."""
        with pytest.raises(PydanticValidationError):
            TextInput(text="   \n\t\r   ")

    @patch("app.api.schemas.requests.get_settings")
    def test_settings_mock_error_handling(self, mock_get_settings):
        """Tests for graceful fallback when the settings dependency fails."""
        # Simulate settings access error
        mock_get_settings.side_effect = Exception("Settings error")

        # Should fall back to default behavior
        valid_input = TextInput(text="Test text")
        assert valid_input.text == "Test text"

    def test_international_characters(self):
        """Tests that various international character sets are handled correctly."""
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


class TestPredictionServiceValidation:
    """A test suite for the `PredictionService` validation logic."""

    @pytest.fixture
    def mock_model(self):
        """Mocks the model strategy."""
        model = Mock()
        model.is_ready.return_value = True
        return model

    @pytest.fixture
    def mock_settings(self):
        """Mocks the application settings."""
        settings = Mock()
        settings.max_text_length = 512
        return settings

    def test_text_too_long_raises_error_in_service(self, mock_model, mock_settings):
        """Tests that `PredictionService` raises `TextTooLongError` for oversized input."""
        from app.services.prediction import PredictionService

        mock_settings.max_text_length = 20
        service = PredictionService(model=mock_model, settings=mock_settings)
        long_text = "This text is well over the twenty-character limit."

        with pytest.raises(TextTooLongError) as exc_info:
            service.predict(long_text)

        assert exc_info.value.code == "TEXT_TOO_LONG"
        assert "exceeds maximum" in str(exc_info.value)
        assert exc_info.value.text_length == len(long_text)
        assert exc_info.value.max_length == mock_settings.max_text_length


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
