"""Tests for Pydantic setting validators in `app.core.config`.

This module contains test cases for the custom validators and properties
defined in the `Settings` class. It ensures that the configuration logic is
robust and correctly handles valid and invalid inputs.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.unit
class TestConfigValidators:
    """A test suite for the individual validator methods in the `Settings` class.

    These tests verify that each custom validation method behaves as expected,
    raising `ValidationError` for invalid configurations and passing for
    valid ones.
    """

    def test_validate_model_in_allowed_list_success(self):
        """Tests that model validation passes when the model is in the allowed list."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            allowed_models=[
                "distilbert-base-uncased-finetuned-sst-2-english",
                "other-model",
            ],
        )
        # Should not raise an exception.
        settings._validate_model_in_allowed_list()

    def test_validate_model_in_allowed_list_failure(self):
        """Tests that model validation fails if the model is not in the allowed list."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="unauthorized-model",
                allowed_models=["allowed-model-1", "allowed-model-2"],
            )

        assert "must be in allowed_models list" in str(exc_info.value)

    def test_validate_worker_count_consistency_debug_mode(self):
        """Tests that validation fails if multiple workers are set in debug mode."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
                debug=True,
                workers=4,
            )

        assert "Cannot use multiple workers in debug mode" in str(exc_info.value)

    def test_validate_worker_count_consistency_production(self):
        """Tests that validation passes with multiple workers in production mode."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            debug=False,
            workers=4,
        )
        # Should not raise an exception.
        settings._validate_worker_count_consistency()

    def test_validate_cache_memory_usage_within_limits(self):
        """Tests that cache memory validation passes when usage is within limits."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            prediction_cache_max_size=1000,
            max_text_length=512,
        )
        # Should not raise an exception.
        settings._validate_cache_memory_usage()

    def test_validate_cache_memory_usage_exceeds_limits(self):
        """Tests that cache memory validation fails if the estimated usage is too high."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
                prediction_cache_max_size=100000,  # Large cache
                max_text_length=10000,  # Large text
            )

        assert "may use too much memory" in str(exc_info.value)

    def test_cors_origins_validation_rejects_wildcard(self):
        """Tests that CORS validation fails if a wildcard origin `"*"` is used."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
                allowed_origins=["*"],
            )

        assert "Wildcard CORS origin" in str(exc_info.value)

    def test_cors_origins_validation_accepts_explicit_origins(self):
        """Tests that CORS validation passes with a list of explicit origins."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            allowed_origins=["https://example.com", "https://api.example.com"],
        )
        assert len(settings.allowed_origins) == 2

    def test_api_key_validation_requires_minimum_length(self):
        """Tests that API key validation fails if the key is too short."""
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
        """Tests that API key validation fails if the key lacks complexity."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
                api_key="onlyletters",
            )

        assert "must contain both letters and numbers" in str(exc_info.value)

    def test_api_key_validation_passes_with_valid_key(self):
        """Tests that API key validation passes for a valid, complex key."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            api_key="ValidKey123",
        )
        assert settings.api_key == "ValidKey123"

    def test_onnx_model_path_default_field(self):
        """Tests that the `onnx_model_path_default` field is correctly generated."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
        )
        assert hasattr(settings, "onnx_model_path_default")
        assert settings.onnx_model_path_default.endswith(
            "distilbert-base-uncased-finetuned-sst-2-english"
        )


