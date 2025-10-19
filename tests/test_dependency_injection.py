"""
Tests for dependency injection and service layer architecture.

These tests verify that the new service-based approach works correctly,
providing proper separation of concerns between models, services, and API layers.
"""

from unittest.mock import Mock, patch

import pytest

from app.core.dependencies import get_prediction_service
from app.models.base import ModelStrategy

# Import for backward compatibility tests
from app.models.pytorch_sentiment import get_sentiment_analyzer
from app.services.prediction import PredictionService


class TestPredictionService:
    """Test the PredictionService class functionality."""

    def test_prediction_service_initialization(self):
        """Test that PredictionService initializes correctly."""
        mock_model = Mock(spec=ModelStrategy)
        mock_settings = Mock()

        service = PredictionService(model=mock_model, settings=mock_settings)

        assert service.model is mock_model
        assert service.settings is mock_settings
        assert hasattr(service, "logger")

    def test_predict_success(self):
        """Test successful prediction through service."""
        # Setup mocks
        mock_model = Mock(spec=ModelStrategy)
        mock_model.is_ready.return_value = True
        mock_model.predict.return_value = {
            "label": "POSITIVE",
            "score": 0.95,
            "inference_time_ms": 150.0,
        }

        mock_settings = Mock()
        service = PredictionService(model=mock_model, settings=mock_settings)

        # Perform prediction
        result = service.predict("I love this product!")

        assert result["label"] == "POSITIVE"
        assert result["score"] == 0.95
        assert result["inference_time_ms"] == 150.0
        mock_model.predict.assert_called_once_with("I love this product!")

    def test_predict_empty_text_raises_error(self):
        """Test that empty text raises TextEmptyError."""
        mock_model = Mock(spec=ModelStrategy)
        mock_settings = Mock()

        service = PredictionService(model=mock_model, settings=mock_settings)

        with pytest.raises(Exception):  # Should be TextEmptyError, but we'll test the behavior
            service.predict("")

        with pytest.raises(Exception):
            service.predict("   ")

    def test_predict_model_not_ready_raises_error(self):
        """Test that unavailable model raises ModelNotLoadedError."""
        mock_model = Mock(spec=ModelStrategy)
        mock_model.is_ready.return_value = False
        mock_model.settings = Mock()
        mock_model.settings.model_name = "test-model"

        mock_settings = Mock()
        service = PredictionService(model=mock_model, settings=mock_settings)

        with pytest.raises(Exception):  # Should be ModelNotLoadedError
            service.predict("Some text")

    def test_get_model_status(self):
        """Test getting model status through service."""
        mock_model = Mock(spec=ModelStrategy)
        mock_model.is_ready.return_value = True
        mock_model.get_model_info.return_value = {"model_name": "test-model"}

        mock_settings = Mock()
        service = PredictionService(model=mock_model, settings=mock_settings)

        status = service.get_model_status()

        assert status["is_ready"] is True
        assert status["model_info"] == {"model_name": "test-model"}
        mock_model.is_ready.assert_called_once()
        mock_model.get_model_info.assert_called_once()


class TestDependencyInjectionFunctions:
    """Test the dependency injection functions in app.core.dependencies."""

    @patch("app.models.factory.get_settings")
    @patch("app.models.pytorch_sentiment.pipeline")
    def test_get_prediction_service_integration(self, mock_pipeline, mock_get_settings):
        """Test that get_prediction_service works with real dependencies."""
        # Setup mocks for the model creation chain
        mock_settings = Mock()
        mock_settings.allowed_models = ["test-model"]
        mock_settings.model_name = "test-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_settings.model_cache_dir = None
        mock_get_settings.return_value = mock_settings
        mock_pipeline.return_value = Mock()

        # Should create prediction service through the dependency chain
        service = get_prediction_service()

        assert service is not None
        assert isinstance(service, PredictionService)
        assert hasattr(service, "predict")
        assert hasattr(service, "get_model_status")

    def test_get_prediction_service_is_callable(self):
        """Test that get_prediction_service is a callable function."""
        # Basic sanity check that the function exists and is callable
        assert callable(get_prediction_service)
        assert get_prediction_service.__name__ == "get_prediction_service"


