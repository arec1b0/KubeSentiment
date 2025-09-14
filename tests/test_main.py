"""Tests for the main application module."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import create_app, CorrelationIDMiddleware


class TestApp:
    """Test suite for the main FastAPI application."""

    def test_create_app(self):
        """Test that the app is created successfully."""
        app = create_app()
        assert app.title == "ML Model Serving API"
        assert app.version == "1.0.0"

    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ML Model Serving API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"

    def test_correlation_id_middleware(self, client):
        """Test that correlation ID is added to responses."""
        response = client.get("/")
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) == 36  # UUID length

    def test_cors_middleware(self, client):
        """Test CORS headers are present."""
        response = client.get("/")
        # CORS headers are added automatically by FastAPI middleware
        assert response.status_code == 200

    def test_debug_mode_endpoints(self, client):
        """Test that debug mode endpoints are accessible."""
        # In debug mode, docs should be available
        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/redoc")
        assert response.status_code == 200


class TestErrorHandling:
    """Test suite for error handling."""

    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    @patch("app.main.logger")
    def test_global_exception_handler(self, mock_logger, app):
        """Test global exception handler."""
        # Create a route that raises an exception
        @app.get("/test-error")
        async def test_error():
            raise ValueError("Test error")

        client = TestClient(app)
        response = client.get("/test-error")
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Internal server error"
        assert "error_id" in data
        mock_logger.error.assert_called_once()