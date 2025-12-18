"""Test suite for map_legacy_fields validator in Settings class."""

import pytest
from app.core.config.settings import Settings
from app.core.config.model import ModelConfig

@pytest.mark.unit
class TestSettingsLegacyMapping:
    """Test suite for map_legacy_fields edge cases."""

    def test_empty_dict(self):
        """Test that passing an empty dict works without side effects."""
        # Using map_legacy_fields directly
        values = {}
        result = Settings.map_legacy_fields(values)
        assert result == {}
        
        # Initializing Settings with no args
        settings = Settings()
        assert settings.server.debug is False  # default

    def test_none_values(self):
        """Test that None values are mapped correctly."""
        # We need to test if None is propagated.
        # However, fields like 'debug' (bool) might fail Pydantic validation if None is passed.
        # But 'model_name' is str, let's try that.
        # Or a field that is Optional. 'onnx_model_path' is Optional[str].
        
        # Case 1: passing None for an optional field
        values = {"onnx_model_path": None}
        result = Settings.map_legacy_fields(values)
        assert "onnx_model_path" not in result
        assert result["model"]["onnx_model_path"] is None
        
        # Settings instantiation should work
        settings = Settings(onnx_model_path=None)
        assert settings.model.onnx_model_path is None

    def test_domain_model_instance_preserved(self):
        """Test that if a domain model is already instantiated, legacy fields are ignored/popped."""
        custom_model_config = ModelConfig(model_name="original-model")
        
        # We pass both an instantiated domain config AND a legacy override
        values = {
            "model": custom_model_config,
            "model_name": "legacy-override-attempt"
        }
        
        result = Settings.map_legacy_fields(values)
        
        # Expect legacy key to be removed
        assert "model_name" not in result
        # Expect domain model to be untouched (still the instance)
        assert result["model"] is custom_model_config
        assert result["model"].model_name == "original-model"
        
        # Verify with Settings instantiation
        # Note: validation will run after this. 
        # But since Settings(model=...) works, let's check.
        # Pydantic might re-validate the model instance, but values should hold the instance.
        
        # Constructing Settings with pre-built model config
        settings = Settings(
            model=custom_model_config,
            model_name="should-be-ignored"
        )
        assert settings.model.model_name == "original-model"

    def test_legacy_field_override(self):
        """Test normal override works."""
        settings = Settings(model_name="new-model-name")
        assert settings.model.model_name == "new-model-name"

    def test_mixed_dict_and_legacy(self):
        """Test mixing nested dict and legacy field works and merges."""
        # User provides partial model dict and a legacy arg
        # map_legacy_fields should merge them
        values = {
            "model": {"max_text_length": 128},
            "model_name": "merged-model-name"
        }
        
        result = Settings.map_legacy_fields(values)
        
        assert result["model"]["max_text_length"] == 128
        assert result["model"]["model_name"] == "merged-model-name"
        
        settings = Settings(
            model={"max_text_length": 128},
            model_name="merged-model-name"
        )
        assert settings.model.max_text_length == 128
        assert settings.model.model_name == "merged-model-name"

    def test_non_dict_input(self):
        """Test that non-dict input is returned as is."""
        values = "not-a-dict"
        result = Settings.map_legacy_fields(values)
        assert result == "not-a-dict"

