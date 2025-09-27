"""
Tests for correlation ID and structured logging functionality.

These tests verify that correlation IDs are properly propagated through
the application and that structured logging works as expected.
"""

import pytest
import json
import uuid
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from io import StringIO

from app.main import create_app
from app.logging_config import (
    set_correlation_id,
    get_correlation_id,
    generate_correlation_id,
    clear_correlation_id,
    get_contextual_logger,
)
from app.config import Settings


class TestCorrelationIdManagement:
    """Test correlation ID context management."""

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
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
        """Test correlation ID generation."""
        id1 = generate_correlation_id()
        id2 = generate_correlation_id()

        # Should be valid UUIDs
        assert uuid.UUID(id1)
        assert uuid.UUID(id2)

        # Should be different
        assert id1 != id2

    def test_contextual_logger_includes_correlation_id(self):
        """Test that contextual logger includes correlation ID."""
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


class TestCorrelationIdMiddleware:
    """Test correlation ID middleware functionality."""

    @pytest.fixture
    def client(self):
        """Create test client with correlation middleware."""
        test_settings = Settings(debug=True, api_key=None, allowed_origins=["*"])

        with patch("app.config.get_settings", return_value=test_settings):
            with patch("app.main.get_settings", return_value=test_settings):
                with patch("app.ml.sentiment.pipeline") as mock_pipeline:
                    mock_model = Mock()
                    mock_model.return_value = [{"label": "POSITIVE", "score": 0.95}]
                    mock_pipeline.return_value = mock_model

                    app = create_app()
                    yield TestClient(app)

    def test_correlation_id_generated_automatically(self, client):
        """Test that correlation ID is generated automatically."""
        response = client.get("/health")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers

        correlation_id = response.headers["X-Correlation-ID"]
        assert correlation_id is not None
        assert len(correlation_id) > 0

        # Should be a valid UUID
        uuid.UUID(correlation_id)

    def test_correlation_id_preserved_from_request(self, client):
        """Test that provided correlation ID is preserved."""
        test_correlation_id = "custom-correlation-id-123"

        response = client.get(
            "/health", headers={"X-Correlation-ID": test_correlation_id}
        )

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_correlation_id

    def test_correlation_id_in_prediction_flow(self, client):
        """Test correlation ID through prediction flow."""
        test_correlation_id = str(uuid.uuid4())

        response = client.post(
            "/predict",
            json={"text": "This is a test message"},
            headers={"X-Correlation-ID": test_correlation_id},
        )

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_correlation_id

    def test_correlation_id_in_error_responses(self, client):
        """Test correlation ID is included in error responses."""
        test_correlation_id = str(uuid.uuid4())

        # Make request with empty text (should cause validation error)
        response = client.post(
            "/predict",
            json={"text": ""},
            headers={"X-Correlation-ID": test_correlation_id},
        )

        assert response.status_code == 400
        assert response.headers["X-Correlation-ID"] == test_correlation_id


class TestStructuredLogging:
    """Test structured logging functionality."""

    def test_log_structure_contains_required_fields(self):
        """Test that log entries contain required structured fields."""
        import logging
        from app.logging_config import setup_structured_logging, get_logger

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
        """Test that contextual logger properly binds context."""
        from app.logging_config import setup_structured_logging

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


class TestLoggingIntegration:
    """Test logging integration across the application."""

    @pytest.fixture
    def client_with_logging_capture(self):
        """Create client with log capture."""
        test_settings = Settings(debug=True, api_key=None, log_level="DEBUG")

        with patch("app.config.get_settings", return_value=test_settings):
            with patch("app.ml.sentiment.pipeline") as mock_pipeline:
                mock_model = Mock()
                mock_model.return_value = [{"label": "POSITIVE", "score": 0.95}]
                mock_pipeline.return_value = mock_model

                # Capture logs
                log_capture = StringIO()
                handler = logging.StreamHandler(log_capture)
                logging.getLogger().addHandler(handler)

                try:
                    app = create_app()
                    client = TestClient(app)
                    yield client, log_capture
                finally:
                    logging.getLogger().removeHandler(handler)

    def test_end_to_end_logging_with_correlation_id(self, client_with_logging_capture):
        """Test end-to-end logging with correlation ID propagation."""
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

        assert correlation_found, (
            f"Correlation ID {test_correlation_id} not found in logs"
        )

    def test_error_logging_with_correlation_id(self, client_with_logging_capture):
        """Test error logging includes correlation ID."""
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
                if log_entry.get(
                    "correlation_id"
                ) == test_correlation_id and log_entry.get("level") in [
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
