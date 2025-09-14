"""Test configuration and fixtures for the MLOps sentiment analysis service."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import create_app
from app.config import get_settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = get_settings()
    settings.debug = True
    settings.model_name = "mock-model"
    return settings


@pytest.fixture
def mock_sentiment_analyzer():
    """Create a mock sentiment analyzer for testing."""
    mock_analyzer = MagicMock()
    mock_analyzer.is_ready.return_value = True
    mock_analyzer.predict.return_value = {"label": "POSITIVE", "score": 0.999}
    return mock_analyzer


@pytest.fixture
def app(mock_settings):
    """Create a test FastAPI app."""
    with patch("app.main.get_settings", return_value=mock_settings):
        return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def client_with_mock_model(app):
    """Create a test client with mocked sentiment analyzer."""
    with patch("app.api.get_sentiment_analyzer") as mock_get_analyzer:
        mock_analyzer = MagicMock()
        mock_analyzer.is_ready.return_value = True
        mock_analyzer.predict.return_value = {
            "label": "POSITIVE",
            "score": 0.999,
            "inference_time_ms": 10.0,
            "model_name": "mock-model",
            "text_length": 19
        }
        mock_get_analyzer.return_value = mock_analyzer
        yield TestClient(app)