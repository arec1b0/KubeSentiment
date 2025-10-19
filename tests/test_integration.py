"""
Integration tests for the MLOps sentiment analysis service.

These tests verify end-to-end functionality including API endpoints,
model loading, caching, monitoring, and error handling across the full stack.
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.dependencies import get_prediction_service
from app.main import create_app


class TestFullRequestFlow:
    """Test complete request flows from API to model inference."""

    @pytest.fixture
    def test_settings(self):
        """Create test settings with validation."""
        return Settings(
            debug=True,
            model_name="distilbert-base-uncased-finetuned-sst-2-english",
            allowed_models=["distilbert-base-uncased-finetuned-sst-2-english"],
            max_text_length=100,
            prediction_cache_max_size=10,
            enable_metrics=True,
            api_key=None,  # No auth for integration tests
            allowed_origins=["*"],
        )

    @pytest.fixture
    def client(self, test_settings):
        """Create test client with mocked dependencies."""
        with patch("app.config.get_settings", return_value=test_settings):
            with patch("app.ml.sentiment.pipeline") as mock_pipeline:
                # Mock the transformers pipeline
                mock_model = Mock()
                mock_model.return_value = [{"label": "POSITIVE", "score": 0.95}]
                mock_pipeline.return_value = mock_model

                # Reset model caches for clean test state
                from app.models.factory import ModelFactory

                ModelFactory.reset_models()

                app = create_app()
                yield TestClient(app)

    def test_successful_prediction_flow(self, client):
        """Test successful end-to-end prediction flow."""
        # Test data
        test_text = "I love this product!"

        # Make prediction request
        response = client.post("/predict", json={"text": test_text})

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "label" in data
        assert "score" in data
        assert "inference_time_ms" in data
        assert "model_name" in data
        assert "text_length" in data

        # Check response values
        assert data["label"] == "POSITIVE"
        assert data["score"] == 0.95
        assert data["text_length"] == len(test_text)
        assert data["model_name"] == "distilbert-base-uncased-finetuned-sst-2-english"
        assert isinstance(data["inference_time_ms"], (int, float))
        assert data["inference_time_ms"] > 0

        # Check response headers
        assert "X-Inference-Time-MS" in response.headers

    def test_prediction_caching_flow(self, client):
        """Test that prediction caching works correctly."""
        test_text = "This is a test message for caching"

        # First request - should not be cached
        response1 = client.post("/predict", json={"text": test_text})
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1.get("cached", False) is False

        # Second request with same text - should be cached
        response2 = client.post("/predict", json={"text": test_text})
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2.get("cached", False) is True

        # Results should be identical except for cached flag
        assert data1["label"] == data2["label"]
        assert data1["score"] == data2["score"]
        assert data1["text_length"] == data2["text_length"]

    def test_health_check_flow(self, client):
        """Test health check endpoint functionality."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "status" in data
        assert "model_status" in data
        assert "version" in data
        assert "timestamp" in data

        # Check values
        assert data["status"] == "healthy"
        assert data["model_status"] == "available"
        assert isinstance(data["timestamp"], (int, float))

    def test_metrics_endpoint_flow(self, client):
        """Test metrics endpoint functionality."""
        # First make some predictions to generate metrics
        client.post("/predict", json={"text": "Test message 1"})
        client.post("/predict", json={"text": "Test message 2"})

        # Get Prometheus metrics
        response = client.get("/metrics")
        assert response.status_code == 200

        # Check content type
        assert "text/plain" in response.headers["content-type"]

        # Check that metrics contain expected data
        metrics_text = response.text
        assert "sentiment_requests_total" in metrics_text
        assert "sentiment_inference_duration_seconds" in metrics_text

        # Get JSON metrics
        response_json = client.get("/metrics-json")
        assert response_json.status_code == 200

        data = response_json.json()
        assert "torch_version" in data
        assert "cuda_available" in data

    def test_model_info_flow(self, client):
        """Test model info endpoint functionality."""
        response = client.get("/model-info")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "model_name" in data
        assert "is_loaded" in data
        assert "is_ready" in data
        assert "torch_version" in data
        assert "cuda_available" in data
        assert "cache_stats" in data

        # Check values
        assert data["model_name"] == "distilbert-base-uncased-finetuned-sst-2-english"
        assert data["is_loaded"] is True
        assert data["is_ready"] is True


