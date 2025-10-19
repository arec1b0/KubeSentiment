"""
Health check utilities.

This module provides health checking functionality for models and services.
"""

from typing import Any, Dict

from app.core.logging import get_logger

logger = get_logger(__name__)


class HealthChecker:
    """
    Health checker for models and services.
    """

    @staticmethod
    def check_model_health(model) -> Dict[str, Any]:
        """
        Check the health of a model.

        Args:
            model: The model instance to check

        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            is_ready = model.is_ready()
            model_info = model.get_model_info()

            return {
                "status": "healthy" if is_ready else "degraded",
                "is_ready": is_ready,
                "details": model_info,
            }

        except Exception as e:
            logger.error("Health check failed", error=str(e), exc_info=True)
            return {
                "status": "unhealthy",
                "is_ready": False,
                "error": str(e),
            }

    @staticmethod
    def check_system_health() -> Dict[str, Any]:
        """
        Check overall system health.

        Returns:
            Dict[str, Any]: System health information
        """
        import psutil
        import torch

        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            health_info = {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
                "torch_available": True,
                "cuda_available": torch.cuda.is_available(),
            }

            # Mark as degraded if resources are constrained
            if cpu_percent > 90 or memory.percent > 90:
                health_info["status"] = "degraded"

            return health_info

        except Exception as e:
            logger.error("System health check failed", error=str(e), exc_info=True)
            return {
                "status": "unknown",
                "error": str(e),
            }

