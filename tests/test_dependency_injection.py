"""
Tests for dependency injection refactoring of the sentiment analyzer.

These tests verify that the new service-based approach works correctly
and provides better testability than the global singleton pattern.
"""

import pytest
from unittest.mock import Mock, patch

from app.ml.sentiment import (
    SentimentAnalyzer,
    SentimentAnalyzerService,
    get_sentiment_analyzer,
    get_analyzer_service,
)


class TestSentimentAnalyzerService:
    """Test the new service-based dependency injection approach."""

    @patch("app.ml.sentiment.get_settings")
    @patch("app.ml.sentiment.pipeline")
    def test_service_creates_analyzer_on_first_call(
        self, mock_pipeline, mock_get_settings
    ):
        """Test that service creates analyzer on first call."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.allowed_models = ["test-model"]
        mock_settings.model_name = "test-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_settings.model_cache_dir = None
        mock_get_settings.return_value = mock_settings
        mock_pipeline.return_value = Mock()

        service = SentimentAnalyzerService()

        # First call should create analyzer
        analyzer1 = service.get_analyzer()
        assert analyzer1 is not None
        assert isinstance(analyzer1, SentimentAnalyzer)

        # Second call should return same instance
        analyzer2 = service.get_analyzer()
        assert analyzer1 is analyzer2

    @patch("app.ml.sentiment.get_settings")
    @patch("app.ml.sentiment.pipeline")
    def test_service_reset_clears_analyzer(self, mock_pipeline, mock_get_settings):
        """Test that service reset clears the analyzer."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.allowed_models = ["test-model"]
        mock_settings.model_name = "test-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_settings.model_cache_dir = None
        mock_get_settings.return_value = mock_settings
        mock_pipeline.return_value = Mock()

        service = SentimentAnalyzerService()

        # Create analyzer
        analyzer1 = service.get_analyzer()

        # Reset service
        service.reset_analyzer()

        # Get analyzer again - should be a new instance
        analyzer2 = service.get_analyzer()
        assert analyzer1 is not analyzer2

    def test_service_initialization(self):
        """Test service initialization state."""
        service = SentimentAnalyzerService()

        assert service._analyzer is None
        assert service._initialized is False


class TestDependencyInjectionFunctions:
    """Test the dependency injection functions."""

    @patch("app.ml.sentiment._analyzer_service", None)
    @patch("app.ml.sentiment.get_settings")
    @patch("app.ml.sentiment.pipeline")
    def test_get_sentiment_analyzer_creates_service(
        self, mock_pipeline, mock_get_settings
    ):
        """Test that get_sentiment_analyzer creates service if needed."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.allowed_models = ["test-model"]
        mock_settings.model_name = "test-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_settings.model_cache_dir = None
        mock_get_settings.return_value = mock_settings
        mock_pipeline.return_value = Mock()

        # Should create new service and analyzer
        analyzer = get_sentiment_analyzer()
        assert analyzer is not None
        assert isinstance(analyzer, SentimentAnalyzer)

    @patch("app.ml.sentiment._analyzer_service", None)
    def test_get_analyzer_service_creates_service(self):
        """Test that get_analyzer_service creates service if needed."""
        service = get_analyzer_service()
        assert service is not None
        assert isinstance(service, SentimentAnalyzerService)

    @patch("app.ml.sentiment._analyzer_service", None)
    @patch("app.ml.sentiment.get_settings")
    @patch("app.ml.sentiment.pipeline")
    def test_multiple_calls_return_same_analyzer(
        self, mock_pipeline, mock_get_settings
    ):
        """Test that multiple calls return the same analyzer instance."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.allowed_models = ["test-model"]
        mock_settings.model_name = "test-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_settings.model_cache_dir = None
        mock_get_settings.return_value = mock_settings
        mock_pipeline.return_value = Mock()

        analyzer1 = get_sentiment_analyzer()
        analyzer2 = get_sentiment_analyzer()

        # Should be the same instance
        assert analyzer1 is analyzer2


class TestTestingCapabilities:
    """Test that the new approach improves testability."""

    @patch("app.ml.sentiment.get_settings")
    @patch("app.ml.sentiment.pipeline")
    def test_can_mock_analyzer_in_service(self, mock_pipeline, mock_get_settings):
        """Test that we can easily mock the analyzer for testing."""
        service = SentimentAnalyzerService()

        # Create mock analyzer
        mock_analyzer = Mock(spec=SentimentAnalyzer)
        mock_analyzer.is_ready.return_value = True
        mock_analyzer.predict.return_value = {"label": "POSITIVE", "score": 0.95}

        # Inject mock analyzer
        service._analyzer = mock_analyzer
        service._initialized = True

        # Should return mock analyzer
        analyzer = service.get_analyzer()
        assert analyzer is mock_analyzer
        assert analyzer.is_ready() is True

    @patch("app.ml.sentiment.get_settings")
    @patch("app.ml.sentiment.pipeline")
    def test_service_isolation_between_tests(self, mock_pipeline, mock_get_settings):
        """Test that services can be isolated between tests."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.allowed_models = ["test-model"]
        mock_settings.model_name = "test-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_settings.model_cache_dir = None
        mock_get_settings.return_value = mock_settings
        mock_pipeline.return_value = Mock()

        # Create two separate services
        service1 = SentimentAnalyzerService()
        service2 = SentimentAnalyzerService()

        analyzer1 = service1.get_analyzer()
        analyzer2 = service2.get_analyzer()

        # Should be different instances
        assert analyzer1 is not analyzer2


class TestBackwardCompatibility:
    """Test that existing code continues to work."""

    @patch("app.ml.sentiment._analyzer_service", None)
    @patch("app.ml.sentiment.get_settings")
    @patch("app.ml.sentiment.pipeline")
    def test_existing_get_sentiment_analyzer_still_works(
        self, mock_pipeline, mock_get_settings
    ):
        """Test that existing usage of get_sentiment_analyzer still works."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.allowed_models = ["test-model"]
        mock_settings.model_name = "test-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_settings.model_cache_dir = None
        mock_get_settings.return_value = mock_settings
        mock_pipeline.return_value = Mock()

        # This is how existing code uses the function
        analyzer = get_sentiment_analyzer()

        # Should work exactly as before
        assert analyzer is not None
        assert hasattr(analyzer, "predict")
        assert hasattr(analyzer, "is_ready")

    @patch("app.ml.sentiment._analyzer_service", None)
    @patch("app.ml.sentiment.get_settings")
    @patch("app.ml.sentiment.pipeline")
    def test_singleton_behavior_preserved(self, mock_pipeline, mock_get_settings):
        """Test that singleton behavior is preserved."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.allowed_models = ["test-model"]
        mock_settings.model_name = "test-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_settings.model_cache_dir = None
        mock_get_settings.return_value = mock_settings
        mock_pipeline.return_value = Mock()

        # Multiple calls should return same instance (singleton behavior)
        analyzer1 = get_sentiment_analyzer()
        analyzer2 = get_sentiment_analyzer()
        analyzer3 = get_sentiment_analyzer()

        assert analyzer1 is analyzer2
        assert analyzer2 is analyzer3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
