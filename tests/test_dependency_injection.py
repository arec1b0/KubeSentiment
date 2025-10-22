"""Tests for the dependency injection and service layer architecture.

This module contains test cases to verify that the service-based architecture
works as intended. It ensures proper separation of concerns between the model,
service, and API layers, and confirms that the dependency injection system
correctly provides service instances.
"""

from unittest.mock import Mock, patch

import pytest

from app.core.dependencies import get_prediction_service
from app.models.base import ModelStrategy

# Import for backward compatibility tests
from app.models.pytorch_sentiment import get_sentiment_analyzer
from app.services.prediction import PredictionService


class TestPredictionService:
    """A test suite for the `PredictionService` class.

    These tests verify the core business logic of the prediction service,
    ensuring it correctly handles successful predictions, input validation,
    and error conditions like the model not being ready.
    """

    def test_prediction_service_initialization(self):
        """Tests that the `PredictionService` initializes correctly with its dependencies."""
        mock_model = Mock(spec=ModelStrategy)
        mock_settings = Mock()

        service = PredictionService(model=mock_model, settings=mock_settings)

        assert service.model is mock_model
        assert service.settings is mock_settings
        assert hasattr(service, "logger")

    def test_predict_success(self):
        """Tests a successful prediction call through the service layer."""
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
        """Tests that providing empty or whitespace-only text raises an exception."""
        mock_model = Mock(spec=ModelStrategy)
        mock_settings = Mock()

        service = PredictionService(model=mock_model, settings=mock_settings)

        with pytest.raises(Exception):  # Should be TextEmptyError
            service.predict("")

        with pytest.raises(Exception):
            service.predict("   ")

    def test_predict_model_not_ready_raises_error(self):
        """Tests that an exception is raised if the model is not ready for prediction."""
        mock_model = Mock(spec=ModelStrategy)
        mock_model.is_ready.return_value = False
        mock_model.settings = Mock()
        mock_model.settings.model_name = "test-model"

        mock_settings = Mock()
        service = PredictionService(model=mock_model, settings=mock_settings)

        with pytest.raises(Exception):  # Should be ModelNotLoadedError
            service.predict("Some text")

    def test_get_model_status(self):
        """Tests the retrieval of the model's status through the service."""
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
    """A test suite for the dependency injection functions.

    These tests ensure that the functions in `app.core.dependencies`
    correctly create and provide instances of services.
    """

    @patch("app.models.factory.get_settings")
    @patch("app.models.pytorch_sentiment.pipeline")
    def test_get_prediction_service_integration(self, mock_pipeline, mock_get_settings):
        """Tests the `get_prediction_service` dependency provider.

        This test verifies that the function successfully creates a
        `PredictionService` instance with its dependencies resolved.
        """
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
        """Performs a basic sanity check on the `get_prediction_service` function."""
        # Basic sanity check that the function exists and is callable
        assert callable(get_prediction_service)
        assert get_prediction_service.__name__ == "get_prediction_service"


class TestTestingCapabilities:
    """A test suite to demonstrate the testability of the service-based architecture.

    These tests show how the separation of concerns allows for easy mocking
    and isolation of components during testing.
    """

    def test_can_mock_model_in_prediction_service(self):
        """Tests that the model dependency can be easily mocked for service-level tests."""
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
        """Tests that separate service instances can be created with different dependencies."""
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
        """Tests that the entire service can be mocked for API-level tests."""
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
    """A test suite for the `ModelFactory` and its integration with the service layer.

    These tests ensure that the model factory correctly creates different
    model backends based on the provided configuration.
    """

    @patch("app.models.factory.get_settings")
    @patch("app.models.pytorch_sentiment.pipeline")
    def test_model_factory_creates_pytorch_model(self, mock_pipeline, mock_get_settings):
        """Tests that the `ModelFactory` can successfully create a PyTorch model backend."""
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
        """Tests that requesting an unsupported backend from the factory raises a `ValueError`."""
        from app.models.factory import ModelFactory

        with pytest.raises(ValueError, match="Unsupported backend"):
            ModelFactory.create_model("invalid_backend")

    def test_model_factory_available_backends(self):
        """Tests that the factory correctly reports the list of available backends."""
        from app.models.factory import ModelFactory

        backends = ModelFactory.get_available_backends()

        # Should always include pytorch
        assert "pytorch" in backends

        # ONNX may or may not be available depending on installation
        # We don't assert on this since it varies by environment


class TestServiceLayerIntegration:
    """A test suite for the end-to-end integration of the service and model layers.

    This test verifies that the full dependency injection chain is wired
    correctly, from the top-level service provider down to the model creation.
    """

    @patch("app.models.factory.get_settings")
    @patch("app.models.pytorch_sentiment.pipeline")
    @patch("app.core.dependencies.get_settings")
    def test_full_dependency_chain(self, mock_core_settings, mock_pipeline, mock_factory_settings):
        """Tests the full dependency injection chain from service to model."""
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
