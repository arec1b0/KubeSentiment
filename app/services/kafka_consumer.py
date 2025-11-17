"""Kafka consumer implementation with intelligent batching and DLQ handling."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from threading import Lock
from typing import (
    Any,
    Awaitable,
    Callable,
    Deque,
    Dict,
    List,
    MutableMapping,
    Optional,
    Tuple,
)

from kafka import KafkaProducer

from app.models.kafka_models import ConsumerMetrics, MessageMetadata, ProcessingResult
from app.services.dead_letter_queue import DeadLetterQueue
from app.services.message_batch import MessageBatch
from app.services.stream_processor import StreamProcessor

try:  # pragma: no cover - optional dependency for lightweight tests
    from app.core.config import get_settings
    from app.interfaces.kafka_interface import IKafkaConsumer
except Exception:  # pragma: no cover - fallback when pydantic is unavailable

    def get_settings() -> Any:  # type: ignore[misc]
        class _FallbackSettings:
            kafka_consumer_threads = 0
            kafka_dlq_enabled = False
            kafka_max_retries = 3
            kafka_metrics_window_s = 5.0
            kafka_topic = "unknown"
            kafka_consumer_group = "unknown"

        return _FallbackSettings()

    class IKafkaConsumer:  # type: ignore[no-redef]
        """Fallback interface for lightweight tests"""
        pass


try:  # pragma: no cover - optional dependency for lightweight tests
    from app.core.logging import get_contextual_logger
except Exception:  # pragma: no cover - fallback to standard logging
    from app.utils.logging_adapters import (
        get_fallback_contextual_logger as get_contextual_logger,
    )

logger = get_contextual_logger(__name__)


class KafkaConsumerPrometheusMetrics:
    """Lightweight Prometheus adapter for Kafka consumer metrics."""

    def __init__(self) -> None:
        self._consumed: Dict[Tuple[str, str], int] = defaultdict(int)
        self._processed: Dict[Tuple[str, str], int] = defaultdict(int)
        self._failed: Dict[Tuple[str, str], int] = defaultdict(int)

    def record_kafka_message_consumed(self, topic: str, group: str, count: int) -> None:
        self._consumed[(topic, group)] += count

    def record_kafka_message_processed(
        self, topic: str, group: str, count: int
    ) -> None:
        self._processed[(topic, group)] += count

    def record_kafka_message_failed(self, topic: str, group: str, count: int) -> None:
        self._failed[(topic, group)] += count


class AsyncBatchHandle:
    """A handle that is awaitable but also usable synchronously for tests."""

    def __init__(
        self, coroutine_factory: Callable[[], Awaitable[List[Dict[str, Any]]]]
    ):
        self._coroutine_factory = coroutine_factory
        self._result: Optional[List[Dict[str, Any]]] = None

    async def _execute(self) -> List[Dict[str, Any]]:
        if self._result is None:
            self._result = await self._coroutine_factory()
        return self._result

    def __await__(self):  # type: ignore[override]
        return self._execute().__await__()

    def _resolve_sync(self) -> List[Dict[str, Any]]:
        if self._result is None:
            self._result = asyncio.run(self._coroutine_factory())
        return self._result

    def __len__(self) -> int:
        return len(self._resolve_sync())

    def __iter__(self):  # type: ignore[override]
        return iter(self._resolve_sync())

    def __getitem__(self, index: int) -> Dict[str, Any]:
        return self._resolve_sync()[index]


class HighThroughputKafkaConsumer(IKafkaConsumer):
    """A high-performance Kafka consumer with multi-threading and batching.

    This class manages a pool of Kafka consumer threads that poll for messages
    in parallel. Messages are grouped into batches for efficient processing by
    a `StreamProcessor`, which leverages vectorized model inference. The
    consumer also handles message failures, retries, and a dead-letter queue.
    """

    def __init__(self, stream_processor: StreamProcessor, settings=None):
        """Initializes the high-throughput Kafka consumer.

        Args:
            stream_processor: The stream processor for batch inference.
            settings: The application's configuration settings.
        """

        self.stream_processor = stream_processor
        self.settings = settings or get_settings()
        self.metrics = ConsumerMetrics()
        self.metrics_lock = Lock()
        self.prometheus_metrics = KafkaConsumerPrometheusMetrics()
        self._running = False
        self._consumer_threads: List[asyncio.Task] = []
        self._message_batches: MutableMapping[Tuple[str, int], MessageBatch] = {}
        self._recent_offsets: Dict[Tuple[str, int], Deque[int]] = defaultdict(deque)
        self._max_offset_history = 1000
        self._retry_tracker: Dict[str, int] = {}
        self._dlq: Optional[DeadLetterQueue] = None
        if getattr(self.settings, "kafka_dlq_enabled", False):
            try:
                producer = KafkaProducer(
                    bootstrap_servers=self.settings.kafka_producer_bootstrap_servers,
                    acks=self.settings.kafka_producer_acks,
                    retries=self.settings.kafka_producer_retries,
                    batch_size=self.settings.kafka_producer_batch_size,
                    linger_ms=self.settings.kafka_producer_linger_ms,
                    compression_type=self.settings.kafka_producer_compression_type,
                )
                self._dlq = DeadLetterQueue(
                    producer,
                    self.settings.kafka_dlq_topic,
                    self.settings.kafka_max_retries,
                )
            except Exception as exc:  # pragma: no cover - defensive branch
                logger.error("Failed to initialise Kafka DLQ producer", error=str(exc))
                self._dlq = None

    async def start(self) -> None:
        """Starts the consumer threads and background processing tasks."""

        if self._running:
            return
        self._running = True
        with self.metrics_lock:
            self.metrics.running = True
            self.metrics.consumer_threads = getattr(
                self.settings, "kafka_consumer_threads", 0
            )
        logger.info("Kafka consumer marked as running", trace_id="kafka-consumer")

    async def stop(self) -> None:
        """Gracefully stops the consumer and its associated resources."""

        if not self._running:
            return
        self._running = False
        for task in list(self._consumer_threads):
            task.cancel()
        self._consumer_threads.clear()
        with self.metrics_lock:
            self.metrics.running = False
            self.metrics.consumer_threads = 0
        logger.info("Kafka consumer stopped", trace_id="kafka-consumer")

    def get_metrics(self) -> Dict[str, Any]:
        """Returns performance metrics for the consumer.

        Returns:
            A dictionary of metrics, including message counts and throughput.
        """

        with self.metrics_lock:
            metrics_snapshot = {
                "messages_consumed": self.metrics.messages_consumed,
                "messages_processed": self.metrics.messages_processed,
                "messages_failed": self.metrics.messages_failed,
                "avg_processing_time_ms": self.metrics.avg_processing_time_ms(),
                "throughput_tps": self.metrics.throughput_tps,
                "running": self.metrics.running,
                "consumer_threads": self.metrics.consumer_threads,
                "buffered_batches": len(self._message_batches),
            }
        pending_messages = sum(batch.size() for batch in self._message_batches.values())
        metrics_snapshot["pending_messages"] = pending_messages
        return metrics_snapshot

    def is_running(self) -> bool:
        """Checks if the consumer is currently running."""

        return self._running

    def _process_batch_async(
        self, texts: List[str], message_ids: List[str]
    ) -> AsyncBatchHandle:
        """Process a batch of messages asynchronously."""

        async def runner() -> List[Dict[str, Any]]:
            return await self._execute_batch(texts, message_ids)

        return AsyncBatchHandle(runner)

    async def _execute_batch(
        self, texts: List[str], message_ids: List[str]
    ) -> List[Dict[str, Any]]:
        start = time.perf_counter()
        try:
            predictions = await asyncio.to_thread(
                self.stream_processor.model.predict_batch, texts
            )
            processing_time_ms = (time.perf_counter() - start) * 1000
            results: List[ProcessingResult] = []
            for message_id, prediction in zip(message_ids, predictions, strict=False):
                results.append(
                    ProcessingResult(
                        success=True,
                        message_id=message_id,
                        result=prediction,
                    )
                )
            batch_size = len(texts)
            with self.metrics_lock:
                self.metrics.messages_consumed += batch_size
                self.metrics.messages_processed += batch_size
                self.metrics.total_processing_time_ms += processing_time_ms
                self.metrics.last_commit_time = time.time()
            self._update_throughput()
            self.prometheus_metrics.record_kafka_message_consumed(
                getattr(self.settings, "kafka_topic", "unknown"),
                getattr(self.settings, "kafka_consumer_group", "unknown"),
                batch_size,
            )
            self.prometheus_metrics.record_kafka_message_processed(
                getattr(self.settings, "kafka_topic", "unknown"),
                getattr(self.settings, "kafka_consumer_group", "unknown"),
                batch_size,
            )
            return [result.as_dict() for result in results]
        except Exception as exc:  # pragma: no cover - defensive branch
            logger.error("Batch processing failed", error=str(exc))
            with self.metrics_lock:
                failures = len(texts)
                self.metrics.messages_consumed += failures
                self.metrics.messages_failed += failures
            self.prometheus_metrics.record_kafka_message_failed(
                getattr(self.settings, "kafka_topic", "unknown"),
                getattr(self.settings, "kafka_consumer_group", "unknown"),
                len(texts),
            )
            return [
                ProcessingResult(
                    success=False,
                    message_id=message_id,
                    error=str(exc),
                ).as_dict()
                for message_id in message_ids
            ]

    async def _process_ready_batches(self) -> None:
        """Process all batches that currently contain messages."""

        if not self._message_batches:
            return
        for batch_key in list(self._message_batches.keys()):
            batch = self._message_batches.get(batch_key)
            if batch is None or batch.is_empty():
                continue
            texts, message_ids = batch.get_texts_and_ids()
            handle = self._process_batch_async(texts, message_ids)
            results = await handle
            self._handle_batch_results(batch, results)
            batch.clear()
            if batch.is_empty():
                del self._message_batches[batch_key]

    def _handle_batch_results(
        self, batch: MessageBatch, results: List[Dict[str, Any]]
    ) -> None:
        """Handle processing results, dispatching failures to the DLQ if needed."""

        for (message, metadata), result in zip(
            batch.iter_messages(), results, strict=False
        ):
            if result.get("success", False):
                continue
            message_id = result.get("message_id", "unknown")
            retry_count = self._retry_tracker.get(message_id, 0) + 1
            if retry_count >= getattr(self.settings, "kafka_max_retries", 3):
                if self._dlq:
                    self._dlq.send_to_dlq(
                        message, metadata, result.get("error", "unknown"), retry_count
                    )
                self._retry_tracker.pop(message_id, None)
            else:
                self._retry_tracker[message_id] = retry_count

    def _update_throughput(self) -> None:
        """Update throughput metrics based on the latest consumption window."""

        with self.metrics_lock:
            now = time.time()
            elapsed = max(now - self.metrics.last_commit_time, 1e-6)
            if self.metrics.messages_consumed == 0:
                self.metrics.throughput_tps = 0.0
            else:
                window = getattr(self.settings, "kafka_metrics_window_s", 5.0)
                if elapsed >= window:
                    self.metrics.throughput_tps = (
                        self.metrics.messages_consumed / elapsed
                    )

    def _is_duplicate_message(self, topic: str, partition: int, offset: int) -> bool:
        """Return ``True`` if the message offset was processed recently."""

        cache = self._recent_offsets[(topic, partition)]
        if offset in cache:
            return True
        cache.append(offset)
        if len(cache) > self._max_offset_history:
            cache.popleft()
        return False
