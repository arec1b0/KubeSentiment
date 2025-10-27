"""
Stream processor with intelligent batching for optimized inference.

This module implements dynamic batching and stream processing capabilities
to significantly reduce latency through vectorized operations.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.logging import get_contextual_logger, get_logger
from app.models.base import ModelStrategy

logger = get_logger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing behavior.

    Attributes:
        max_batch_size: Maximum number of items to process in a single batch.
        max_wait_time_ms: Maximum time to wait for batch to fill (milliseconds).
        min_batch_size: Minimum batch size before processing (for efficiency).
        dynamic_batching: Enable dynamic batch size adjustment based on load.
    """
    max_batch_size: int = 32
    max_wait_time_ms: float = 50.0  # 50ms max wait
    min_batch_size: int = 1
    dynamic_batching: bool = True


@dataclass
class PendingRequest:
    """Represents a pending prediction request in the batch queue.

    Attributes:
        text: The input text to be analyzed.
        future: Asyncio future to resolve when prediction completes.
        timestamp: Time when request was added to queue.
        request_id: Unique identifier for the request.
    """
    text: str
    future: asyncio.Future
    timestamp: float
    request_id: str


class StreamProcessor:
    """Processes prediction requests with intelligent batching.

    This processor collects incoming prediction requests and batches them
    together for efficient vectorized inference. It uses dynamic batching
    with configurable timeouts to balance latency and throughput.

    Attributes:
        model: The model strategy instance for making predictions.
        config: Batch processing configuration.
        queue: Queue of pending requests waiting to be processed.
    """

    def __init__(
        self,
        model: ModelStrategy,
        config: Optional[BatchConfig] = None
    ):
        """Initializes the stream processor.

        Args:
            model: An instance of a model strategy for predictions.
            config: Batch processing configuration. Uses defaults if not provided.
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

    async def predict_async(self, text: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Adds a prediction request to the batch queue.

        This method queues the request and returns a future that will be
        resolved when the batch containing this request is processed.

        Args:
            text: The input text to be analyzed.
            request_id: Optional unique identifier for tracking.

        Returns:
            A dictionary containing the prediction results.
        """
        if request_id is None:
            import uuid
            request_id = str(uuid.uuid4())

        # Create a future for this request
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        # Create pending request
        pending_request = PendingRequest(
            text=text,
            future=future,
            timestamp=time.time(),
            request_id=request_id
        )

        # Add to queue
        async with self._lock:
            self.queue.append(pending_request)
            self._stats["total_requests"] += 1

            # Start batch processor if not already running
            if not self._processing:
                self._batch_task = asyncio.create_task(self._process_batches())

        # Wait for result
        result = await future
        return result

    async def _process_batches(self) -> None:
        """Main batch processing loop.

        This method continuously processes batches of requests from the queue,
        using intelligent batching with timeout-based and size-based triggers.
        """
        self._processing = True

        try:
            while True:
                # Wait for requests to accumulate
                await asyncio.sleep(0.001)  # 1ms check interval

                # Check if we should process a batch
                should_process, batch = await self._should_process_batch()

                if should_process and batch:
                    await self._process_single_batch(batch)

                # If queue is empty and no activity, stop processing loop
                async with self._lock:
                    if len(self.queue) == 0:
                        await asyncio.sleep(0.1)  # Wait a bit longer
                        if len(self.queue) == 0:
                            break

        finally:
            self._processing = False

    async def _should_process_batch(self) -> Tuple[bool, List[PendingRequest]]:
        """Determines if a batch should be processed now.

        Uses multiple criteria:
        - Max batch size reached
        - Max wait time exceeded for oldest request
        - Queue has minimum batch size and recent inactivity

        Returns:
            A tuple of (should_process, batch_requests).
        """
        async with self._lock:
            if len(self.queue) == 0:
                return False, []

            current_time = time.time()
            oldest_request = self.queue[0]
            wait_time_ms = (current_time - oldest_request.timestamp) * 1000

            # Determine batch size to process
            batch_size = min(len(self.queue), self.config.max_batch_size)

            # Trigger conditions
            size_trigger = batch_size >= self.config.max_batch_size
            timeout_trigger = wait_time_ms >= self.config.max_wait_time_ms
            min_size_trigger = batch_size >= self.config.min_batch_size

            should_process = size_trigger or timeout_trigger or (
                min_size_trigger and wait_time_ms >= self.config.max_wait_time_ms * 0.5
            )

            if should_process:
                # Extract batch from queue
                batch = []
                for _ in range(batch_size):
                    if self.queue:
                        batch.append(self.queue.popleft())

                return True, batch

            return False, []

    async def _process_single_batch(self, batch: List[PendingRequest]) -> None:
        """Processes a single batch of requests.

        Args:
            batch: List of pending requests to process together.
        """
        batch_logger = get_contextual_logger(
            __name__,
            operation="stream_batch_processing",
            batch_size=len(batch),
        )

        start_time = time.time()

        try:
            # Extract texts from batch
            texts = [req.text for req in batch]

            batch_logger.debug(
                "Processing batch",
                batch_size=len(batch),
                queue_size=len(self.queue),
            )

            # Perform vectorized batch prediction
            results = self.model.predict_batch(texts)

            processing_time = (time.time() - start_time) * 1000

            # Update statistics
            self._stats["total_batches"] += 1
            self._stats["total_processing_time_ms"] += processing_time

            # Calculate rolling average batch size
            alpha = 0.1  # Smoothing factor for exponential moving average
            self._stats["avg_batch_size"] = (
                alpha * len(batch) + (1 - alpha) * self._stats["avg_batch_size"]
            )

            # Count cache hits
            cache_hits = sum(1 for r in results if r.get("cached", False))
            self._stats["cache_hits"] += cache_hits

            # Resolve all futures with their results
            for req, result in zip(batch, results):
                if not req.future.done():
                    req.future.set_result(result)

            batch_logger.info(
                "Batch processed successfully",
                batch_size=len(batch),
                processing_time_ms=round(processing_time, 2),
                throughput_requests_per_sec=round(len(batch) / (processing_time / 1000), 2),
                cache_hits=cache_hits,
                cache_hit_rate=round(cache_hits / len(batch), 2),
            )

        except Exception as e:
            batch_logger.error(
                "Batch processing failed",
                error=str(e),
                error_type=type(e).__name__,
                batch_size=len(batch),
                exc_info=True,
            )

            # Resolve all futures with the exception
            for req in batch:
                if not req.future.done():
                    req.future.set_exception(e)

    def get_stats(self) -> Dict[str, Any]:
        """Retrieves processing statistics.

        Returns:
            A dictionary containing various performance metrics.
        """
        avg_processing_time = 0.0
        if self._stats["total_batches"] > 0:
            avg_processing_time = (
                self._stats["total_processing_time_ms"] / self._stats["total_batches"]
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
                self._stats["cache_hits"] / self._stats["total_requests"]
                if self._stats["total_requests"] > 0 else 0.0,
                2
            ),
        }

    def reset_stats(self) -> None:
        """Resets processing statistics."""
        self._stats = {
            "total_requests": 0,
            "total_batches": 0,
            "total_processing_time_ms": 0.0,
            "avg_batch_size": 0.0,
            "cache_hits": 0,
        }

    async def shutdown(self) -> None:
        """Gracefully shuts down the stream processor.

        Processes any remaining requests in the queue before stopping.
        """
        logger.info("Shutting down stream processor", queue_size=len(self.queue))

        # Process remaining requests
        while len(self.queue) > 0:
            async with self._lock:
                if len(self.queue) == 0:
                    break

                batch_size = min(len(self.queue), self.config.max_batch_size)
                batch = []
                for _ in range(batch_size):
                    if self.queue:
                        batch.append(self.queue.popleft())

            if batch:
                await self._process_single_batch(batch)

        # Cancel batch processing task if running
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass

        logger.info("Stream processor shutdown complete")

    async def predict_async_batch(self, texts: List[str], batch_id: str) -> List[Dict[str, Any]]:
        """Process a batch of texts asynchronously.

        This method provides async batch processing optimized for high throughput.

        Args:
            texts: List of texts to process.
            batch_id: Identifier for the batch.

        Returns:
            List of prediction results.
        """
        batch_logger = get_contextual_logger(
            __name__,
            operation="async_batch_processing",
            batch_id=batch_id,
            batch_size=len(texts),
        )

        try:
            # Use the existing batch prediction logic but in async context
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

            # Return error results for all texts
            error_results = []
            for text in texts:
                error_results.append({
                    "label": "ERROR",
                    "score": 0.0,
                    "error": str(e),
                    "inference_time_ms": 0.0,
                    "model_name": "stream_processor",
                    "text_length": len(text),
                    "backend": "async_batch",
                    "cached": False,
                })

            return error_results

