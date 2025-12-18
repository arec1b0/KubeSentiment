"""Test suite for FeatureEngineer dependency injection."""

import pytest
from unittest.mock import patch, MagicMock
from app.features.feature_engineering import get_feature_engineer, FeatureEngineer
import app.features.feature_engineering as fe_module

@pytest.mark.unit
class TestFeatureEngineerDI:
    """Tests for FeatureEngineer factory and initialization."""

    def setup_method(self):
        """Reset singleton before each test."""
        fe_module._feature_engineer_instance = None

    @patch("app.features.feature_engineering.FeatureEngineer._download_nltk_resources")
    def test_get_feature_engineer_defaults(self, mock_download):
        """Test default initialization downloads data."""
        fe = get_feature_engineer()
        assert isinstance(fe, FeatureEngineer)
        mock_download.assert_called_once()

    @patch("app.features.feature_engineering.FeatureEngineer._download_nltk_resources")
    def test_get_feature_engineer_no_download(self, mock_download):
        """Test initialization with download_nltk_data=False."""
        fe = get_feature_engineer(download_nltk_data=False)
        assert isinstance(fe, FeatureEngineer)
        mock_download.assert_not_called()

    @patch("app.features.feature_engineering.FeatureEngineer._download_nltk_resources")
    def test_singleton_pattern(self, mock_download):
        """Test that get_feature_engineer returns the same instance."""
        fe1 = get_feature_engineer(download_nltk_data=False)
        fe2 = get_feature_engineer(download_nltk_data=True) # Should be ignored
        
        assert fe1 is fe2
        # Should be called 0 times because first init was False, and second init didn't happen
        mock_download.assert_not_called()