class TestErrorHandlingFlow:
    """Test error handling across the full stack."""

    @pytest.fixture
    def client_with_auth(self):
        """Create client with API key authentication."""
        test_settings = Settings(
            debug=False,
            api_key="test123key",  # Valid API key
            allowed_origins=["*"],
        )

        with patch("app.config.get_settings", return_value=test_settings):
            with patch("app.ml.sentiment.pipeline") as mock_pipeline:
                mock_model = Mock()
                mock_model.return_value = [{"label": "POSITIVE", "score": 0.95}]
                mock_pipeline.return_value = mock_model

                app = create_app()
                yield TestClient(app)

    def test_authentication_error_flow(self, client_with_auth):
        """Test authentication error handling."""
        # Request without API key
        response = client_with_auth.post("/predict", json={"text": "test"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Unauthorized"

        # Request with invalid API key
        response = client_with_auth.post(
            "/predict", json={"text": "test"}, headers={"X-API-Key": "invalid"}
        )
        assert response.status_code == 401

        # Request with valid API key should work
        response = client_with_auth.post(
            "/predict", json={"text": "test"}, headers={"X-API-Key": "test123key"}
        )
        assert response.status_code == 200

    @pytest.fixture
    def client_with_broken_model(self):
        """Create client with model that fails to load."""
        test_settings = Settings(
            debug=True,
            model_name="invalid-model",
            allowed_models=["invalid-model"],
            api_key=None,
        )

        with patch("app.config.get_settings", return_value=test_settings):
            with patch("app.ml.sentiment.pipeline", side_effect=Exception("Model load failed")):
                app = create_app()
                yield TestClient(app)

    def test_model_loading_error_flow(self, client_with_broken_model):
        """Test handling of model loading failures."""
        # Health check should show model unavailable
        response = client_with_broken_model.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["model_status"] == "unavailable"

        # Prediction should fail with 503
        response = client_with_broken_model.post("/predict", json={"text": "test"})
        assert response.status_code == 503
        assert "MODEL_NOT_LOADED" in response.json()["error_code"]

    def test_validation_error_flow(self, client):
        """Test input validation error handling."""
        # Empty text
        response = client.post("/predict", json={"text": ""})
        assert response.status_code == 400
        assert "TEXT_EMPTY" in response.json()["error_code"]

        # Missing text field
        response = client.post("/predict", json={})
        assert response.status_code == 422  # Pydantic validation error

        # Text too long
        long_text = "x" * 1000  # Exceeds max_text_length of 100
        response = client.post("/predict", json={"text": long_text})
        assert response.status_code == 400
        assert "TEXT_TOO_LONG" in response.json()["error_code"]


class TestConcurrencyAndPerformance:
    """Test concurrent requests and performance characteristics."""

    @pytest.fixture
    def client(self):
        """Create client for performance testing."""
        test_settings = Settings(debug=False, prediction_cache_max_size=100, api_key=None)

        with patch("app.config.get_settings", return_value=test_settings):
            with patch("app.ml.sentiment.pipeline") as mock_pipeline:
                # Mock with slight delay to simulate real inference
                def mock_inference(text):
                    time.sleep(0.01)  # 10ms delay
                    return [{"label": "POSITIVE", "score": 0.95}]

                mock_model = Mock(side_effect=mock_inference)
                mock_pipeline.return_value = mock_model

                app = create_app()
                yield TestClient(app)

    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        import queue
        import threading

        results = queue.Queue()

        def make_request(text):
            try:
                response = client.post("/predict", json={"text": f"Test message {text}"})
                results.put(("success", response.status_code, response.json()))
            except Exception as e:
                results.put(("error", str(e), None))

        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        success_count = 0
        while not results.empty():
            status, code, data = results.get()
            if status == "success":
                assert code == 200
                success_count += 1

        assert success_count == 10

    def test_cache_performance(self, client):
        """Test cache performance under load."""
        test_messages = [
            "This is test message 1",
            "This is test message 2",
            "This is test message 3",
        ]

        # First round - populate cache
        start_time = time.time()
        for msg in test_messages:
            response = client.post("/predict", json={"text": msg})
            assert response.status_code == 200
        first_round_time = time.time() - start_time

        # Second round - should be faster due to caching
        start_time = time.time()
        for msg in test_messages:
            response = client.post("/predict", json={"text": msg})
            assert response.status_code == 200
            assert response.json().get("cached", False) is True
        second_round_time = time.time() - start_time

        # Cached requests should be significantly faster
        assert second_round_time < first_round_time * 0.5


class TestConfigurationIntegration:
    """Test configuration validation in real application context."""

    def test_invalid_configuration_prevents_startup(self):
        """Test that invalid configuration prevents application startup."""
        # Test invalid model name not in allowed list
        with pytest.raises(ValueError, match="not in allowed models"):
            Settings(model_name="unauthorized-model", allowed_models=["valid-model"])

        # Test invalid port range
        with pytest.raises(ValueError):
            Settings(port=99999)  # Too high

        # Test invalid log level
        with pytest.raises(ValueError):
            Settings(log_level="INVALID")

    def test_configuration_validation_with_environment(self):
        """Test configuration validation with environment variables."""
        import os

        # Test valid configuration
        os.environ["MLOPS_MODEL_NAME"] = "distilbert-base-uncased-finetuned-sst-2-english"
        os.environ["MLOPS_PORT"] = "8080"
        os.environ["MLOPS_DEBUG"] = "true"

        try:
            settings = Settings()
            assert settings.model_name == "distilbert-base-uncased-finetuned-sst-2-english"
            assert settings.port == 8080
            assert settings.debug is True
        finally:
            # Clean up environment
            for key in ["MLOPS_MODEL_NAME", "MLOPS_PORT", "MLOPS_DEBUG"]:
                os.environ.pop(key, None)


class TestMonitoringIntegration:
    """Test monitoring and metrics integration."""

    @pytest.fixture
    def client(self):
        """Create client with monitoring enabled."""
        test_settings = Settings(debug=False, enable_metrics=True, api_key=None)

        with patch("app.config.get_settings", return_value=test_settings):
            with patch("app.ml.sentiment.pipeline") as mock_pipeline:
                mock_model = Mock()
                mock_model.return_value = [{"label": "POSITIVE", "score": 0.95}]
                mock_pipeline.return_value = mock_model

                app = create_app()
                yield TestClient(app)

    def test_metrics_collection_flow(self, client):
        """Test that metrics are properly collected during requests."""
        # Make some requests
        client.post("/predict", json={"text": "Test 1"})
        client.post("/predict", json={"text": "Test 2"})
        client.get("/health")

        # Get metrics
        response = client.get("/metrics")
        assert response.status_code == 200

        metrics_text = response.text

        # Check for request metrics
        assert "sentiment_requests_total" in metrics_text
        assert "sentiment_request_duration_seconds" in metrics_text
        assert "sentiment_inference_duration_seconds" in metrics_text

        # Check for system metrics
        assert "sentiment_model_loaded" in metrics_text
        assert "sentiment_torch_version" in metrics_text

    def test_metrics_caching(self, client):
        """Test metrics response caching."""
        # First request
        start_time = time.time()
        response1 = client.get("/metrics")
        first_request_time = time.time() - start_time

        # Second request (should be cached)
        start_time = time.time()
        response2 = client.get("/metrics")
        second_request_time = time.time() - start_time

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Second request should be faster (cached)
        assert second_request_time < first_request_time


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
