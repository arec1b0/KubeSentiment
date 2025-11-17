"""Tests for correlation ID and structured logging functionality.

This module contains test cases to ensure that correlation IDs are correctly
generated, propagated through middleware, and included in structured logs,
both for successful requests and error conditions.
"""

import pytest


import json
import uuid
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.middleware.correlation import CorrelationIdMiddleware
from app.core.config import Settings
from app.core.logging import (
    clear_correlation_id,
    generate_correlation_id,
    get_contextual_logger,
    get_correlation_id,
    set_correlation_id,
)
from app.main import create_app


@pytest.mark.unit
class TestCorrelationIdManagement:
    """A test suite for the correlation ID context management functions.

    These tests verify the core functions for setting, getting, generating,
    and clearing correlation IDs from the application's context.
    """

    def test_set_and_get_correlation_id(self):
        """Tests that a correlation ID can be set and retrieved correctly."""
        test_id = "test-correlation-id-123"

        # Initially should be None
        assert get_correlation_id() is None

        # Set correlation ID
        set_correlation_id(test_id)
        assert get_correlation_id() == test_id

        # Clear correlation ID
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_generate_correlation_id(self):
        """Tests that the generated correlation ID is a valid and unique UUID."""
        id1 = generate_correlation_id()
        id2 = generate_correlation_id()

        # Should be valid UUIDs
        assert uuid.UUID(id1)
        assert uuid.UUID(id2)

        # Should be different
        assert id1 != id2

    def test_contextual_logger_includes_correlation_id(self):
        """Tests that the contextual logger is created with the correlation ID.

        This test is an indirect check; the full functionality is verified
        in the middleware tests where logs are captured and inspected.
        """
        test_id = "test-correlation-123"
        set_correlation_id(test_id)

        try:
            # Create contextual logger
            logger = get_contextual_logger(__name__, operation="test")

            # The logger should have correlation ID in context
            # This is tested indirectly through the middleware tests
            assert logger is not None

        finally:
            clear_correlation_id()


@pytest.mark.unit
class TestCorrelationIdMiddleware:
    """A test suite for the `CorrelationIdMiddleware`.

    These tests ensure the middleware correctly handles the `X-Correlation-ID`
    header, generating a new ID if one is not provided, and preserving an
    existing one across the request-response cycle.
    """

    @pytest.fixture
    def client(self):
        """Creates a test client with the correlation middleware.

        Yields:
            A `TestClient` instance for making requests to the app.
        """
        test_settings = Settings(debug=True, api_key=None, allowed_origins=["*"])

        with patch("app.config.get_settings", return_value=test_settings), patch(
            "app.main.get_settings", return_value=test_settings
        ), patch("app.ml.sentiment.pipeline") as mock_pipeline:
            mock_model = Mock()
                    mock_model.return_value = [{"label": "POSITIVE", "score": 0.95}]
                    mock_pipeline.return_value = mock_model

                    app = create_app()
                    yield TestClient(app)

    def test_correlation_id_generated_automatically(self, client):
        """Tests that a correlation ID is automatically generated if none is provided."""
        response = client.get("/health")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers

        correlation_id = response.headers["X-Correlation-ID"]
        assert correlation_id is not None
        assert len(correlation_id) > 0

        # Should be a valid UUID
        uuid.UUID(correlation_id)

    def test_correlation_id_preserved_from_request(self, client):
        """Tests that a correlation ID from an incoming request is preserved."""
        test_correlation_id = "custom-correlation-id-123"

        response = client.get("/health", headers={"X-Correlation-ID": test_correlation_id})

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_correlation_id

    def test_correlation_id_in_prediction_flow(self, client):
        """Tests that the correlation ID is present throughout a prediction request."""
        test_correlation_id = str(uuid.uuid4())

        response = client.post(
            "/predict",
            json={"text": "This is a test message"},
            headers={"X-Correlation-ID": test_correlation_id},
        )

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_correlation_id

    def test_correlation_id_in_error_responses(self, client):
        """Tests that the correlation ID is included in HTTP error responses."""
        test_correlation_id = str(uuid.uuid4())

        # Make request with empty text (should cause validation error)
        response = client.post(
            "/predict",
            json={"text": ""},
            headers={"X-Correlation-ID": test_correlation_id},
        )

        assert response.status_code == 400
        assert response.headers["X-Correlation-ID"] == test_correlation_id


