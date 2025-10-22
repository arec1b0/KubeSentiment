"""
Health check endpoints.
"""

import time

from fastapi import APIRouter, Depends

from app.api.schemas.responses import HealthResponse
from app.core.config import Settings, get_settings
from app.core.dependencies import get_model_backend, get_model_service

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Check the health status of the service and model availability.",
)
async def health_check(
    model=Depends(get_model_service),
    backend: str = Depends(get_model_backend),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Performs a comprehensive health check of the service.

    This endpoint verifies the overall health of the application, including
    the status of the machine learning model. It's designed to be used by
    monitoring systems to check the service's operational status.

    Args:
        model: The model service instance, injected as a dependency.
        backend: The name of the model backend in use.
        settings: The application's configuration settings.

    Returns:
        A `HealthResponse` object containing detailed health information.
    """
    model_status = "available" if model.is_ready() else "unavailable"

    return HealthResponse(
        status="healthy",
        model_status=model_status,
        version=settings.app_version,
        backend=backend,
        timestamp=time.time(),
    )


@router.get(
    "/ready",
    summary="Readiness check",
    description="Kubernetes readiness probe endpoint.",
)
async def readiness_check(
    model=Depends(get_model_service),
):
    """Checks if the service is ready to accept incoming traffic.

    This endpoint is intended for use as a Kubernetes readiness probe. It
    succeeds only if the machine learning model is loaded and ready to serve
    predictions. If the model is not ready, it returns a 503 Service
    Unavailable error.

    Args:
        model: The model service instance, injected as a dependency.

    Returns:
        A dictionary with a "status" key indicating readiness.

    Raises:
        ServiceUnavailableError: If the model is not loaded and ready.
    """
    if not model.is_ready():
        from app.utils.exceptions import ServiceUnavailableError

        raise ServiceUnavailableError(
            message="Service not ready",
            context={"model_loaded": getattr(model, "_is_loaded", False)},
        )

    return {"status": "ready"}
