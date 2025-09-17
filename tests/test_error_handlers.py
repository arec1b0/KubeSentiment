"""
Unit tests for error handling utilities.
"""

import pytest
from fastapi import HTTPException
from app.utils.error_handlers import (
    handle_prediction_error,
    handle_metrics_error,
    handle_model_info_error,
    handle_prometheus_metrics_error,
)


class TestErrorHandlers:
    """Test cases for error handling utilities."""

    def test_handle_prediction_value_error(self):
        """Test handling ValueError in prediction."""
        with pytest.raises(HTTPException) as exc_info:
            handle_prediction_error(ValueError("Invalid input"), "prediction")

        assert exc_info.value.status_code == 422
        assert "Invalid input" in exc_info.value.detail

    def test_handle_prediction_runtime_error(self):
        """Test handling RuntimeError in prediction."""
        with pytest.raises(HTTPException) as exc_info:
            handle_prediction_error(RuntimeError("Model failed"), "prediction")

        assert exc_info.value.status_code == 500
        assert "Prediction failed" in exc_info.value.detail

    def test_handle_prediction_generic_error(self):
        """Test handling generic Exception in prediction."""
        with pytest.raises(HTTPException) as exc_info:
            handle_prediction_error(Exception("Unexpected error"), "prediction")

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error"

    def test_handle_metrics_error(self):
        """Test handling errors in metrics retrieval."""
        with pytest.raises(HTTPException) as exc_info:
            handle_metrics_error(Exception("Metrics error"))

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to retrieve metrics"

    def test_handle_model_info_error(self):
        """Test handling errors in model info retrieval."""
        with pytest.raises(HTTPException) as exc_info:
            handle_model_info_error(Exception("Model info error"))

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to retrieve model information"

    def test_handle_prometheus_metrics_error(self):
        """Test handling errors in Prometheus metrics retrieval."""
        with pytest.raises(HTTPException) as exc_info:
            handle_prometheus_metrics_error(Exception("Prometheus error"))

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to retrieve metrics"
