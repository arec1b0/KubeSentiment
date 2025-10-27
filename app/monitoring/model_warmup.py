"""
Model Warm-up and Health Check Module for the MLOps sentiment analysis service.

This module implements intelligent model warm-up strategies to ensure optimal
performance from the first inference request. By pre-running inference on
dummy data, it initializes caches and compiles model components, reducing
cold-start latency. It also integrates with health checks to signal service
readiness only after a successful warm-up.
"""

import asyncio
import time
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelWarmupManager:
    """Manages model warm-up operations for optimal cold-start performance.

    This class provides methods to warm up one or more machine learning models
    by running a series of dummy inference requests. This process helps to
    mitigate cold-start latency by ensuring that the model is fully initialized
    and its internal caches are populated before it starts serving live traffic.
    """

    def __init__(self):
        """Initializes the model warm-up manager."""
        self.settings = get_settings()
        self._warmup_complete = False
        self._warmup_stats: Dict[str, Any] = {}
        self._warmup_timestamp: Optional[float] = None

    def is_warmed_up(self) -> bool:
        """Checks if the model warm-up process has completed successfully.

        Returns:
            `True` if the warm-up is complete, `False` otherwise.
        """
        return self._warmup_complete

    def get_warmup_stats(self) -> Dict[str, Any]:
        """Retrieves statistics from the last warm-up run.

        Returns:
            A dictionary containing warm-up metrics, such as the average
            inference time, and the overall status of the warm-up process.
        """
        return {
            "complete": self._warmup_complete,
            "timestamp": self._warmup_timestamp,
            "stats": self._warmup_stats,
        }

    async def warmup_model(self, model, num_iterations: int = 10) -> Dict[str, Any]:
        """Warms up a given model by running dummy inference requests.

        This method sends a series of predefined text inputs to the model's
        `predict` method, measuring the latency of each request. It then
        calculates performance statistics and determines if the model is
        performing within acceptable latency targets.

        Args:
            model: An instance of a model that adheres to the `ModelStrategy`
                protocol.
            num_iterations: The number of warm-up iterations to perform.

        Returns:
            A dictionary containing detailed statistics from the warm-up run.
        """
        logger.info("Starting model warm-up", iterations=num_iterations)
        start_time = time.time()
        warmup_texts = [
            "This is a short test.",
            "This is a slightly longer test sentence for warm-up.",
            "Testing model performance with a medium-length input text.",
        ]
        inference_times = []

        for i in range(num_iterations):
            text = warmup_texts[i % len(warmup_texts)]
            try:
                iter_start = time.time()
                if asyncio.iscoroutinefunction(model.predict):
                    await model.predict(text)
                else:
                    model.predict(text)
                inference_times.append((time.time() - iter_start) * 1000)
            except Exception as e:
                logger.warning("Warm-up iteration failed", iteration=i + 1, error=str(e))

        total_warmup_time = (time.time() - start_time) * 1000
        avg_inference_time = sum(inference_times) / len(inference_times) if inference_times else 0

        self._warmup_stats = {
            "total_warmup_time_ms": round(total_warmup_time, 2),
            "avg_inference_time_ms": round(avg_inference_time, 2),
        }
        self._warmup_complete = avg_inference_time < 100  # Target latency
        self._warmup_timestamp = time.time()

        logger.info("Model warm-up completed", **self._warmup_stats)
        return self._warmup_stats

    async def warmup_multiple_models(
        self, models: Dict[str, Any], iterations_per_model: int = 5
    ) -> Dict[str, Any]:
        """Warms up multiple models concurrently.

        This method is useful in scenarios where the service might need to
        serve multiple different models. It runs the warm-up process for each
        model in parallel to reduce the total startup time.

        Args:
            models: A dictionary mapping model names to model instances.
            iterations_per_model: The number of warm-up iterations to perform
                for each model.

        Returns:
            A dictionary with warm-up statistics for each model.
        """
        logger.info("Starting multi-model warm-up", model_count=len(models))
        tasks = [self.warmup_model(model, iterations_per_model) for model in models.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        warmup_results = {name: res for name, res in zip(models.keys(), results)}
        logger.info("Multi-model warm-up completed")
        return warmup_results


class WarmupHealthCheck:
    """A health check that reports the model's warm-up status.

    This class integrates with the main health check system to ensure that the
    service is not reported as 'ready' until the model warm-up process has
    been successfully completed. This is crucial for preventing traffic from
    being routed to a pod that is not yet ready to serve predictions
    efficiently.
    """

    def __init__(self, warmup_manager: ModelWarmupManager):
        """Initializes the warm-up health check.

        Args:
            warmup_manager: The `ModelWarmupManager` instance to monitor.
        """
        self.warmup_manager = warmup_manager

    def check_warmup_status(self) -> Dict[str, Any]:
        """Checks the current warm-up status of the model.

        Returns:
            A dictionary containing the warm-up status, which can be included
            in a health check response.
        """
        is_ready = self.warmup_manager.is_warmed_up()
        stats = self.warmup_manager.get_warmup_stats()
        return {
            "status": "ready" if is_ready else "warming_up",
            "warmed_up": is_ready,
            "performance": stats.get("stats", {}),
        }

    def is_ready(self) -> bool:
        """Indicates whether the model is ready to serve traffic.

        Returns:
            `True` if the warm-up is complete, `False` otherwise.
        """
        return self.warmup_manager.is_warmed_up()


_warmup_manager: Optional[ModelWarmupManager] = None


def get_warmup_manager() -> ModelWarmupManager:
    """Provides a singleton instance of the `ModelWarmupManager`.

    This factory function ensures that the `ModelWarmupManager` is initialized
    only once, creating a single, shared instance that can be used throughout
    the application.

    Returns:
        The singleton `ModelWarmupManager` instance.
    """
    global _warmup_manager
    if _warmup_manager is None:
        _warmup_manager = ModelWarmupManager()
    return _warmup_manager


def reset_warmup_manager() -> None:
    """Resets the global warm-up manager.

    This function is primarily intended for use in testing scenarios where a
    fresh `ModelWarmupManager` instance is needed for each test case.
    """
    global _warmup_manager
    _warmup_manager = None
