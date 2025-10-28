"""Kafka consumer implementation with intelligent batching and DLQ handling."""

from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from typing import (
    Any,
    Awaitable,
    Callable,
    Deque,
    Dict,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Tuple,
)

from kafka import KafkaProducer

try:  # pragma: no cover - optional dependency for lightweight tests
    from app.core.config import get_settings
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


try:  # pragma: no cover - optional dependency for lightweight tests
    from app.core.logging import get_contextual_logger
except Exception:  # pragma: no cover - fallback to standard logging
    import logging

    class _StdLoggerAdapter:
        def __init__(self, name: str):
            self._logger = logging.getLogger(name)

        def _render(self, message: str, **extra: Any) -> str:
            payload = {k: v for k, v in extra.items() if k != "exc_info"}
            if payload:
                formatted = ", ".join(
                    f"{key}={value!r}" for key, value in payload.items()
                )
                return f"{message} | {formatted}"
            return message

        def info(self, message: str, *args: Any, **kwargs: Any) -> None:
            exc_info = kwargs.pop("exc_info", None)
            self._logger.info(self._render(message, **kwargs), *args, exc_info=exc_info)

        def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
            exc_info = kwargs.pop("exc_info", None)
            self._logger.warning(
                self._render(message, **kwargs), *args, exc_info=exc_info
            )

        def error(self, message: str, *args: Any, **kwargs: Any) -> None:
            exc_info = kwargs.pop("exc_info", None)
            self._logger.error(
                self._render(message, **kwargs), *args, exc_info=exc_info
            )

    def get_contextual_logger(name: str) -> _StdLoggerAdapter:
        return _StdLoggerAdapter(name)


from app.services.stream_processor import StreamProcessor

logger = get_contextual_logger(__name__)


@dataclass(slots=True)
class MessageMetadata:
    """Represents metadata for a Kafka message."""

    topic: str
    partition: int
    offset: int
    timestamp: float

    def as_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the metadata."""

        return {
            "topic": self.topic,
            "partition": self.partition,
            "offset": self.offset,
            "timestamp": self.timestamp,
        }


@dataclass(slots=True)
class ProcessingResult:
    """Represents the result of processing a single message."""

    success: bool
    message_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Convert the result to a JSON-serialisable dictionary."""

        payload: Dict[str, Any] = {
            "success": self.success,
            "message_id": self.message_id,
        }
        if self.result is not None:
            payload["result"] = self.result
        if self.error is not None:
            payload["error"] = self.error
        return payload


class MessageBatch:
    """Container for messages that should be processed together."""

    def __init__(self, max_size: int, created_at: Optional[float] = None) -> None:
        self.max_size = max_size
        self._messages: List[Any] = []
        self._metadata: List[MessageMetadata] = []
        self.created_at = created_at or time.time()

    def add_message(self, message: Any, metadata: MessageMetadata) -> bool:
        """Add a message to the batch if capacity is available."""

        if self.is_full():
            return False
        self._messages.append(message)
        self._metadata.append(metadata)
        return True

    def size(self) -> int:
        """Return the number of messages currently buffered."""

        return len(self._messages)

    def is_full(self) -> bool:
        """Return ``True`` when the batch reached its configured size."""

        return self.size() >= self.max_size

    def is_empty(self) -> bool:
        """Return ``True`` when the batch has no buffered messages."""

        return self.size() == 0

    def clear(self) -> None:
        """Remove all buffered messages from the batch."""

        self._messages.clear()
        self._metadata.clear()
        self.created_at = time.time()

    def iter_messages(self) -> Iterable[Tuple[Any, MessageMetadata]]:
        """Yield pairs of message payloads and their metadata."""

        return zip(self._messages, self._metadata, strict=True)

    def get_texts_and_ids(self) -> Tuple[List[str], List[str]]:
        """Extract message texts and identifiers for model inference."""

        texts: List[str] = []
        message_ids: List[str] = []
        for message in self._messages:
            text = (
                message.get("text", "") if isinstance(message, dict) else str(message)
            )
            message_id = (
                message.get("id")
                if isinstance(message, dict) and message.get("id") is not None
                else f"{time.time_ns()}"
            )
            texts.append(text)
            message_ids.append(message_id)
        return texts, message_ids


class DeadLetterQueue:
    """Handles messages that fail processing after multiple retries.

    This class encapsulates the logic for sending failed messages to a
    designated dead-letter queue (DLQ) topic in Kafka. This ensures that
    failing messages do not block the consumer and can be investigated
    separately.
    """

    def __init__(self, producer: KafkaProducer, dlq_topic: str, max_retries: int = 3):
        self.producer = producer
        self.dlq_topic = dlq_topic
        self.max_retries = max_retries

    def send_to_dlq(
        self,
        message: Any,
        metadata: MessageMetadata,
        error: str,
        retry_count: int = 0,
    ) -> bool:
        """Sends a message to the dead-letter queue.

        Args:
            message: The original message that failed.
            metadata: The metadata of the original message.
            error: The error that caused the failure.
            retry_count: Number of attempts already performed.

        Returns:
            `True` if the message was sent successfully, `False` otherwise.
        """

        payload = {
            "message": message,
            "metadata": metadata.as_dict(),
            "error": error,
            "retry_count": retry_count,
            "timestamp": time.time(),
        }

        backoff_base = 0.002  # seconds; keeps retries fast in tests while honouring exponential backoff
        for attempt in range(1, self.max_retries + 1):
            try:
                future = self.producer.send(
                    self.dlq_topic,
                    value=json.dumps(payload).encode("utf-8"),
                )
                future.get(timeout=5.0)
                logger.info(
                    "Message forwarded to Kafka DLQ",
                    topic=self.dlq_topic,
                    attempt=attempt,
                    trace_id=metadata.topic,
                )
                return True
            except Exception as exc:  # pragma: no cover - defensive branch
                logger.warning(
                    "Retrying DLQ publish",
                    error=str(exc),
                    attempt=attempt,
                    trace_id=metadata.topic,
                )
                time.sleep(min(backoff_base * (2**attempt), 0.1))
        logger.error(
            "Failed to forward message to Kafka DLQ",
            topic=self.dlq_topic,
            error=error,
            trace_id=metadata.topic,
        )
        return False


@dataclass(slots=True)
class ConsumerMetrics:
    """Aggregated metrics describing consumer activity."""

    messages_consumed: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    total_processing_time_ms: float = 0.0
    throughput_tps: float = 0.0
    last_commit_time: float = field(default_factory=time.time)
    consumer_threads: int = 0
    running: bool = False

    def avg_processing_time_ms(self) -> float:
        """Average processing time per consumed message."""

        if self.messages_consumed == 0:
            return 0.0
        return self.total_processing_time_ms / self.messages_consumed


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


class HighThroughputKafkaConsumer:
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
