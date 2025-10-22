"""
Health check utilities.

This module provides health checking functionality for models and services.
"""

from typing import Any, Dict

from app.core.logging import get_logger

logger = get_logger(__name__)


class HealthChecker:
    """Provides methods for checking the health of system components.

    This class centralizes health-checking logic, offering a consistent way to
    verify the status of different parts of the application, such as machine
    learning models and the underlying system resources.
    """

    @staticmethod
    def check_model_health(model) -> Dict[str, Any]:
        """Checks the health and readiness of a given model instance.

        This method queries the model for its readiness status and detailed
        information, providing a comprehensive overview of its health.

        Args:
            model: An instance of a model that adheres to the `ModelStrategy`
                protocol.

        Returns:
            A dictionary containing the model's health status.
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
        """Checks the overall health of the system.

        This method gathers key metrics about the system's resources, such as
        CPU and memory usage. It can be used to detect if the system is under
        heavy load, which might impact the application's performance.

        Returns:
            A dictionary containing system health metrics.
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
