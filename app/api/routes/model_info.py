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
    """
    Get information about the loaded model.

    Args:
        model: The model service instance
        backend: The backend being used

    Returns:
        Dict[str, Any]: Model information
    """
    try:
        info = model.get_model_info()
        info["backend"] = backend
        return info
    except Exception as e:
        handle_model_info_error(e)

