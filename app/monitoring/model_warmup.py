"""
Model Warm-up and Health Check Module.

Implements intelligent model warm-up strategies to ensure optimal performance
from the first inference request. Integrates with health checks to signal
readiness only after warm-up completion.
"""

import asyncio
import time
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelWarmupManager:
    """Manages model warm-up operations for optimal cold-start performance.

    This class implements warm-up strategies that:
    1. Pre-run inference on dummy data to initialize all caches
    2. Verify model performance meets latency requirements
    3. Report readiness status for health checks
    4. Support gradual warm-up for multiple model versions
    """

    def __init__(self):
        """Initializes the model warm-up manager."""
        self.settings = get_settings()
        self._warmup_complete = False
        self._warmup_stats: Dict[str, Any] = {}
        self._warmup_timestamp: Optional[float] = None

    def is_warmed_up(self) -> bool:  # type: ignore
        """Checks if the model has been warmed up.

        Returns:
            True if warm-up is complete, False otherwise.
        """
        return self._warmup_complete

    def get_warmup_stats(self) -> Dict[str, Any]:
        """Retrieves warm-up statistics.

        Returns:
            Dictionary containing warm-up metrics and status.
        """
        return {
            "complete": self._warmup_complete,
            "timestamp": self._warmup_timestamp,
            "stats": self._warmup_stats,
        }

    async def warmup_model(self, model, num_iterations: int = 10) -> Dict[str, Any]:
        """Warms up a model with dummy inference requests.

        Args:
            model: The model instance to warm up (must have predict method).
            num_iterations: Number of warm-up iterations to perform.

        Returns:
            Dictionary with warm-up statistics.
        """
        logger.info(
            "Starting model warm-up", iterations=num_iterations, model_type=type(model).__name__
        )

        start_time = time.time()

        # Sample warm-up texts with varying lengths
        warmup_texts = [
            "This is a short test.",
            "This is a slightly longer test sentence for warm-up.",
            "Testing model performance with a medium-length input text that contains multiple words and punctuation marks.",
            "A very comprehensive warm-up text that includes various linguistic patterns, multiple clauses, and sufficient complexity to thoroughly exercise the model's tokenization, embedding, and inference pathways.",
            "Quick warmup",  # Short
        ]

        inference_times = []
        successful_iterations = 0
        failed_iterations = 0

        for i in range(num_iterations):
            text = warmup_texts[i % len(warmup_texts)]

            try:
                iter_start = time.time()

                # Run inference
                if asyncio.iscoroutinefunction(model.predict):
                    result = await model.predict(text)
                else:
                    result = model.predict(text)

                iter_duration = (time.time() - iter_start) * 1000
                inference_times.append(iter_duration)
                successful_iterations += 1

                logger.debug(
                    "Warm-up iteration completed",
                    iteration=i + 1,
                    duration_ms=round(iter_duration, 2),
                    label=result.get("label"),
                )

            except Exception as e:
                failed_iterations += 1
                logger.warning("Warm-up iteration failed", iteration=i + 1, error=str(e))

        total_warmup_time = (time.time() - start_time) * 1000

        # Calculate statistics
        if inference_times:
            avg_inference_time = sum(inference_times) / len(inference_times)
            min_inference_time = min(inference_times)
            max_inference_time = max(inference_times)
            p95_inference_time = sorted(inference_times)[int(len(inference_times) * 0.95)]
        else:
            avg_inference_time = 0
            min_inference_time = 0
            max_inference_time = 0
            p95_inference_time = 0

        self._warmup_stats = {
            "total_warmup_time_ms": round(total_warmup_time, 2),
            "iterations": num_iterations,
            "successful": successful_iterations,
            "failed": failed_iterations,
            "avg_inference_time_ms": round(avg_inference_time, 2),
            "min_inference_time_ms": round(min_inference_time, 2),
            "max_inference_time_ms": round(max_inference_time, 2),
            "p95_inference_time_ms": round(p95_inference_time, 2),
        }

        # Check if performance meets targets
        target_latency_ms = 100  # Sub-100ms target
        performance_acceptable = avg_inference_time < target_latency_ms and failed_iterations == 0

        self._warmup_complete = performance_acceptable
        self._warmup_timestamp = time.time()

        logger.info(
            "Model warm-up completed",
            total_time_ms=self._warmup_stats["total_warmup_time_ms"],
            avg_inference_ms=self._warmup_stats["avg_inference_time_ms"],
            p95_inference_ms=self._warmup_stats["p95_inference_time_ms"],
            performance_acceptable=performance_acceptable,
            successful=successful_iterations,
            failed=failed_iterations,
        )

        if not performance_acceptable:
            logger.warning(
                "Model performance below target",
                avg_latency_ms=avg_inference_time,
                target_latency_ms=target_latency_ms,
                failed_iterations=failed_iterations,
            )

        return self._warmup_stats

    async def warmup_multiple_models(
        self, models: Dict[str, Any], iterations_per_model: int = 5
    ) -> Dict[str, Any]:
        """Warms up multiple models concurrently.

        Args:
            models: Dictionary of model_name -> model_instance.
            iterations_per_model: Number of warm-up iterations per model.

        Returns:
            Dictionary with warm-up statistics for each model.
        """
        logger.info("Starting multi-model warm-up", model_count=len(models))

        start_time = time.time()

        # Create warm-up tasks for all models
        tasks = []
        model_names = []

        for model_name, model in models.items():
            tasks.append(self.warmup_model(model, num_iterations=iterations_per_model))
            model_names.append(model_name)

        # Run warm-ups concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Compile results
        warmup_results: Dict[str, Any] = {}
        for model_name, result in zip(model_names, results):
            if isinstance(result, Exception):
                logger.error("Model warm-up failed", model_name=model_name, error=str(result))
                warmup_results[model_name] = {"error": str(result), "complete": False}
            else:
                warmup_results[model_name] = result

        total_time = (time.time() - start_time) * 1000

        logger.info(
            "Multi-model warm-up completed",
            total_time_ms=round(total_time, 2),
            models_count=len(models),
            successful_models=sum(1 for r in warmup_results.values() if not r.get("error")),
        )

        return warmup_results


