"""
API route handlers.
"""

from fastapi import APIRouter

from app.api.routes import model_info, predictions

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(predictions.router, tags=["Predictions"])
router.include_router(model_info.router, tags=["Model Info"])

__all__ = ["router"]

