"""
Model information endpoints.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.core.dependencies import get_model_backend, get_model_service
from app.utils.error_handlers import handle_model_info_error

router = APIRouter()


@router.get(
    "/model-info",
    summary="Model information",
    description="Get detailed information about the loaded model.",
)
async def get_model_info(
    model=Depends(get_model_service),
    backend: str = Depends(get_model_backend),
) -> Dict[str, Any]:
    """Retrieves detailed information about the currently loaded model.

    This endpoint provides metadata about the machine learning model that is
    serving predictions, such as its name, version, and other relevant
    details.

    Args:
        model: The model service instance, injected as a dependency.
        backend: The name of the model backend in use.

    Returns:
        A dictionary containing detailed information about the model.
    """
    try:
        info = model.get_model_info()
        info["backend"] = backend
        return info
    except Exception as e:
        handle_model_info_error(e)