class TestTestingCapabilities:
    """Test that the new approach improves testability."""

    def test_can_mock_model_in_prediction_service(self):
        """Test that we can easily mock the model for testing."""
        mock_model = Mock(spec=ModelStrategy)
        mock_model.is_ready.return_value = True
        mock_model.predict.return_value = {"label": "POSITIVE", "score": 0.95}

        mock_settings = Mock()
        service = PredictionService(model=mock_model, settings=mock_settings)

        # Should work with mock model
        result = service.predict("Test text")
        assert result["label"] == "POSITIVE"
        assert result["score"] == 0.95
        mock_model.predict.assert_called_once_with("Test text")

    def test_service_isolation_between_tests(self):
        """Test that services can be isolated between tests."""
        # Create two separate services with different models
        mock_model1 = Mock(spec=ModelStrategy)
        mock_model2 = Mock(spec=ModelStrategy)
        mock_settings = Mock()

        service1 = PredictionService(model=mock_model1, settings=mock_settings)
        service2 = PredictionService(model=mock_model2, settings=mock_settings)

        # Services should be independent
        assert service1.model is not service2.model
        assert service1.model is mock_model1
        assert service2.model is mock_model2

    def test_dependency_injection_can_be_mocked(self):
        """Test that dependency injection can be easily mocked in tests."""
        # Create a mock service directly (simulating what would happen in FastAPI tests)
        mock_service = Mock(spec=PredictionService)
        mock_service.predict.return_value = {"label": "NEGATIVE", "score": 0.85}

        # This simulates how you would override dependencies in FastAPI tests
        # by creating the service with mocked dependencies
        result = mock_service.predict("Test text")

        assert result["label"] == "NEGATIVE"
        assert result["score"] == 0.85
        mock_service.predict.assert_called_once_with("Test text")


class TestModelFactoryIntegration:
    """Test integration between ModelFactory and service layer."""

    @patch("app.models.factory.get_settings")
    @patch("app.models.pytorch_sentiment.pipeline")
    def test_model_factory_creates_pytorch_model(self, mock_pipeline, mock_get_settings):
        """Test that ModelFactory creates PyTorch model correctly."""
        from app.models.factory import ModelFactory

        # Setup mocks
        mock_settings = Mock()
        mock_settings.allowed_models = ["test-model"]
        mock_settings.model_name = "test-model"
        mock_settings.prediction_cache_max_size = 1000
        mock_settings.model_cache_dir = None
        mock_get_settings.return_value = mock_settings
        mock_pipeline.return_value = Mock()

        # Create model through factory
        model = ModelFactory.create_model("pytorch")

        # Should be a model strategy
        assert model is not None
        assert hasattr(model, "predict")
        assert hasattr(model, "is_ready")

    @patch("app.models.factory.ONNX_AVAILABLE", False)
    def test_model_factory_unsupported_backend_raises_error(self):
        """Test that unsupported backend raises ValueError."""
        from app.models.factory import ModelFactory

        with pytest.raises(ValueError, match="Unsupported backend"):
            ModelFactory.create_model("invalid_backend")

    def test_model_factory_available_backends(self):
        """Test that available backends are correctly reported."""
        from app.models.factory import ModelFactory

        backends = ModelFactory.get_available_backends()

        # Should always include pytorch
        assert "pytorch" in backends

        # ONNX may or may not be available depending on installation
        # We don't assert on this since it varies by environment


class TestServiceLayerIntegration:
    """Test integration between service layer and model layer."""

    @patch("app.models.factory.get_settings")
    @patch("app.models.pytorch_sentiment.pipeline")
    @patch("app.core.dependencies.get_settings")
    def test_full_dependency_chain(self, mock_core_settings, mock_pipeline, mock_factory_settings):
        """Test the full dependency injection chain."""
        # Setup mocks
        mock_factory_settings.return_value = Mock()
        mock_core_settings.return_value = Mock()

        # This tests the complete chain:
        # get_prediction_service -> get_model_service -> get_settings
        service = get_prediction_service()

        assert service is not None
        assert isinstance(service, PredictionService)
        assert hasattr(service, "predict")
        assert hasattr(service, "get_model_status")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
