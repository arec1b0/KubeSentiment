"""
Stream processor with intelligent batching for optimized inference.

This module implements dynamic batching and stream processing capabilities
to significantly reduce latency through vectorized operations. It is designed
for high-throughput environments where individual prediction requests can be
efficiently grouped together for model inference.
"""

import asyncio
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.models.stream_models import BatchConfig, PendingRequest
from app.services.feature_processor import FeatureProcessor

try:  # pragma: no cover - allow running without full settings stack
    from app.core.config import get_settings
    from app.interfaces.stream_interface import IStreamProcessor
except Exception:  # pragma: no cover - fallback stub for lightweight tests

    def get_settings():  # type: ignore[misc]
        class _Fallback:
            app_version = "test"
            data_dir = "./data"

        return _Fallback()

    class IStreamProcessor:  # type: ignore[no-redef]
        """Fallback interface for lightweight tests"""

        pass


try:  # pragma: no cover - optional dependency in tests
    from app.core.logging import get_contextual_logger, get_logger
except Exception:  # pragma: no cover - fallback to stdlib logging
    from app.utils.logging_adapters import (
        get_fallback_contextual_logger as get_contextual_logger,
        get_fallback_logger as get_logger,
    )


try:  # pragma: no cover - optional dependency in tests
    from app.features.feature_engineering import get_feature_engineer
except Exception:  # pragma: no cover

    def get_feature_engineer():  # type: ignore[misc]
        return None


try:  # pragma: no cover
    from app.features.online_normalization import OnlineStandardScaler
except Exception:  # pragma: no cover

    class OnlineStandardScaler:  # type: ignore[override]
        def __init__(self) -> None:
            self.n_samples_seen_ = 0

        def load_state(self, *_: Any, **__: Any) -> None:  # noqa: D401 - simple stub
            """No-op for tests when scaler is unavailable."""

        def save_state(self, *_: Any, **__: Any) -> None:
            """No-op save implementation for tests."""

        def partial_fit(self, features: Any) -> None:
            length = len(getattr(features, "index", features))
            self.n_samples_seen_ += int(length)

        def transform(self, features: Any) -> Any:
            return features


from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from app.models.base import ModelStrategy
else:
    ModelStrategy = Any  # type: ignore[misc, assignment]

logger = get_logger(__name__)


