"""Test suite for CORS configuration deprecation."""

import pytest
import warnings
from app.core.config.settings import Settings

@pytest.mark.unit
class TestCorsDeprecation:
    """Test suite for verifying cors_origins deprecation warnings."""

    def test_cors_origins_getter_emits_warning(self):
        """Test that accessing cors_origins getter emits a DeprecationWarning."""
        settings = Settings()
        
        with pytest.warns(DeprecationWarning, match="cors_origins is deprecated"):
            _ = settings.cors_origins

    def test_cors_origins_setter_emits_warning_and_updates_canonical(self):
        """Test that setting cors_origins emits warning and updates allowed_origins."""
        settings = Settings()
        new_origins = ["https://example.com"]
        
        with pytest.warns(DeprecationWarning, match="cors_origins is deprecated"):
            settings.cors_origins = new_origins
            
        # Verify canonical field is updated (canonical path is security.allowed_origins)
        assert settings.security.allowed_origins == new_origins
        
        # Verify alias reflects the change (suppressing warning for this check)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert settings.cors_origins == new_origins
