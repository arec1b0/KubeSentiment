"""
Tests for unified API with strategy pattern.

Tests verify backend selection, strategy pattern implementation, and API consistency.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.config import Settings


@pytest.fixture
def mock_settings_pytorch(monkeypatch):
    """Mock settings for PyTorch backend."""
    settings = Settings(
        model_name="distilbert-base-uncased-finetuned-sst-2-english",
        onnx_model_path=None,  # No ONNX path = PyTorch
        enable_metrics=True,
    )
    monkeypatch.setattr("app.unified_api.get_settings", lambda: settings)
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    return settings


@pytest.fixture
def mock_settings_onnx(monkeypatch):
    """Mock settings for ONNX backend."""
    settings = Settings(
        model_name="distilbert-base-uncased-finetuned-sst-2-english",
        onnx_model_path="./onnx_models/test-model",
        onnx_model_path_default="./onnx_models/default-model",
        enable_metrics=True,
    )
    monkeypatch.setattr("app.unified_api.get_settings", lambda: settings)
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    return settings


@pytest.mark.unit
@pytest.mark.strategy
class TestBackendSelection:
    """Test model backend selection logic."""

    def test_default_backend_without_onnx_path(self, mock_settings_pytorch):
        """Test default backend is PyTorch when no ONNX path configured."""
        from app.unified_api import get_model_backend, ModelBackend

        backend = get_model_backend()
        assert backend == ModelBackend.PYTORCH

    def test_default_backend_with_onnx_path(self, mock_settings_onnx):
        """Test default backend is ONNX when ONNX path configured."""
        from app.unified_api import get_model_backend, ModelBackend

        backend = get_model_backend()
        assert backend == ModelBackend.ONNX

    def test_explicit_backend_override(self, mock_settings_pytorch):
        """Test explicit backend parameter overrides default."""
        from app.unified_api import get_model_backend, ModelBackend

        backend = get_model_backend(backend="onnx")
        assert backend == "onnx"

        backend = get_model_backend(backend="pytorch")
        assert backend == "pytorch"


@pytest.mark.unit
@pytest.mark.strategy
class TestModelStrategy:
    """Test model strategy pattern implementation."""

    def test_strategy_returns_pytorch_analyzer(
        self, mock_settings_pytorch, monkeypatch
    ):
        """Test strategy returns PyTorch analyzer for pytorch backend."""
        from app.unified_api import get_model_strategy, ModelBackend

        mock_analyzer = Mock()
        mock_analyzer.is_ready.return_value = True

        monkeypatch.setattr(
            "app.unified_api.get_sentiment_analyzer", lambda: mock_analyzer
        )

        strategy = get_model_strategy(
            backend=ModelBackend.PYTORCH, settings=mock_settings_pytorch
        )

        assert strategy == mock_analyzer

    def test_strategy_returns_onnx_analyzer(self, mock_settings_onnx, monkeypatch):
        """Test strategy returns ONNX analyzer for onnx backend."""
        from app.unified_api import get_model_strategy, ModelBackend

        mock_analyzer = Mock()
        mock_analyzer.is_ready.return_value = True

        monkeypatch.setattr(
            "app.unified_api.get_onnx_sentiment_analyzer", lambda path: mock_analyzer
        )

        strategy = get_model_strategy(
            backend=ModelBackend.ONNX, settings=mock_settings_onnx
        )

        assert strategy == mock_analyzer

    def test_onnx_strategy_uses_default_path(self, mock_settings_onnx, monkeypatch):
        """Test ONNX strategy uses default path when main path is None."""
        from app.unified_api import get_model_strategy, ModelBackend

        # Set onnx_model_path to None
        mock_settings_onnx.onnx_model_path = None

        called_with_path = []

        def capture_path(path):
            called_with_path.append(path)
            mock = Mock()
            mock.is_ready.return_value = True
            return mock

        monkeypatch.setattr("app.unified_api.get_onnx_sentiment_analyzer", capture_path)

        get_model_strategy(backend=ModelBackend.ONNX, settings=mock_settings_onnx)

        assert len(called_with_path) == 1
        assert called_with_path[0] == mock_settings_onnx.onnx_model_path_default


@pytest.mark.integration
@pytest.mark.strategy
class TestUnifiedAPIEndpoints:
    """Test unified API endpoints with mocked strategies."""

    @pytest.fixture
    def client(self, mock_settings_pytorch, monkeypatch):
        """Create test client with mocked strategy."""
        # Mock the strategy to avoid loading actual models
        mock_analyzer = Mock()
        mock_analyzer.is_ready.return_value = True
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
            "cuda_memory_allocated_mb": 0.0,
            "cuda_memory_reserved_mb": 0.0,
            "cuda_device_count": 0,
        }

        monkeypatch.setattr(
            "app.unified_api.get_sentiment_analyzer", lambda: mock_analyzer
        )
        monkeypatch.setattr(
            "app.unified_api.get_onnx_sentiment_analyzer", lambda path: mock_analyzer
        )

        from app.unified_api import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        return TestClient(app)

    def test_predict_endpoint_success(self, client):
        """Test /predict endpoint returns expected response."""
        response = client.post(
            "/predict",
            json={"text": "Test text"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["label"] == "POSITIVE"
        assert data["score"] == 0.95
        assert "backend" in data
        assert "cached" in data

    def test_predict_endpoint_with_backend_parameter(self, client):
        """Test /predict endpoint with explicit backend parameter."""
        response = client.post(
            "/predict?backend=pytorch",
            json={"text": "Test text"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "pytorch"

    def test_predict_endpoint_adds_headers(self, client):
        """Test /predict endpoint adds custom headers."""
        response = client.post(
            "/predict",
            json={"text": "Test text"},
        )

        assert "X-Inference-Time-MS" in response.headers
        assert "X-Model-Backend" in response.headers

    def test_health_endpoint(self, client):
        """Test /health endpoint returns expected response."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["model_status"] == "available"
        assert "backend" in data
        assert "version" in data
        assert "timestamp" in data

    def test_model_info_endpoint(self, client):
        """Test /model-info endpoint returns expected response."""
        response = client.get("/model-info")

        assert response.status_code == 200
        data = response.json()

        assert "model_name" in data
        assert "is_loaded" in data
        assert "is_ready" in data
        assert "backend" in data

    def test_metrics_json_endpoint(self, client):
        """Test /metrics-json endpoint returns expected response."""
        response = client.get("/metrics-json")

        assert response.status_code == 200
        data = response.json()

        assert "torch_version" in data
        assert "cuda_available" in data

    def test_predict_empty_text_validation(self, client):
        """Test /predict endpoint validates empty text."""
        response = client.post(
            "/predict",
            json={"text": ""},
        )

        # Should get validation error
        assert response.status_code == 422  # Validation error


@pytest.mark.unit
@pytest.mark.strategy
class TestModelStrategyProtocol:
    """Test that analyzers conform to ModelStrategy protocol."""

    def test_pytorch_analyzer_implements_protocol(self):
        """Test SentimentAnalyzer implements ModelStrategy protocol."""
        from app.ml.sentiment import SentimentAnalyzer
        from app.ml.model_strategy import ModelStrategy

        # Check that all required methods exist
        assert hasattr(SentimentAnalyzer, "is_ready")
        assert hasattr(SentimentAnalyzer, "predict")
        assert hasattr(SentimentAnalyzer, "get_model_info")
        assert hasattr(SentimentAnalyzer, "get_performance_metrics")

    def test_onnx_analyzer_implements_protocol(self):
        """Test ONNXSentimentAnalyzer implements ModelStrategy protocol."""
        from app.ml.onnx_optimizer import ONNXSentimentAnalyzer
        from app.ml.model_strategy import ModelStrategy

        # Check that all required methods exist
        assert hasattr(ONNXSentimentAnalyzer, "is_ready")
        assert hasattr(ONNXSentimentAnalyzer, "predict")
        assert hasattr(ONNXSentimentAnalyzer, "get_model_info")
