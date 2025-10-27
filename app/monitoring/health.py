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
    @staticmethod
    def check_secrets_backend_health(secret_manager) -> Dict[str, Any]:
        """Checks the health of the secrets management backend.

        Args:
            secret_manager: An instance of a `SecretManager`.

        Returns:
            A dictionary containing the health status of the secrets backend.
        """
        try:
            is_healthy = secret_manager.is_healthy()
            health_info = secret_manager.get_health_info()

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "details": health_info,
            }
        except Exception as e:
            logger.error("Secrets backend health check failed", error=str(e), exc_info=True)
            return {
                "status": "unhealthy",
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

    @staticmethod
    def check_kafka_health(kafka_consumer) -> Dict[str, Any]:
        """Checks the health of the Kafka consumer.

        Args:
            kafka_consumer: An instance of HighThroughputKafkaConsumer.

        Returns:
            A dictionary containing the health status of the Kafka consumer.
        """
        try:
            if not kafka_consumer:
                return {
                    "status": "disabled",
                    "details": {"reason": "Kafka consumer not initialized"},
                }

            is_running = kafka_consumer.is_running()
            metrics = kafka_consumer.get_metrics()

            health_info = {
                "status": "healthy" if is_running else "unhealthy",
                "is_running": is_running,
                "details": {
                    "messages_consumed": metrics.get("messages_consumed", 0),
                    "messages_processed": metrics.get("messages_processed", 0),
                    "throughput_tps": metrics.get("throughput_tps", 0.0),
                    "consumer_threads": metrics.get("consumer_threads", 0),
                    "running": metrics.get("running", False),
                },
            }

            # Mark as degraded if throughput is very low or no recent activity
            if is_running and metrics.get("throughput_tps", 0) < 1.0:
                health_info["status"] = "degraded"

            return health_info

        except Exception as e:
            logger.error("Kafka health check failed", error=str(e), exc_info=True)
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    @staticmethod
    def check_async_batch_health(async_batch_service) -> Dict[str, Any]:
        """Checks the health of the async batch service.

        Args:
            async_batch_service: An instance of AsyncBatchService.

        Returns:
            A dictionary containing the health status of the async batch service.
        """
        try:
            if not async_batch_service:
                return {
                    "status": "disabled",
                    "details": {"reason": "Async batch service not initialized"},
                }

            # Get basic metrics to check if service is responsive
            try:
                # For health check, we'll get metrics synchronously or handle async
                if hasattr(async_batch_service, 'get_batch_metrics'):
                    # Check if method is async
                    import asyncio
                    if asyncio.iscoroutinefunction(async_batch_service.get_batch_metrics):
                        # If async, we'll just check basic properties instead
                        metrics = None
                    else:
                        metrics = async_batch_service.get_batch_metrics()
                else:
                    metrics = None

                queue_status = async_batch_service.get_job_queue_status()
            except Exception:
                # If metrics fail, assume service is unhealthy
                metrics = None
                queue_status = {"high_priority": 0, "medium_priority": 0, "low_priority": 0, "total": 0}

            # Check if service is processing jobs
            active_jobs = metrics.active_jobs if metrics else 0
            total_jobs = metrics.total_jobs if metrics else 0
            throughput = metrics.average_throughput_tps if metrics else 0.0
            efficiency = metrics.processing_efficiency if metrics else 0.0
            is_active = active_jobs > 0 or any(size > 0 for size in queue_status.values())

            health_info = {
                "status": "healthy",
                "is_active": is_active,
                "details": {
                    "total_jobs": total_jobs,
                    "active_jobs": active_jobs,
                    "queue_status": queue_status,
                    "throughput_tps": throughput,
                    "processing_efficiency": efficiency,
                },
            }

            # Mark as degraded if no activity for extended period
            if not is_active and total_jobs == 0:
                health_info["status"] = "degraded"

            return health_info

        except Exception as e:
            logger.error("Async batch health check failed", error=str(e), exc_info=True)
            return {
                "status": "unhealthy",
                "error": str(e),
            }
