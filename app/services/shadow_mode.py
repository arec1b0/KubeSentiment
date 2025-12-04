"""
Shadow Mode Service for Dark Launch Deployments.

This module provides the ShadowModeService, which enables running a candidate
(shadow) model alongside the primary production model. Shadow predictions are
processed asynchronously and logged for comparison, without affecting the
response returned to users.

This is a key MLOps pattern for:
- Risk-free validation of new models on production traffic
- A/B testing model versions without user impact
- Performance comparison between model versions
- Regression detection before full rollout
"""

import asyncio
import random
import time
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.base import ModelStrategy
from app.monitoring.prometheus import (
    SHADOW_PREDICTION_DURATION,
    SHADOW_PREDICTION_MATCHES,
    SHADOW_PREDICTION_MISMATCHES,
    SHADOW_PREDICTIONS_TOTAL,
)

logger = get_logger(__name__)


class ShadowModeService:
    """Manages shadow model predictions for dark launch deployments.

    This service handles the lifecycle of a shadow (candidate) model and
    provides methods to dispatch shadow predictions asynchronously. It
    compares shadow predictions with primary predictions and logs the
    results for analysis.

    Attributes:
        settings: Application configuration settings.
        shadow_model: The shadow model instance.
        primary_model: Reference to the primary production model.
        enabled: Whether shadow mode is currently active.
    """

    def __init__(
        self,
        settings: Settings,
        primary_model: ModelStrategy,
        shadow_model: ModelStrategy | None = None,
    ):
        """Initialize the Shadow Mode Service.

        Args:
            settings: Application configuration settings.
            primary_model: The primary production model.
            shadow_model: Optional pre-loaded shadow model. If not provided,
                the service will attempt to load it based on settings.
        """
        self.settings = settings
        self.primary_model = primary_model
        self.shadow_model = shadow_model
        self.enabled = settings.mlops.shadow_mode_enabled
        self._started = False
        self._pending_tasks: set = set()

        logger.info(
            "Shadow Mode Service initialized",
            enabled=self.enabled,
            shadow_model_name=settings.mlops.shadow_model_name,
            traffic_percentage=settings.mlops.shadow_traffic_percentage,
        )

    async def start(self) -> None:
        """Start the shadow mode service and load the shadow model if needed."""
        if self._started:
            return

        if not self.enabled:
            logger.info("Shadow mode is disabled, skipping initialization")
            self._started = True
            return

        if self.shadow_model is None:
            await self._load_shadow_model()

        self._started = True
        logger.info("Shadow Mode Service started")

    async def stop(self) -> None:
        """Stop the shadow mode service and cleanup pending tasks."""
        if not self._started:
            return

        # Wait for pending shadow predictions to complete (with timeout)
        if self._pending_tasks:
            logger.info(
                "Waiting for pending shadow predictions to complete",
                pending_count=len(self._pending_tasks),
            )
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._pending_tasks, return_exceptions=True),
                    timeout=5.0,
                )
            except TimeoutError:
                logger.warning("Timeout waiting for shadow predictions to complete")

        self._started = False
        logger.info("Shadow Mode Service stopped")

    async def _load_shadow_model(self) -> None:
        """Load the shadow model based on configuration."""
        from app.models.factory import ModelFactory

        shadow_model_name = self.settings.mlops.shadow_model_name
        if not shadow_model_name:
            logger.warning("Shadow mode enabled but no shadow_model_name configured")
            self.enabled = False
            return

        try:
            backend = self.settings.mlops.shadow_model_backend
            self.shadow_model = ModelFactory.create_model(
                backend=backend,
                model_name=shadow_model_name,
            )

            if self.shadow_model.is_ready():
                logger.info(
                    "Shadow model loaded successfully",
                    model_name=shadow_model_name,
                    backend=backend,
                )
            else:
                logger.error("Shadow model failed to load, disabling shadow mode")
                self.enabled = False
                self.shadow_model = None

        except Exception as e:
            logger.error(
                "Failed to load shadow model",
                error=str(e),
                model_name=shadow_model_name,
                exc_info=True,
            )
            self.enabled = False
            self.shadow_model = None

    def should_shadow(self) -> bool:
        """Determine if the current request should be shadowed.

        Uses random sampling based on the configured traffic percentage.

        Returns:
            True if this request should be sent to the shadow model.
        """
        if not self.enabled or self.shadow_model is None:
            return False

        return random.random() * 100 < self.settings.mlops.shadow_traffic_percentage

    async def dispatch_shadow_prediction(
        self,
        text: str,
        primary_result: dict[str, Any],
        prediction_id: str,
    ) -> None:
        """Dispatch a shadow prediction asynchronously.

        This method creates a background task to run the shadow prediction,
        compare results with the primary prediction, and log metrics.

        Args:
            text: The input text for prediction.
            primary_result: The result from the primary model.
            prediction_id: The unique ID for this prediction.
        """
        if not self.enabled or self.shadow_model is None:
            return

        if self.settings.mlops.shadow_async_dispatch:
            # Fire and forget - create task and track it
            task = asyncio.create_task(
                self._run_shadow_prediction(text, primary_result, prediction_id)
            )
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)
        else:
            # Synchronous dispatch (blocks response)
            await self._run_shadow_prediction(text, primary_result, prediction_id)

    async def _run_shadow_prediction(
        self,
        text: str,
        primary_result: dict[str, Any],
        prediction_id: str,
    ) -> None:
        """Execute shadow prediction and compare with primary result.

        Args:
            text: The input text for prediction.
            primary_result: The result from the primary model.
            prediction_id: The unique ID for this prediction.
        """
        start_time = time.time()

        try:
            # Run prediction in executor to avoid blocking
            loop = asyncio.get_running_loop()
            shadow_result = await loop.run_in_executor(None, self.shadow_model.predict, text)

            inference_time = (time.time() - start_time) * 1000  # ms

            # Record metrics
            SHADOW_PREDICTIONS_TOTAL.inc()
            SHADOW_PREDICTION_DURATION.observe(inference_time / 1000)

            # Compare results
            primary_label = primary_result.get("label")
            shadow_label = shadow_result.get("label")
            labels_match = primary_label == shadow_label

            if labels_match:
                SHADOW_PREDICTION_MATCHES.inc()
            else:
                SHADOW_PREDICTION_MISMATCHES.inc()

            # Log comparison if enabled
            if self.settings.mlops.shadow_log_comparisons:
                self._log_comparison(
                    prediction_id=prediction_id,
                    primary_result=primary_result,
                    shadow_result=shadow_result,
                    labels_match=labels_match,
                    shadow_inference_time_ms=inference_time,
                )

        except Exception as e:
            logger.error(
                "Shadow prediction failed",
                prediction_id=prediction_id,
                error=str(e),
                exc_info=True,
            )

    def _log_comparison(
        self,
        prediction_id: str,
        primary_result: dict[str, Any],
        shadow_result: dict[str, Any],
        labels_match: bool,
        shadow_inference_time_ms: float,
    ) -> None:
        """Log the comparison between primary and shadow predictions.

        Args:
            prediction_id: Unique prediction identifier.
            primary_result: Result from the primary model.
            shadow_result: Result from the shadow model.
            labels_match: Whether the labels match.
            shadow_inference_time_ms: Shadow model inference time in ms.
        """
        primary_score = primary_result.get("score", 0)
        shadow_score = shadow_result.get("score", 0)
        score_diff = abs(primary_score - shadow_score)

        log_data = {
            "prediction_id": prediction_id,
            "model_mode": "shadow_comparison",
            "primary_label": primary_result.get("label"),
            "shadow_label": shadow_result.get("label"),
            "labels_match": labels_match,
            "primary_score": primary_score,
            "shadow_score": shadow_score,
            "score_difference": score_diff,
            "primary_inference_ms": primary_result.get("inference_time_ms"),
            "shadow_inference_ms": shadow_inference_time_ms,
            "shadow_model_name": self.settings.mlops.shadow_model_name,
        }

        if labels_match:
            logger.info("Shadow prediction matches primary", **log_data)
        else:
            logger.warning("Shadow prediction DIFFERS from primary", **log_data)


# Singleton instance
_shadow_mode_service: ShadowModeService | None = None


def get_shadow_mode_service() -> ShadowModeService | None:
    """Get the global shadow mode service instance.

    Returns:
        The ShadowModeService instance, or None if not initialized.
    """
    return _shadow_mode_service


def initialize_shadow_mode_service(
    settings: Settings,
    primary_model: ModelStrategy,
    shadow_model: ModelStrategy | None = None,
) -> ShadowModeService:
    """Initialize and return the global shadow mode service.

    Args:
        settings: Application configuration settings.
        primary_model: The primary production model.
        shadow_model: Optional pre-loaded shadow model.

    Returns:
        The initialized ShadowModeService instance.
    """
    global _shadow_mode_service  # noqa: PLW0603
    _shadow_mode_service = ShadowModeService(
        settings=settings,
        primary_model=primary_model,
        shadow_model=shadow_model,
    )
    return _shadow_mode_service
