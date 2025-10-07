"""
Tests for refactored config validators.

Tests verify individual validator methods work correctly.
"""

import pytest
from pydantic import ValidationError
from app.config import Settings


@pytest.mark.unit
class TestConfigValidators:
    """Test individual config validator methods."""

    def test_validate_model_in_allowed_list_success(self):
        """Test model validation passes when model is in allowed list."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            allowed_models=[
                "distilbert-base-uncased-finetuned-sst-2-english",
                "other-model",
            ],
        )

        # Should not raise
        settings._validate_model_in_allowed_list()

    def test_validate_model_in_allowed_list_failure(self):
        """Test model validation fails when model not in allowed list."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="unauthorized-model",
                allowed_models=["allowed-model-1", "allowed-model-2"],
            )

        assert "must be in allowed_models list" in str(exc_info.value)

    def test_validate_worker_count_consistency_debug_mode(self):
        """Test worker count validation in debug mode."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
                debug=True,
                workers=4,
            )

        assert "Cannot use multiple workers in debug mode" in str(exc_info.value)

    def test_validate_worker_count_consistency_production(self):
        """Test worker count validation in production mode."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            debug=False,
            workers=4,
        )

        # Should not raise
        settings._validate_worker_count_consistency()

    def test_validate_cache_memory_usage_within_limits(self):
        """Test cache memory validation passes within limits."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            prediction_cache_max_size=1000,
            max_text_length=512,
        )

        # Should not raise
        settings._validate_cache_memory_usage()

    def test_validate_cache_memory_usage_exceeds_limits(self):
        """Test cache memory validation fails when exceeding limits."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
                prediction_cache_max_size=100000,  # Large cache
                max_text_length=10000,  # Large text
            )

        assert "may use too much memory" in str(exc_info.value)

    def test_cors_origins_validation_rejects_wildcard(self):
        """Test CORS validation rejects wildcard origins."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
                allowed_origins=["*"],
            )

        assert "Wildcard CORS origin" in str(exc_info.value)

    def test_cors_origins_validation_accepts_explicit_origins(self):
        """Test CORS validation accepts explicit origins."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            allowed_origins=["https://example.com", "https://api.example.com"],
        )

        assert len(settings.allowed_origins) == 2

    def test_api_key_validation_requires_minimum_length(self):
        """Test API key validation requires minimum length."""
        import os

        # Set env var to trigger validation
        os.environ["MLOPS_API_KEY"] = "short"

        try:
            with pytest.raises(ValidationError) as exc_info:
                Settings(
                    model_name="distilbert-base-uncased-finetuned-sst-2-english",
                    api_key="short",
                )

            assert "at least 8 characters" in str(exc_info.value)
        finally:
            os.environ.pop("MLOPS_API_KEY", None)

    def test_api_key_validation_requires_complexity(self):
        """Test API key validation requires letters and numbers."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
                api_key="onlyletters",
            )

        assert "must contain both letters and numbers" in str(exc_info.value)

    def test_api_key_validation_passes_with_valid_key(self):
        """Test API key validation passes with valid key."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            api_key="ValidKey123",
        )

        assert settings.api_key == "ValidKey123"

    def test_onnx_model_path_default_field(self):
        """Test onnx_model_path_default field exists and has default."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
        )

        assert hasattr(settings, "onnx_model_path_default")
        assert settings.onnx_model_path_default.endswith(
            "distilbert-base-uncased-finetuned-sst-2-english"
        )


@pytest.mark.unit
class TestConfigFieldValidators:
    """Test individual field validators."""

    def test_allowed_models_format_validation(self):
        """Test allowed_models validates format correctly."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="test",
                allowed_models=["invalid@model#name", "test"],
            )

        assert "Invalid model name format" in str(exc_info.value)

    def test_allowed_models_length_validation(self):
        """Test allowed_models validates model name length."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="test",
                allowed_models=["a" * 250, "test"],  # Too long
            )

        assert "Model name too long" in str(exc_info.value)

    def test_cors_origins_url_format_validation(self):
        """Test CORS origins validates URL format."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
                allowed_origins=["not-a-valid-url"],
            )

        assert "Invalid CORS origin URL" in str(exc_info.value)

    def test_cors_origins_accepts_http_and_https(self):
        """Test CORS origins accepts both HTTP and HTTPS."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            allowed_origins=[
                "http://localhost:3000",
                "https://example.com",
                "https://api.example.com:8443",
            ],
        )

        assert len(settings.allowed_origins) == 3


@pytest.mark.unit
class TestConfigProperties:
    """Test config properties and computed values."""

    def test_cors_origins_property(self):
        """Test cors_origins property returns allowed_origins."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            allowed_origins=["https://example.com"],
        )

        assert settings.cors_origins == settings.allowed_origins

    def test_config_env_prefix(self):
        """Test config uses MLOPS_ prefix for env vars."""
        import os

        os.environ["MLOPS_DEBUG"] = "true"
        os.environ["MLOPS_LOG_LEVEL"] = "DEBUG"

        try:
            settings = Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
            )

            assert settings.debug is True
            assert settings.log_level == "DEBUG"
        finally:
            os.environ.pop("MLOPS_DEBUG", None)
            os.environ.pop("MLOPS_LOG_LEVEL", None)
