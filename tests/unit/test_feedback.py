"""Unit tests for the feedback API endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock

from app.api.routes.feedback import router as feedback_router
from app.services.feedback_service import FeedbackService
from app.core.dependencies import get_feedback_service

@pytest.fixture
def mock_feedback_service():
    """Creates a mock feedback service."""
    service = Mock(spec=FeedbackService)
    service.submit_feedback = AsyncMock(return_value=True)
    return service

@pytest.fixture
def app(mock_feedback_service):
    """Creates a test FastAPI application."""
    app = FastAPI()
    app.include_router(feedback_router)
    
    # Override dependency
    app.dependency_overrides[get_feedback_service] = lambda: mock_feedback_service
    return app

@pytest.fixture
def client(app):
    """Creates a test client."""
    return TestClient(app)

@pytest.mark.unit
def test_submit_feedback_success(client, mock_feedback_service):
    """Test successful feedback submission."""
    payload = {
        "prediction_id": "550e8400-e29b-41d4-a716-446655440000",
        "corrected_label": "POSITIVE",
        "comments": "Great!"
    }
    response = client.post("/feedback", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["prediction_id"] == payload["prediction_id"]
    
    # Verify service was called
    mock_feedback_service.submit_feedback.assert_called_once()
    # Verify arguments match
    call_args = mock_feedback_service.submit_feedback.call_args
    feedback_obj = call_args[0][0]
    assert str(feedback_obj.prediction_id) == payload["prediction_id"]
    assert feedback_obj.corrected_label == payload["corrected_label"]

@pytest.mark.unit
def test_submit_feedback_invalid_uuid(client):
    """Test validation error for invalid UUID."""
    payload = {
        "prediction_id": "invalid-uuid",
        "corrected_label": "POSITIVE"
    }
    response = client.post("/feedback", json=payload)
    assert response.status_code == 422

@pytest.mark.unit
def test_submit_feedback_invalid_label(client):
    """Test validation error for invalid label."""
    payload = {
        "prediction_id": "550e8400-e29b-41d4-a716-446655440000",
        "corrected_label": "INVALID_LABEL"
    }
    response = client.post("/feedback", json=payload)
    assert response.status_code == 422

@pytest.mark.unit
def test_submit_feedback_service_failure(client, mock_feedback_service):
    """Test error handling when service fails."""
    mock_feedback_service.submit_feedback.return_value = False
    
    payload = {
        "prediction_id": "550e8400-e29b-41d4-a716-446655440000",
        "corrected_label": "POSITIVE"
    }
    response = client.post("/feedback", json=payload)
    
    assert response.status_code == 503
    assert response.json()["detail"] == "Feedback system unavailable"
