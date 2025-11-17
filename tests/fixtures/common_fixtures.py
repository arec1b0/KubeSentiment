"""Common pytest fixtures used across multiple test files.

This module provides reusable fixtures to reduce duplication and
ensure consistency across the test suite.
"""

import pytest
from unittest.mock import patch

from tests.fixtures.common_mocks import (
    MockModel,
    MockSettings,
    create_mock_analyzer,
)

# Import FastAPI dependencies with fallback for test discovery
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    TestClient = None


@pytest.fixture
def mock_model():
    """Provide a mock model for testing.

    Returns:
        MockModel instance configured for testing.
    """
    return MockModel()


@pytest.fixture
def mock_settings():
    """Provide mock settings for testing.

    Returns:
        MockSettings instance with default test configuration.
    """
    return MockSettings()


@pytest.fixture
def mock_analyzer():
    """Provide a mock SentimentAnalyzer for testing.

    Returns:
        Mock object simulating SentimentAnalyzer behavior.
    """
    return create_mock_analyzer()


@pytest.fixture
def test_app(mock_analyzer, mock_settings):
    """Create a test FastAPI application instance.

    This fixture sets up a new FastAPI app for each test, includes the API
    routers, and patches the dependency injection system to use the mock
    analyzer and settings.

    Args:
        mock_analyzer: The mocked SentimentAnalyzer fixture.
        mock_settings: The mocked settings fixture.

    Yields:
        The configured FastAPI app instance for testing.
    """
    from app.api.routes.health import router as health_router
    from app.api.routes.metrics import router as metrics_router
    from app.api.routes.model_info import router as model_info_router
    from app.api.routes.predictions import router as predictions_router

    app = FastAPI()
    app.include_router(predictions_router)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(model_info_router)

    # Mock the dependencies
    with (
        patch("app.models.pytorch_sentiment.get_sentiment_analyzer", return_value=mock_analyzer),
        patch("app.core.config.get_settings", return_value=mock_settings),
    ):
        yield app


@pytest.fixture
def client(test_app):
    """Create a TestClient for the FastAPI application.

    This provides a client to make requests to the test application.

    Args:
        test_app: The test FastAPI application instance.

    Returns:
        A TestClient instance.
    """
    return TestClient(test_app)