@pytest.mark.unit
class TestConfigFieldValidators:
    """A test suite for the Pydantic `field_validator` decorators.

    These tests ensure that validators attached directly to fields in the
    `Settings` model correctly validate format, length, and other constraints.
    """

    def test_allowed_models_format_validation(self):
        """Tests that the `allowed_models` validator rejects invalid model name formats."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="test",
                allowed_models=["invalid@model#name", "test"],
            )

        assert "Invalid model name format" in str(exc_info.value)

    def test_allowed_models_length_validation(self):
        """Tests that the `allowed_models` validator rejects overly long model names."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="test",
                allowed_models=["a" * 250, "test"],  # Too long
            )

        assert "Model name too long" in str(exc_info.value)

    def test_cors_origins_url_format_validation(self):
        """Tests that the `allowed_origins` validator rejects invalid URL formats."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                model_name="distilbert-base-uncased-finetuned-sst-2-english",
                allowed_origins=["not-a-valid-url"],
            )

        assert "Invalid CORS origin URL" in str(exc_info.value)

    def test_cors_origins_accepts_http_and_https(self):
        """Tests that the `allowed_origins` validator accepts various valid URL schemes."""
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
    """A test suite for the computed properties of the `Settings` class.

    These tests verify that computed properties and configurations derived
    from other settings (like environment variable prefixes) are working correctly.
    """

    def test_cors_origins_property(self):
        """Tests that the `cors_origins` property correctly returns `allowed_origins`."""
        settings = Settings(
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            allowed_origins=["https://example.com"],
        )
        assert settings.cors_origins == settings.allowed_origins

    def test_config_env_prefix(self):
        """Tests that the Pydantic settings model correctly uses the 'MLOPS_' prefix for environment variables."""
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


@pytest.mark.unit
class TestDomainConfigs:
    """Test suite for domain-specific configuration classes."""

    def test_server_config_domain_access(self):
        """Test accessing server settings through domain config."""
        from app.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "server")
        assert settings.server.host is not None
        assert settings.server.port > 0
        assert isinstance(settings.server.port, int)

    def test_model_config_domain_access(self):
        """Test accessing model settings through domain config."""
        from app.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "model")
        assert settings.model.model_name is not None
        assert isinstance(settings.model.max_text_length, int)

    def test_kafka_config_domain_access(self):
        """Test accessing Kafka settings through domain config."""
        from app.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "kafka")
        assert isinstance(settings.kafka.kafka_enabled, bool)
        assert isinstance(settings.kafka.kafka_bootstrap_servers, list)

    def test_redis_config_domain_access(self):
        """Test accessing Redis settings through domain config."""
        from app.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "redis")
        assert isinstance(settings.redis.redis_enabled, bool)
        assert isinstance(settings.redis.redis_port, int)

    def test_all_domain_configs_present(self):
        """Test that all expected domain configs are present."""
        from app.core.config import Settings

        settings = Settings()
        expected_domains = [
            "server",
            "model",
            "security",
            "performance",
            "kafka",
            "redis",
            "vault",
            "data_lake",
            "monitoring",
            "mlops",
        ]

        for domain in expected_domains:
            assert hasattr(settings, domain), f"Missing domain config: {domain}"


@pytest.mark.unit
class TestBackwardCompatibility:
    """Test suite for backward compatibility properties."""

    def test_model_name_backward_compatibility(self):
        """Test that model_name property works for backward compatibility."""
        from app.core.config import Settings

        settings = Settings()
        # Old style access
        model_name_old = settings.model_name
        # New style access
        model_name_new = settings.model.model_name

        assert model_name_old == model_name_new

    def test_kafka_enabled_backward_compatibility(self):
        """Test that kafka_enabled property works for backward compatibility."""
        from app.core.config import Settings

        settings = Settings()
        # Old style access
        kafka_enabled_old = settings.kafka_enabled
        # New style access
        kafka_enabled_new = settings.kafka.kafka_enabled

        assert kafka_enabled_old == kafka_enabled_new

    def test_redis_enabled_backward_compatibility(self):
        """Test that redis_enabled property works for backward compatibility."""
        from app.core.config import Settings

        settings = Settings()
        # Old style access
        redis_enabled_old = settings.redis_enabled
        # New style access
        redis_enabled_new = settings.redis.redis_enabled

        assert redis_enabled_old == redis_enabled_new

    def test_port_backward_compatibility(self):
        """Test that port property works for backward compatibility."""
        from app.core.config import Settings

        settings = Settings()
        # Old style access
        port_old = settings.port
        # New style access
        port_new = settings.server.port

        assert port_old == port_new

    def test_debug_backward_compatibility(self):
        """Test that debug property works for backward compatibility."""
        from app.core.config import Settings

        settings = Settings()
        # Old style access
        debug_old = settings.debug
        # New style access
        debug_new = settings.server.debug

        assert debug_old == debug_new


@pytest.mark.unit
class TestProfileLoading:
    """Test suite for profile-based configuration loading."""

    def test_profile_defaults_applied(self):
        """Test that profile defaults are applied correctly."""
        import os

        from app.core.config import Settings

        # Set profile
        os.environ["MLOPS_PROFILE"] = "local"

        try:
            settings = Settings()
            # Local profile should have debug enabled
            assert settings.server.debug is True
            assert settings.server.environment == "local"
        finally:
            os.environ.pop("MLOPS_PROFILE", None)

    def test_profile_override_with_env_var(self):
        """Test that environment variables override profile defaults."""
        import os

        from app.core.config import Settings

        os.environ["MLOPS_PROFILE"] = "local"
        os.environ["MLOPS_DEBUG"] = "false"  # Override profile default

        try:
            settings = Settings()
            # Environment variable should override profile default
            assert settings.server.debug is False
        finally:
            os.environ.pop("MLOPS_PROFILE", None)
            os.environ.pop("MLOPS_DEBUG", None)

    def test_production_profile_defaults(self):
        """Test production profile applies correct defaults."""
        import os

        from app.core.config import Settings

        os.environ["MLOPS_PROFILE"] = "production"

        try:
            settings = Settings()
            # Production profile should have debug disabled
            assert settings.server.debug is False
            assert settings.server.environment == "production"
            # Production should enable more services
            assert settings.redis.redis_enabled is True
        finally:
            os.environ.pop("MLOPS_PROFILE", None)


@pytest.mark.unit
class TestConfigurationInheritance:
    """Test suite for configuration inheritance and composition."""

    def test_settings_composes_all_domains(self):
        """Test that Settings class composes all domain configs."""
        from app.core.config import Settings

        settings = Settings()

        # Verify all domains are composed
        assert settings.server is not None
        assert settings.model is not None
        assert settings.kafka is not None
        assert settings.redis is not None
        assert settings.vault is not None
        assert settings.security is not None
        assert settings.performance is not None
        assert settings.data_lake is not None
        assert settings.monitoring is not None
        assert settings.mlops is not None

    def test_domain_configs_are_independent(self):
        """Test that domain configs can be accessed independently."""
        from app.core.config import ModelConfig, ServerConfig, Settings

        settings = Settings()

        # Domain configs should be independent instances
        assert isinstance(settings.server, ServerConfig)
        assert isinstance(settings.model, ModelConfig)
        assert settings.server is not settings.model
        assert isinstance(settings.server, ServerConfig)
        assert isinstance(settings.model, ModelConfig)
        assert settings.server is not settings.model