class WarmupHealthCheck:
    """Health check that includes model warm-up status.

    Integrates with the existing health check system to signal readiness
    only after model warm-up is complete.
    """

    def __init__(self, warmup_manager: ModelWarmupManager):
        """Initializes the warmup health check.

        Args:
            warmup_manager: The ModelWarmupManager instance to check.
        """
        self.warmup_manager = warmup_manager

    def check_warmup_status(self) -> Dict[str, Any]:
        """Checks the model warm-up status.

        Returns:
            Dictionary with warmup status for health checks.
        """
        is_ready = self.warmup_manager.is_warmed_up()
        stats = self.warmup_manager.get_warmup_stats()

        return {
            "status": "ready" if is_ready else "warming_up",
            "warmed_up": is_ready,
            "timestamp": stats.get("timestamp"),
            "performance": (
                {
                    "avg_inference_ms": stats.get("stats", {}).get("avg_inference_time_ms"),
                    "p95_inference_ms": stats.get("stats", {}).get("p95_inference_time_ms"),
                }
                if stats.get("stats")
                else None
            ),
        }

    def is_ready(self) -> bool:
        """Checks if the model is ready (warmed up).

        Returns:
            True if warm-up is complete, False otherwise.
        """
        return self.warmup_manager.is_warmed_up()


# Global warmup manager instance
_warmup_manager: Optional[ModelWarmupManager] = None


def get_warmup_manager() -> ModelWarmupManager:
    """Gets or creates the global warmup manager instance.

    Returns:
        The ModelWarmupManager singleton instance.
    """
    global _warmup_manager
    if _warmup_manager is None:
        _warmup_manager = ModelWarmupManager()
    return _warmup_manager


def reset_warmup_manager() -> None:
    """Resets the global warmup manager (for testing)."""
    global _warmup_manager
    _warmup_manager = None
