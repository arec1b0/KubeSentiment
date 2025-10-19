"""
API layer for the MLOps sentiment analysis service.

This module contains all API-related components including routes,
middleware, and request/response schemas.
"""

from app.api.routes import router

__all__ = ["router"]

