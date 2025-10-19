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
    """
    Perform a health check of the service.

    Args:
        model: The model service instance
        backend: The backend being used
        settings: Application settings

    Returns:
        HealthResponse: Service health information
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
    """
    Readiness check for Kubernetes.

    Returns 200 if the service is ready to accept traffic.
    """
    if not model.is_ready():
        from app.utils.exceptions import ServiceUnavailableError

        raise ServiceUnavailableError(
            message="Service not ready",
            context={"model_loaded": getattr(model, "_is_loaded", False)},
        )

    return {"status": "ready"}

