"""Test suite for settings property setters."""

import pytest
from app.core.config.settings import Settings

@pytest.mark.unit
class TestSettingsSetters:
    """Test suite for verifying that legacy property setters update nested configs."""

    def test_debug_setter(self):
        settings = Settings(debug=False)
        assert settings.server.debug is False
        settings.debug = True
        assert settings.server.debug is True
        assert settings.debug is True

    def test_log_level_setter(self):
        settings = Settings(log_level="INFO")
        assert settings.monitoring.log_level == "INFO"
        settings.log_level = "DEBUG"
        assert settings.monitoring.log_level == "DEBUG"
        assert settings.log_level == "DEBUG"

    def test_model_name_setter(self):
        settings = Settings(model_name="old-model")
        assert settings.model.model_name == "old-model"
        settings.model_name = "new-model"
        assert settings.model.model_name == "new-model"
        assert settings.model_name == "new-model"

    def test_onnx_model_path_setter(self):
        settings = Settings(onnx_model_path=None)
        assert settings.model.onnx_model_path is None
        settings.onnx_model_path = "/path/to/model"
        assert settings.model.onnx_model_path == "/path/to/model"
        assert settings.onnx_model_path == "/path/to/model"

    def test_host_setter(self):
        settings = Settings(host="0.0.0.0")
        assert settings.server.host == "0.0.0.0"
        settings.host = "127.0.0.1"
        assert settings.server.host == "127.0.0.1"
        assert settings.host == "127.0.0.1"

    def test_port_setter(self):
        settings = Settings(port=8000)
        assert settings.server.port == 8000
        settings.port = 9090
        assert settings.server.port == 9090
        assert settings.port == 9090

    def test_allowed_origins_setter(self):
        settings = Settings(allowed_origins=["*"])
        assert settings.security.allowed_origins == ["*"]
        settings.allowed_origins = ["https://example.com"]
        assert settings.security.allowed_origins == ["https://example.com"]
        assert settings.allowed_origins == ["https://example.com"]

    def test_cors_origins_setter_syncs_allowed_origins(self):
        settings = Settings(cors_origins=["*"])
        assert settings.security.allowed_origins == ["*"]
        settings.cors_origins = ["https://example.com"]
        assert settings.security.allowed_origins == ["https://example.com"]
        assert settings.cors_origins == ["https://example.com"]
        assert settings.allowed_origins == ["https://example.com"]

    def test_api_key_setter(self):
        settings = Settings(api_key="old-key")
        assert settings.security.api_key == "old-key"
        settings.api_key = "new-key"
        assert settings.security.api_key == "new-key"
        assert settings.api_key == "new-key"

    def test_kafka_enabled_setter(self):
        settings = Settings(kafka_enabled=False)
        assert settings.kafka.kafka_enabled is False
        settings.kafka_enabled = True
        assert settings.kafka.kafka_enabled is True
        assert settings.kafka_enabled is True

    def test_redis_enabled_setter(self):
        settings = Settings(redis_enabled=False)
        assert settings.redis.redis_enabled is False
        settings.redis_enabled = True
        assert settings.redis.redis_enabled is True
        assert settings.redis_enabled is True
