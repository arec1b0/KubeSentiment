"""
Tests for the detailed health check endpoint.
"""

import pytest

from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient

import pytest

from app.main import app

client = TestClient(app)


@patch("app.monitoring.routes.HealthChecker")
@patch("app.monitoring.routes.get_secret_manager")
@patch("app.monitoring.routes.get_model_service")
@pytest.mark.unit
def test_detailed_health_check_healthy(
    mock_get_model_service, mock_get_secret_manager, mock_health_checker
):
    """
    Tests the detailed health check endpoint when all components are healthy.
    """
    # Arrange
    mock_model = MagicMock()
    mock_model.is_ready.return_value = True
    mock_get_model_service.return_value = mock_model

    mock_secret_manager = MagicMock()
    mock_secret_manager.is_healthy.return_value = True
    mock_get_secret_manager.return_value = mock_secret_manager

    mock_checker_instance = mock_health_checker.return_value
    mock_checker_instance.check_model_health.return_value = {
        "status": "healthy",
        "is_ready": True,
        "details": {},
    }
    mock_checker_instance.check_system_health.return_value = {"status": "healthy"}
    mock_checker_instance.check_secrets_backend_health.return_value = {
        "status": "healthy",
        "details": {},
    }

    # Act
    response = client.get("/health/details")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert len(data["dependencies"]) == 3
    for dep in data["dependencies"]:
        assert dep["details"]["status"] == "healthy"


@patch("app.monitoring.routes.HealthChecker")
@patch("app.monitoring.routes.get_secret_manager")
@patch("app.monitoring.routes.get_model_service")
@pytest.mark.unit
def test_detailed_health_check_unhealthy_model(
    mock_get_model_service, mock_get_secret_manager, mock_health_checker
):
    """
    Tests the detailed health check endpoint when the model is unhealthy.
    """
    # Arrange
    mock_model = MagicMock()
    mock_model.is_ready.return_value = False
    mock_get_model_service.return_value = mock_model

    mock_secret_manager = MagicMock()
    mock_secret_manager.is_healthy.return_value = True
    mock_get_secret_manager.return_value = mock_secret_manager

    mock_checker_instance = mock_health_checker.return_value
    mock_checker_instance.check_model_health.return_value = {
        "status": "degraded",
        "is_ready": False,
        "details": {},
        "error": "Model not loaded",
    }
    mock_checker_instance.check_system_health.return_value = {"status": "healthy"}
    mock_checker_instance.check_secrets_backend_health.return_value = {
        "status": "healthy",
        "details": {},
    }

    # Act
    response = client.get("/health/details")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    model_health = next((d for d in data["dependencies"] if d["component_name"] == "model"), None)
    assert model_health is not None
    assert model_health["details"]["status"] == "degraded"
    assert model_health["details"]["error"] == "Model not loaded"


@patch("app.monitoring.routes.HealthChecker")
@patch("app.monitoring.routes.get_secret_manager")
@patch("app.monitoring.routes.get_model_service")
@pytest.mark.unit
def test_detailed_health_check_unhealthy_secrets_backend(
    mock_get_model_service, mock_get_secret_manager, mock_health_checker
):
    """
    Tests the detailed health check endpoint when the secrets backend is unhealthy.
    """
    # Arrange
    mock_model = MagicMock()
    mock_model.is_ready.return_value = True
    mock_get_model_service.return_value = mock_model

    mock_secret_manager = MagicMock()
    mock_secret_manager.is_healthy.return_value = False
    mock_get_secret_manager.return_value = mock_secret_manager

    mock_checker_instance = mock_health_checker.return_value
    mock_checker_instance.check_model_health.return_value = {
        "status": "healthy",
        "is_ready": True,
        "details": {},
    }
    mock_checker_instance.check_system_health.return_value = {"status": "healthy"}
    mock_checker_instance.check_secrets_backend_health.return_value = {
        "status": "unhealthy",
        "details": {},
        "error": "Vault connection failed",
    }

    # Act
    response = client.get("/health/details")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    secrets_health = next(
        (d for d in data["dependencies"] if d["component_name"] == "secrets_backend"),
        None,
    )
    assert secrets_health is not None
    assert secrets_health["details"]["status"] == "unhealthy"
    assert secrets_health["details"]["error"] == "Vault connection failed"
