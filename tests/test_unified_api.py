"""Tests for the unified API with the Strategy design pattern.

This module contains test cases to verify that the model backend selection
logic, the Strategy pattern implementation, and the unified API endpoints all
function correctly and consistently, regardless of the selected backend
(PyTorch or ONNX).
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings


@pytest.fixture
def mock_settings_pytorch(monkeypatch):
    """Provides mocked settings to configure the application for the PyTorch backend.

    Args:
        monkeypatch: The pytest `monkeypatch` fixture.

    Returns:
        A mocked `Settings` object configured for PyTorch.
    """
    settings = Settings(
        model_name="distilbert-base-uncased-finetuned-sst-2-english",
        onnx_model_path=None,  # No ONNX path = PyTorch
        enable_metrics=True,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.models.factory.get_settings", lambda: settings, raising=False)
    monkeypatch.setattr("app.core.dependencies.get_settings", lambda: settings, raising=False)
    return settings


@pytest.fixture
def mock_settings_onnx(monkeypatch):
    """Provides mocked settings to configure the application for the ONNX backend.

    Args:
        monkeypatch: The pytest `monkeypatch` fixture.

    Returns:
        A mocked `Settings` object configured for ONNX.
    """
    settings = Settings(
        model_name="distilbert-base-uncased-finetuned-sst-2-english",
        onnx_model_path="./onnx_models/test-model",
        onnx_model_path_default="./onnx_models/default-model",
        enable_metrics=True,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.models.factory.get_settings", lambda: settings, raising=False)
    monkeypatch.setattr("app.core.dependencies.get_settings", lambda: settings, raising=False)
    return settings


@pytest.mark.unit
@pytest.mark.strategy
class TestBackendSelection:
    """A test suite for the model backend selection logic.

    These tests verify that the `ModelFactory` correctly determines which
    backend to use based on the application's configuration.
    """

    def test_default_backend_without_onnx_path(self, mock_settings_pytorch):
        """Tests that the default backend is PyTorch when no ONNX path is configured."""
        from app.core.dependencies import get_model_backend

        backend = get_model_backend()
        assert backend == "pytorch"

    def test_default_backend_with_onnx_path(self, mock_settings_onnx):
        """Tests that the default backend is ONNX when an ONNX path is configured."""
        from app.core.dependencies import get_model_backend

        backend = get_model_backend()
        assert backend == "onnx"

    def test_explicit_backend_override(self, mock_settings_pytorch):
        """Tests that the `ModelFactory` can create a specific backend when requested explicitly."""
        from app.models.factory import ModelFactory

        # Test that factory can create different model types
        with patch("app.models.pytorch_sentiment.SentimentAnalyzer") as mock_sa:
            pytorch_model = ModelFactory.create_model("pytorch")
            assert pytorch_model is not None
            mock_sa.assert_called()


@pytest.mark.unit
@pytest.mark.strategy
class TestModelStrategy:
    """A test suite for the Model Strategy pattern implementation.

    These tests ensure that the `ModelFactory` correctly returns the
    appropriate analyzer instance (PyTorch or ONNX) for the chosen strategy.
    """

    def test_strategy_returns_pytorch_analyzer(self, mock_settings_pytorch, monkeypatch):
        """Tests that the factory returns a PyTorch analyzer for the 'pytorch' backend."""
        from app.models.factory import ModelFactory

        mock_analyzer = Mock()
        mock_analyzer.is_ready.return_value = True

        monkeypatch.setattr(
            "app.models.pytorch_sentiment.get_sentiment_analyzer", lambda: mock_analyzer
        )

        strategy = ModelFactory.create_model("pytorch")

        assert strategy is mock_analyzer

    def test_strategy_returns_onnx_analyzer(self, mock_settings_onnx, monkeypatch):
        """Tests that the factory returns an ONNX analyzer for the 'onnx' backend."""
        from app.models.factory import ModelFactory

        mock_analyzer = Mock()
        mock_analyzer.is_ready.return_value = True

        monkeypatch.setattr(
            "app.models.onnx_sentiment.get_onnx_sentiment_analyzer", lambda path: mock_analyzer
        )

        strategy = ModelFactory.create_model("onnx", model_path="./test-path")

        assert strategy is mock_analyzer

    def test_onnx_strategy_uses_default_path(self, mock_settings_onnx, monkeypatch):
        """Tests that the ONNX strategy uses the default ONNX model path when the main one is not provided."""
        from app.models.factory import ModelFactory

        # Set onnx_model_path to None
        mock_settings_onnx.onnx_model_path = None

        called_with_path = []

        def capture_path(path):
            called_with_path.append(path)
            mock = Mock()
            mock.is_ready.return_value = True
            return mock

        monkeypatch.setattr("app.models.onnx_sentiment.get_onnx_sentiment_analyzer", capture_path)

        ModelFactory.create_model("onnx", model_path=None)

        assert len(called_with_path) == 1
        assert called_with_path[0] == mock_settings_onnx.onnx_model_path_default


@pytest.mark.integration
@pytest.mark.strategy
class TestUnifiedAPIEndpoints:
    """An integration test suite for the unified API endpoints.

    These tests use mocked model strategies to verify that the API endpoints
    behave consistently regardless of the backend selected.
    """

    @pytest.fixture
    def client(self, mock_settings_pytorch, monkeypatch):
        """Creates a `TestClient` with a mocked model strategy.

        Args:
            mock_settings_pytorch: The PyTorch settings fixture.
            monkeypatch: The pytest `monkeypatch` fixture.

        Returns:
            A `TestClient` instance.
        """
        # Mock the strategy to avoid loading actual models
        mock_analyzer = Mock()
        mock_analyzer.get_model_status.return_value = {"is_ready": True}
        mock_analyzer.predict.return_value = {
            "label": "POSITIVE",
            "score": 0.95,
            "inference_time_ms": 25.5,
            "model_name": "test-model",
            "text_length": 9,
            "cached": False,
        }
        mock_analyzer.get_model_info.return_value = {
            "model_name": "test-model",
            "is_loaded": True,
            "is_ready": True,
        }
        mock_analyzer.get_performance_metrics.return_value = {
            "torch_version": "2.1.0",
            "cuda_available": False,
        }

        with patch("app.core.dependencies.get_prediction_service") as mock_get_service:
            mock_get_service.return_value = mock_analyzer
            from app.main import create_app

            app = create_app()
            yield TestClient(app)

    def test_predict_endpoint_success(self, client):
        """Tests that the `/predict` endpoint returns the expected successful response."""
        response = client.post(
            "/predict",
            json={"text": "Test text"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "sentiment" in data
        assert data["sentiment"]["label"] == "POSITIVE"
        assert data["sentiment"]["score"] == 0.95
        assert "cached" in data

    def test_predict_endpoint_with_backend_parameter(self, client):
        """Tests that the `/predict` endpoint correctly handles the 'backend' query parameter."""
        # This test confirms the parameter is present; the logic is tested at the unit level.
        response = client.post(
            "/predict?backend=pytorch",
            json={"text": "Test text"},
        )

        assert response.status_code == 200

    def test_predict_endpoint_adds_headers(self, client):
        """Tests that the `/predict` endpoint includes the correct custom headers in the response."""
        response = client.post(
            "/predict",
            json={"text": "Test text"},
        )

        assert "X-Inference-Time-MS" in response.headers
        assert "X-Model-Backend" in response.headers

    def test_health_endpoint(self, client):
        """Tests that the `/health` endpoint returns the expected healthy response."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["model_status"] == "available"
        assert "version" in data
        assert "timestamp" in data

    def test_model_info_endpoint(self, client):
        """Tests that the `/api/v1/info/model` endpoint returns the expected model information."""
        response = client.get("/api/v1/info/model")

        assert response.status_code == 200
        data = response.json()

        assert "model_name" in data
        assert "is_loaded" in data
        assert "is_ready" in data

    def test_metrics_json_endpoint(self, client):
        """Tests that the `/api/v1/metrics/json` endpoint returns the expected performance metrics."""
        response = client.get("/api/v1/metrics/json")

        assert response.status_code == 200
        data = response.json()

        assert "torch_version" in data
        assert "cuda_available" in data

    def test_predict_empty_text_validation(self, client):
        """Tests that the `/predict` endpoint correctly performs input validation for empty text."""
        response = client.post(
            "/predict",
            json={"text": ""},
        )

        # Should get validation error
        assert response.status_code == 400  # Custom validation error
        assert "TEXT_EMPTY" in response.json()["error_code"]