class StreamProcessor(IStreamProcessor):
    """Processes prediction requests with intelligent, dynamic batching.

    This processor collects incoming prediction requests and groups them into
    batches for efficient, vectorized inference. It uses a dynamic batching
    strategy with configurable timeouts to balance latency and throughput,
    making it suitable for high-performance, real-time applications.

    The processor also integrates feature engineering and online normalization,
    ensuring that the data fed to the model is consistently preprocessed.

    Attributes:
        model: An instance of a model strategy used for making predictions.
        config: The configuration for batch processing behavior.
        queue: A deque holding the pending requests to be processed.
    """

    def __init__(self, model: ModelStrategy, config: Optional[BatchConfig] = None):
        """Initializes the StreamProcessor.

        Sets up the model, batching configuration, request queue, and other
        internal state needed for processing. It also initializes the feature
        engineering and online normalization components.

        Args:
            model: An instance of a model strategy (e.g., ONNX, scikit-learn)
                   that will be used for making predictions.
            config: An optional BatchConfig object to customize batching
                    behavior. If not provided, default settings are used.
        """
        self.model = model
        self.config = config or BatchConfig()
        self.queue: deque[PendingRequest] = deque()
        self._processing = False
        self._lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None
        self._stats = {
            "total_requests": 0,
            "total_batches": 0,
            "total_processing_time_ms": 0.0,
            "avg_batch_size": 0.0,
            "cache_hits": 0,
        }

        settings = get_settings()
        self.logger = get_logger(__name__)

        self.feature_engineer = get_feature_engineer()
        self.online_scaler = OnlineStandardScaler()
        data_dir = getattr(settings, "data_dir", "./data")
        self.scaler_state_path = Path(data_dir) / "scaler_state.json"

        try:
            self.online_scaler.load_state(str(self.scaler_state_path))
            self.logger.info("Loaded existing scaler state", path=str(self.scaler_state_path))
        except Exception as e:
            self.logger.info("No existing scaler state found, starting fresh", error=str(e))

    async def predict_async(self, text: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Adds a prediction request to the batch queue and awaits the result.

        This method queues the request and returns a future that will be
        resolved when the batch containing this request is processed. It is
        the primary entry point for individual prediction requests.

        Args:
            text: The input text to be analyzed.
            request_id: An optional unique identifier for tracking the request.
                        If not provided, a UUID will be generated.

        Returns:
            A dictionary containing the prediction results, including the
            predicted label, score, and other metadata.
        """
        if request_id is None:
            import uuid

            request_id = str(uuid.uuid4())

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        pending_request = PendingRequest(
            text=text, future=future, timestamp=time.time(), request_id=request_id
        )

        async with self._lock:
            self.queue.append(pending_request)
            self._stats["total_requests"] += 1

            if not self._processing:
                self._batch_task = asyncio.create_task(self._process_batches())

        return await future

    async def _process_batches(self) -> None:
        """The main batch processing loop.

        This method continuously monitors the request queue and processes batches
        of requests. It uses intelligent batching with timeout-based and
        size-based triggers to optimize performance. The loop runs as an
        asyncio task.
        """
        self._processing = True
        try:
            while True:
                await asyncio.sleep(0.001)

                should_process, batch = await self._should_process_batch()
                if should_process and batch:
                    await self._process_single_batch(batch)

                async with self._lock:
                    if len(self.queue) == 0:
                        await asyncio.sleep(0.1)
                        if len(self.queue) == 0:
                            break
        finally:
            self._processing = False

    async def _should_process_batch(self) -> Tuple[bool, List[PendingRequest]]:
        """Determines if a batch of requests should be processed.

        This method checks for several conditions to decide whether to form a
        batch from the current queue. The criteria are:
        - The queue has reached the maximum batch size.
        - The oldest request in the queue has exceeded the maximum wait time.
        - The queue has reached the minimum batch size and there is a period
          of inactivity.

        Returns:
            A tuple containing a boolean indicating whether to process a batch,
            and a list of PendingRequest objects to be processed.
        """
        async with self._lock:
            if not self.queue:
                return False, []

            current_time = time.time()
            oldest_request = self.queue[0]
            wait_time_ms = (current_time - oldest_request.timestamp) * 1000

            batch_size = min(len(self.queue), self.config.max_batch_size)
            size_trigger = batch_size >= self.config.max_batch_size
            timeout_trigger = wait_time_ms >= self.config.max_wait_time_ms
            min_size_trigger = batch_size >= self.config.min_batch_size

            should_process = (
                size_trigger
                or timeout_trigger
                or (min_size_trigger and wait_time_ms >= self.config.max_wait_time_ms * 0.5)
            )

            if should_process:
                batch = [self.queue.popleft() for _ in range(batch_size) if self.queue]
                return True, batch

            return False, []

    async def _process_single_batch(self, batch: List[PendingRequest]) -> None:
        """Processes a single batch of prediction requests.

        This method handles feature engineering, online normalization, and
        vectorized prediction for a given batch. It also manages error handling
        and ensures that all request futures are resolved.

        Args:
            batch: A list of PendingRequest objects to be processed together.
        """
        batch_logger = get_contextual_logger(
            __name__, operation="stream_batch_processing", batch_size=len(batch)
        )
        start_time = time.time()

        try:
            texts = [req.text for req in batch]
            batch_logger.debug(
                "Processing batch", batch_size=len(batch), queue_size=len(self.queue)
            )

            self._process_features(texts, batch_logger)
            results = self.model.predict_batch(texts)
            self._finalize_batch_processing(batch, results, start_time, batch_logger)
        except Exception as e:
            batch_logger.error("Batch processing failed", error=str(e), exc_info=True)
            for req in batch:
                if not req.future.done():
                    req.future.set_exception(e)

    def _process_features(self, texts: List[str], batch_logger) -> None:
        """Processes and normalizes features for a batch of texts.

        This method extracts numerical features from the texts, updates the
        online scaler with the new data, and then normalizes the features
        before prediction.

        Args:
            texts: A list of input texts for feature extraction.
            batch_logger: A contextual logger for logging batch-specific information.
        """
        FeatureProcessor.process_features(
            texts, self.feature_engineer, self.online_scaler, batch_logger
        )
        # Save scaler state after processing
        try:
            self.online_scaler.save_state(str(self.scaler_state_path))
        except Exception:
            pass  # Logging already handled in FeatureProcessor

    def _finalize_batch_processing(
        self,
        batch: List[PendingRequest],
        results: List[Dict[str, Any]],
        start_time: float,
        batch_logger,
    ) -> None:
        """Finalizes the processing of a batch and updates statistics.

        This method calculates performance metrics for the batch, resolves the
        asyncio futures for each request, and logs the results.

        Args:
            batch: The list of PendingRequest objects that were processed.
            results: The list of prediction results from the model.
            start_time: The timestamp when the batch processing started.
            batch_logger: A contextual logger for batch-specific information.
        """
        processing_time = (time.time() - start_time) * 1000
        self._stats["total_batches"] += 1
        self._stats["total_processing_time_ms"] += processing_time
        alpha = 0.1
        self._stats["avg_batch_size"] = (
            alpha * len(batch) + (1 - alpha) * self._stats["avg_batch_size"]
        )
        cache_hits = sum(1 for r in results if r.get("cached", False))
        self._stats["cache_hits"] += cache_hits

        for req, result in zip(batch, results):
            if not req.future.done():
                req.future.set_result(result)

        batch_logger.info(
            "Batch processed successfully",
            batch_size=len(batch),
            processing_time_ms=round(processing_time, 2),
            throughput_requests_per_sec=(
                round(len(batch) / (processing_time / 1000), 2)
                if processing_time > 0
                else float("inf")
            ),
            cache_hits=cache_hits,
            cache_hit_rate=round(cache_hits / len(batch), 2) if len(batch) > 0 else 0.0,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Retrieves the current processing statistics.

        This method provides a snapshot of the processor's performance, including
        metrics like the number of requests processed, average batch size, and
        cache hit rate.

        Returns:
            A dictionary containing various performance metrics.
        """
        avg_processing_time = (
            self._stats["total_processing_time_ms"] / self._stats["total_batches"]
            if self._stats["total_batches"] > 0
            else 0.0
        )
        return {
            "total_requests": self._stats["total_requests"],
            "total_batches": self._stats["total_batches"],
            "avg_batch_size": round(self._stats["avg_batch_size"], 2),
            "avg_processing_time_ms": round(avg_processing_time, 2),
            "current_queue_size": len(self.queue),
            "is_processing": self._processing,
            "cache_hits": self._stats["cache_hits"],
            "cache_hit_rate": round(
                (
                    self._stats["cache_hits"] / self._stats["total_requests"]
                    if self._stats["total_requests"] > 0
                    else 0.0
                ),
                2,
            ),
        }

    def reset_stats(self) -> None:
        """Resets the processing statistics to their initial state."""
        self._stats = {
            "total_requests": 0,
            "total_batches": 0,
            "total_processing_time_ms": 0.0,
            "avg_batch_size": 0.0,
            "cache_hits": 0,
        }

    async def shutdown(self) -> None:
        """Gracefully shuts down the stream processor.

        This method ensures that any remaining requests in the queue are
        processed before stopping the batch processing task.
        """
        logger.info("Shutting down stream processor", queue_size=len(self.queue))
        while self.queue:
            async with self._lock:
                if not self.queue:
                    break
                batch_size = min(len(self.queue), self.config.max_batch_size)
                batch = [self.queue.popleft() for _ in range(batch_size) if self.queue]
            if batch:
                await self._process_single_batch(batch)

        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
        logger.info("Stream processor shutdown complete")

    async def predict_async_batch(self, texts: List[str], batch_id: str) -> List[Dict[str, Any]]:
        """Processes a batch of texts asynchronously for high throughput.

        This method is optimized for processing pre-formed batches of requests,
        such as those coming from a Kafka consumer. It bypasses the individual
        request queueing mechanism for better performance.

        Args:
            texts: A list of texts to be processed.
            batch_id: A unique identifier for the batch, used for logging.

        Returns:
            A list of prediction result dictionaries.
        """
        batch_logger = get_contextual_logger(
            __name__,
            operation="async_batch_processing",
            batch_id=batch_id,
            batch_size=len(texts),
        )
        try:
            results = self.model.predict_batch(texts)
            batch_logger.info(
                "Async batch processed successfully",
                batch_size=len(texts),
                batch_id=batch_id,
            )
            return results
        except Exception as e:
            batch_logger.error(
                "Async batch processing failed",
                batch_id=batch_id,
                error=str(e),
                exc_info=True,
            )
            error_result = {
                "label": "ERROR",
                "score": 0.0,
                "error": str(e),
                "inference_time_ms": 0.0,
                "model_name": "stream_processor",
                "text_length": 0,
                "backend": "async_batch",
                "cached": False,
            }
            return [error_result for _ in texts]
