"""
Service layer for monitoring and health checks.

This module consolidates business logic for system monitoring, aggregating
health checks from various components and providing unified metrics access.
"""

import time
from typing import Any, Dict

from fastapi import Request

from app.api.schemas.responses import ComponentHealth, HealthDetail
from app.core.config import Settings
from app.core.logging import get_logger
from app.monitoring.health import HealthChecker
from app.monitoring.prometheus import get_metrics as get_prometheus_metrics_data

logger = get_logger(__name__)


class MonitoringService:
    """Service for handling monitoring and health check logic."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.health_checker = HealthChecker()

    async def get_detailed_health(
        self,
        request: Request,
        model: Any,
        secret_manager: Any,
    ) -> Dict[str, Any]:
        """
        Aggregates health status from all major components.
        
        Args:
            request: FastAPI request (to access app state for optional components)
            model: Model service instance
            secret_manager: Secret manager instance
            
        Returns:
            Dictionary with aggregated health data suitable for DetailedHealthResponse
        """
        checks = {
            "model": self.health_checker.check_model_health(model),
            "system": self.health_checker.check_system_health(),
            "secrets_backend": self.health_checker.check_secrets_backend_health(secret_manager),
        }

        # Optional components
        if self.settings.kafka.kafka_enabled:
            checks["kafka"] = self.health_checker.check_kafka_health(
                getattr(request.app.state, "kafka_consumer", None)
            )
        
        if self.settings.performance.async_batch_enabled:
            checks["async_batch"] = self.health_checker.check_async_batch_health(
                getattr(request.app.state, "async_batch_service", None)
            )

        overall_status = "healthy"
        dependencies = []
        for name, result in checks.items():
            status = result.get("status", "unhealthy")
            if status != "healthy":
                overall_status = "unhealthy"
            
            # Create dependency dict structure matching ComponentHealth schema
            dependencies.append(ComponentHealth(
                component_name=name,
                details=HealthDetail(
                    status=status,
                    error=result.get("error")
                )
            ))

        return {
            "status": overall_status,
            "version": self.settings.server.app_version,
            "timestamp": time.time(),
            "dependencies": dependencies,
        }

    async def get_simple_health(self, model: Any, secret_manager: Any) -> Dict[str, Any]:
        """
        Performs a high-level health check (liveness).
        """
        model_ready = model.is_ready()
        secrets_healthy = secret_manager.is_healthy()
        status = "healthy" if model_ready and secrets_healthy else "unhealthy"
        return {
            "status": status,
            "model_status": "available" if model_ready else "unavailable"
        }

    async def get_readiness(self, model: Any) -> bool:
        """Checks if the service is ready to accept traffic."""
        return model.is_ready()

    def get_prometheus_metrics(self) -> Any:
        """Retrieves Prometheus metrics."""
        return get_prometheus_metrics_data()
