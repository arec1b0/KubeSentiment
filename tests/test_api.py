"""Tests for the API endpoints."""

import pytest
from unittest.mock import patch, MagicMock


class TestHealthEndpoint:
    """Test suite for the health endpoint."""

    def test_health_endpoint_success(self, client_with_mock_model):
        """Test health endpoint when model is ready."""
        response = client_with_mock_model.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_status"] == "available"
        assert "version" in data
        assert "timestamp" in data

    def test_health_endpoint_degraded_mode(self, client):
        """Test health endpoint when model is not ready."""
        with patch("app.api.get_sentiment_analyzer") as mock_get_analyzer:
            mock_analyzer = MagicMock()
            mock_analyzer.is_ready.return_value = False
            mock_get_analyzer.return_value = mock_analyzer

            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"  # Status is always healthy, only model_status changes
            assert data["model_status"] == "unavailable"


class TestMetricsEndpoint:
    """Test suite for the metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint returns system information."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "torch_version" in data
        assert "cuda_available" in data
        assert "cuda_device_count" in data


class TestPredictEndpoint:
    """Test suite for the sentiment prediction endpoint."""

    def test_predict_endpoint_success(self, client_with_mock_model):
        """Test successful prediction."""
        payload = {"text": "I love this service!"}
        with patch("app.api.get_sentiment_analyzer") as mock_get_analyzer:
            mock_analyzer = MagicMock()
            mock_analyzer.is_ready.return_value = True
            mock_analyzer.predict.return_value = {
                "label": "POSITIVE",
                "score": 0.999,
                "inference_time_ms": 10.5,
                "model_name": "test-model",
                "text_length": 19
            }
            mock_get_analyzer.return_value = mock_analyzer
            
            response = client_with_mock_model.post("/predict", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["label"] == "POSITIVE"
            assert data["score"] == 0.999

    def test_predict_endpoint_empty_text(self, client_with_mock_model):
        """Test prediction with empty text."""
        payload = {"text": ""}
        response = client_with_mock_model.post("/predict", json=payload)
        assert response.status_code == 422  # Validation error

    def test_predict_endpoint_whitespace_only(self, client_with_mock_model):
        """Test prediction with whitespace-only text."""
        payload = {"text": "   "}
        response = client_with_mock_model.post("/predict", json=payload)
        assert response.status_code == 422  # Validation error

    def test_predict_endpoint_missing_text(self, client_with_mock_model):
        """Test prediction without text field."""
        payload = {}
        response = client_with_mock_model.post("/predict", json=payload)
        assert response.status_code == 422  # Validation error

    def test_predict_endpoint_invalid_json(self, client_with_mock_model):
        """Test prediction with invalid JSON."""
        response = client_with_mock_model.post(
            "/predict", 
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_predict_endpoint_degraded_mode(self, client):
        """Test prediction when model is not ready."""
        with patch("app.api.get_sentiment_analyzer") as mock_get_analyzer:
            mock_analyzer = MagicMock()
            mock_analyzer.is_ready.return_value = False
            mock_get_analyzer.return_value = mock_analyzer

            payload = {"text": "Test message"}
            response = client.post("/predict", json=payload)
            assert response.status_code == 503  # Service unavailable
            data = response.json()
            assert "Service Unavailable" in data["detail"]

    def test_predict_endpoint_model_error(self, client_with_mock_model):
        """Test prediction when model raises an exception."""
        with patch("app.api.get_sentiment_analyzer") as mock_get_analyzer:
            mock_analyzer = MagicMock()
            mock_analyzer.is_ready.return_value = True
            mock_analyzer.predict.side_effect = Exception("Model error")
            mock_get_analyzer.return_value = mock_analyzer

            payload = {"text": "Test message"}
            response = client_with_mock_model.post("/predict", json=payload)
            assert response.status_code == 500

    def test_predict_endpoint_long_text(self, client_with_mock_model):
        """Test prediction with very long text."""
        long_text = "This is a very long text. " * 1000
        payload = {"text": long_text}
        with patch("app.api.get_sentiment_analyzer") as mock_get_analyzer:
            mock_analyzer = MagicMock()
            mock_analyzer.is_ready.return_value = True
            mock_analyzer.predict.return_value = {
                "label": "POSITIVE",
                "score": 0.85,
                "inference_time_ms": 15.2,
                "model_name": "test-model",
                "text_length": len(long_text)
            }
            mock_get_analyzer.return_value = mock_analyzer
            
            response = client_with_mock_model.post("/predict", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert "label" in data
            assert "score" in data


class TestResponseHeaders:
    """Test suite for response headers."""

    def test_correlation_id_header(self, client):
        """Test that all responses include correlation ID."""
        response = client.get("/health")
        assert "X-Correlation-ID" in response.headers

    def test_content_type_headers(self, client_with_mock_model):
        """Test that JSON responses have correct content type."""
        response = client_with_mock_model.get("/health")
        assert response.headers["content-type"] == "application/json"