@pytest.mark.unit
@pytest.mark.strategy
class TestModelStrategyProtocol:
    """A test suite to ensure that all model analyzers conform to the `ModelStrategy` protocol.

    These tests verify that each concrete model implementation (PyTorch, ONNX)
    has the required methods defined by the `ModelStrategy` interface.
    """

    def test_pytorch_analyzer_implements_protocol(self):
        """Tests that `SentimentAnalyzer` correctly implements the `ModelStrategy` protocol."""
        from app.models.base import ModelStrategy
        from app.models.pytorch_sentiment import SentimentAnalyzer

        # Check that all required methods exist
        assert issubclass(SentimentAnalyzer, ModelStrategy)
        assert hasattr(SentimentAnalyzer, "is_ready")
        assert hasattr(SentimentAnalyzer, "predict")
        assert hasattr(SentimentAnalyzer, "get_model_info")
        assert hasattr(SentimentAnalyzer, "get_performance_metrics")

    def test_onnx_analyzer_implements_protocol(self):
        """Tests that `ONNXSentimentAnalyzer` correctly implements the `ModelStrategy` protocol."""
        from app.models.base import ModelStrategy
        from app.models.onnx_sentiment import ONNXSentimentAnalyzer

        # Check that all required methods exist
        assert issubclass(ONNXSentimentAnalyzer, ModelStrategy)
        assert hasattr(ONNXSentimentAnalyzer, "is_ready")
        assert hasattr(ONNXSentimentAnalyzer, "predict")
        assert hasattr(ONNXSentimentAnalyzer, "get_model_info")
        assert hasattr(ONNXSentimentAnalyzer, "get_performance_metrics")
