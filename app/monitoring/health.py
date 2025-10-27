"""
Health check utilities for the MLOps sentiment analysis service.

This module provides a centralized `HealthChecker` class with methods for
checking the health of various components of the system, including the machine
learning model, the secrets backend, and the underlying system resources.
"""

from typing import Any, Dict

from app.core.logging import get_logger

logger = get_logger(__name__)


class HealthChecker:
    """Provides methods for checking the health of various system components.

    This class centralizes health-checking logic, offering a consistent and
    extensible way to verify the status of different parts of the application.
    Each method returns a dictionary with a standardized structure, making it
    easy to integrate with monitoring and alerting systems.
    """

    @staticmethod
    def check_model_health(model) -> Dict[str, Any]:
        """Checks the health and readiness of a given model instance.

        This method queries the model for its readiness status and detailed
        information, providing a comprehensive overview of its health. A model
        is considered 'healthy' if it is ready to serve predictions.

        Args:
            model: An instance of a class that implements the `ModelStrategy`
                protocol.

        Returns:
            A dictionary containing the model's health status, including its
            readiness state and other details.
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
            logger.error("Model health check failed", error=str(e), exc_info=True)
            return {"status": "unhealthy", "is_ready": False, "error": str(e)}

    @staticmethod
    def check_secrets_backend_health(secret_manager) -> Dict[str, Any]:
        """Checks the health of the secrets management backend.

        This method verifies that the configured secret manager (e.g., HashiCorp
        Vault or environment variables) is accessible and operational.

        Args:
            secret_manager: An instance of a class that implements the
                `SecretManager` protocol.

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
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    def check_system_health() -> Dict[str, Any]:
        """Checks the overall health of the underlying system.

        This method gathers key metrics about the system's resources, such as
        CPU and memory usage. It can be used to detect if the system is under
        heavy load, which might impact the application's performance. A status
        of 'degraded' is reported if resource utilization is high.

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
            if cpu_percent > 90 or memory.percent > 90:
                health_info["status"] = "degraded"
            return health_info
        except Exception as e:
            logger.error("System health check failed", error=str(e), exc_info=True)
            return {"status": "unknown", "error": str(e)}

    @staticmethod
    def check_kafka_health(kafka_consumer) -> Dict[str, Any]:
        """Checks the health of the Kafka consumer.

        This method verifies that the Kafka consumer is running and provides
        key performance metrics, such as the number of messages consumed and
        the current throughput.

        Args:
            kafka_consumer: An instance of `HighThroughputKafkaConsumer`.

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
                    "throughput_tps": metrics.get("throughput_tps", 0.0),
                },
            }
            if is_running and metrics.get("throughput_tps", 0) < 1.0:
                health_info["status"] = "degraded"
            return health_info
        except Exception as e:
            logger.error("Kafka health check failed", error=str(e), exc_info=True)
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    def check_async_batch_health(async_batch_service) -> Dict[str, Any]:
        """Checks the health of the asynchronous batch processing service.

        This method provides insights into the status of the batch service,
        including the number of active jobs and the current queue sizes.

        Args:
            async_batch_service: An instance of `AsyncBatchService`.

        Returns:
            A dictionary containing the health status of the async batch service.
        """
        try:
            if not async_batch_service:
                return {
                    "status": "disabled",
                    "details": {"reason": "Async batch service not initialized"},
                }
            queue_status = async_batch_service.get_job_queue_status()
            is_active = any(size > 0 for size in queue_status.values())
            health_info = {
                "status": "healthy",
                "is_active": is_active,
                "details": {"queue_status": queue_status},
            }
            if not is_active:
                health_info["status"] = "idle"
            return health_info
        except Exception as e:
            logger.error("Async batch health check failed", error=str(e), exc_info=True)
            return {"status": "unhealthy", "error": str(e)}