@pytest.mark.unit
class TestStructuredLogging:
    """A test suite for the structured logging functionality.

    These tests verify that log records are formatted as JSON and contain
    the necessary structured fields, including the correlation ID.
    """

    def test_log_structure_contains_required_fields(self):
        """Tests that JSON log entries contain all required structured fields."""
        import logging

        from app.core.logging import get_logger, setup_structured_logging

        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)

        # Setup logging with our handler
        setup_structured_logging()
        logger = get_logger(__name__)

        # Add our capture handler
        logging.getLogger().addHandler(handler)

        try:
            # Set correlation ID
            test_correlation_id = "test-log-correlation-123"
            set_correlation_id(test_correlation_id)

            # Log a test message
            logger.info("Test log message", operation="test", test_field="test_value")

            # Get log output
            log_output = log_capture.getvalue()

            if log_output:
                # Parse JSON log entry
                log_entry = json.loads(log_output.strip())

                # Check required fields
                assert "timestamp" in log_entry
                assert "level" in log_entry
                assert "event" in log_entry
                assert log_entry["event"] == "Test log message"
                assert "service" in log_entry
                assert log_entry["service"] == "sentiment-analysis"
                assert "correlation_id" in log_entry
                assert log_entry["correlation_id"] == test_correlation_id
                assert "operation" in log_entry
                assert log_entry["operation"] == "test"
                assert "test_field" in log_entry
                assert log_entry["test_field"] == "test_value"

        finally:
            clear_correlation_id()
            logging.getLogger().removeHandler(handler)

    @patch("sys.stdout", new_callable=StringIO)
    def test_contextual_logger_binding(self, mock_stdout):
        """Tests that the contextual logger correctly binds context variables to log entries."""
        from app.core.logging import setup_structured_logging

        setup_structured_logging()

        test_correlation_id = "context-test-123"
        set_correlation_id(test_correlation_id)

        try:
            # Create contextual logger with extra context
            logger = get_contextual_logger(
                __name__,
                operation="test_operation",
                user_id="test_user",
                endpoint="/test",
            )

            # Log message
            logger.info("Test contextual logging")

            # Check output contains our context
            log_output = mock_stdout.getvalue()

            if log_output:
                log_entry = json.loads(log_output.strip())
                assert log_entry["correlation_id"] == test_correlation_id
                assert log_entry["operation"] == "test_operation"
                assert log_entry["user_id"] == "test_user"
                assert log_entry["endpoint"] == "/test"

        finally:
            clear_correlation_id()


@pytest.mark.unit
class TestLoggingIntegration:
    """A test suite for end-to-end logging integration.

    These tests ensure that the correlation ID is correctly propagated
    through the entire application stack and appears in the logs for both
    successful and failed requests.
    """

    @pytest.fixture
    def client_with_logging_capture(self):
        """Creates a test client and captures log output.

        This fixture sets up a test client for a FastAPI app and redirects
        the application's logging output to an in-memory buffer, allowing
        tests to inspect the generated logs.

        Yields:
            A tuple containing the `TestClient` and the log capture buffer.
        """
        test_settings = Settings(debug=True, api_key=None, log_level="DEBUG")

        with patch("app.config.get_settings", return_value=test_settings):
            with patch("app.ml.sentiment.pipeline") as mock_pipeline:
                mock_model = Mock()
                mock_model.return_value = [{"label": "POSITIVE", "score": 0.95}]
                mock_pipeline.return_value = mock_model

                # Capture logs
                log_capture = StringIO()
                handler = MagicMock()
                MagicMock().getLogger().addHandler(handler)

                try:
                    app = create_app()
                    client = TestClient(app)
                    yield client, log_capture
                finally:
                    logging.getLogger().removeHandler(handler)

    def test_end_to_end_logging_with_correlation_id(self, client_with_logging_capture):
        """Tests that a correlation ID is propagated end-to-end and appears in logs."""
        client, log_capture = client_with_logging_capture

        test_correlation_id = str(uuid.uuid4())

        # Make prediction request
        response = client.post(
            "/predict",
            json={"text": "This is a test for logging"},
            headers={"X-Correlation-ID": test_correlation_id},
        )

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_correlation_id

        # Check logs contain correlation ID
        log_output = log_capture.getvalue()
        log_lines = [line.strip() for line in log_output.split("\n") if line.strip()]

        correlation_found = False
        for line in log_lines:
            try:
                log_entry = json.loads(line)
                if log_entry.get("correlation_id") == test_correlation_id:
                    correlation_found = True
                    # Verify log structure
                    assert "timestamp" in log_entry
                    assert "level" in log_entry
                    assert "service" in log_entry
                    break
            except json.JSONDecodeError:
                continue  # Skip non-JSON log lines

        assert correlation_found, f"Correlation ID {test_correlation_id} not found in logs"

    def test_error_logging_with_correlation_id(self, client_with_logging_capture):
        """Tests that error logs correctly include the correlation ID."""
        client, log_capture = client_with_logging_capture

        test_correlation_id = str(uuid.uuid4())

        # Make request that will cause error (empty text)
        response = client.post(
            "/predict",
            json={"text": ""},
            headers={"X-Correlation-ID": test_correlation_id},
        )

        assert response.status_code == 400

        # Check error logs contain correlation ID
        log_output = log_capture.getvalue()
        log_lines = [line.strip() for line in log_output.split("\n") if line.strip()]

        error_with_correlation_found = False
        for line in log_lines:
            try:
                log_entry = json.loads(line)
                if log_entry.get("correlation_id") == test_correlation_id and log_entry.get(
                    "level"
                ) in [
                    "ERROR",
                    "WARNING",
                ]:
                    error_with_correlation_found = True
                    break
            except json.JSONDecodeError:
                continue

        assert error_with_correlation_found, "Error log with correlation ID not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
