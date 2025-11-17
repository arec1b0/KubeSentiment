"""Unit tests for the error handling utility functions.

This module contains test cases for the centralized error handlers in
`app.utils.error_handlers`, ensuring that different exception types are
correctly mapped to the appropriate `HTTPException` with the right status
codes and detail messages.
"""

import pytest


import pytest
from fastapi import HTTPException

from app.utils.error_handlers import (
    handle_metrics_error,
    handle_model_info_error,
    handle_prediction_error,
    handle_prometheus_metrics_error,
)


@pytest.mark.unit
class TestErrorHandlers:
    """A test suite for the error handling utility functions."""

    def test_handle_prediction_value_error(self):
        """Tests that a `ValueError` in prediction is handled as a 422 Unprocessable Entity."""
        with pytest.raises(HTTPException) as exc_info:
            handle_prediction_error(ValueError("Invalid input"), "prediction")

        assert exc_info.value.status_code == 422
        assert "Invalid input" in exc_info.value.detail

    def test_handle_prediction_runtime_error(self):
        """Tests that a `RuntimeError` in prediction is handled as a 500 Internal Server Error."""
        with pytest.raises(HTTPException) as exc_info:
            handle_prediction_error(RuntimeError("Model failed"), "prediction")

        assert exc_info.value.status_code == 500
        assert "Prediction failed" in exc_info.value.detail

    def test_handle_prediction_generic_error(self):
        """Tests that a generic `Exception` in prediction is handled as a 500 Internal Server Error."""
        with pytest.raises(HTTPException) as exc_info:
            handle_prediction_error(Exception("Unexpected error"), "prediction")

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal server error"

    def test_handle_metrics_error(self):
        """Tests that an exception during metrics retrieval is handled as a 500 error."""
        with pytest.raises(HTTPException) as exc_info:
            handle_metrics_error(Exception("Metrics error"))

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to retrieve metrics"

    def test_handle_model_info_error(self):
        """Tests that an exception during model info retrieval is handled as a 500 error."""
        with pytest.raises(HTTPException) as exc_info:
            handle_model_info_error(Exception("Model info error"))

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to retrieve model information"

    def test_handle_prometheus_metrics_error(self):
        """Tests that an exception during Prometheus metrics retrieval is handled as a 500 error."""
        with pytest.raises(HTTPException) as exc_info:
            handle_prometheus_metrics_error(Exception("Prometheus error"))

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to retrieve metrics"
        assert exc_info.value.detail == "Failed to retrieve metrics"
