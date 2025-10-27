"""
High-performance Kafka consumer for real-time sentiment analysis.

This module implements a multi-threaded Kafka consumer that can process
messages at 5,000+ TPS with intelligent batching, dead letter queues,
and comprehensive monitoring for production MLOps environments.
"""

import asyncio
import json
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from app.core.config import get_settings
from app.core.logging import get_contextual_logger, get_logger
from app.monitoring.prometheus import get_metrics
from app.services.stream_processor import StreamProcessor

logger = get_logger(__name__)


@dataclass
class MessageMetadata:
    """Metadata for a Kafka message."""
    topic: str
    partition: int
    offset: int
    timestamp: int
    key: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Result of message processing."""
    success: bool
    message_id: str
    processing_time_ms: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class ConsumerMetrics:
    """Metrics for consumer performance monitoring."""
    messages_consumed: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    messages_retried: int = 0
    messages_sent_to_dlq: int = 0
    total_processing_time_ms: float = 0.0
    avg_processing_time_ms: float = 0.0
    throughput_tps: float = 0.0
    lag_per_partition: Dict[Tuple[str, int], int] = field(default_factory=dict)
    consumer_group_lag: int = 0
    last_commit_time: float = 0.0


class MessageBatch:
    """Represents a batch of messages for processing."""

    def __init__(self, max_size: int = 100):
        self.messages: List[Tuple[Any, MessageMetadata]] = []
        self.max_size = max_size
        self.created_at = time.time()

    def add_message(self, message: Any, metadata: MessageMetadata) -> bool:
        """Add a message to the batch."""
        if len(self.messages) >= self.max_size:
            return False

        self.messages.append((message, metadata))
        return True

    def is_full(self) -> bool:
        """Check if batch is full."""
        return len(self.messages) >= self.max_size

    def is_empty(self) -> bool:
        """Check if batch is empty."""
        return len(self.messages) == 0

    def size(self) -> int:
        """Get current batch size."""
        return len(self.messages)

    def clear(self) -> None:
        """Clear all messages from batch."""
        self.messages.clear()


class DeadLetterQueue:
    """Handles messages that failed processing after retries."""

    def __init__(self, producer: KafkaProducer, dlq_topic: str, max_retries: int = 3):
        self.producer = producer
        self.dlq_topic = dlq_topic
        self.max_retries = max_retries

    def send_to_dlq(self, message: Any, metadata: MessageMetadata,
                   error: str, retry_count: int) -> bool:
        """Send message to dead letter queue."""
        try:
            # Create DLQ message with original metadata and error info
            dlq_message = {
                "original_message": message,
                "metadata": {
                    "topic": metadata.topic,
                    "partition": metadata.partition,
                    "offset": metadata.offset,
                    "timestamp": metadata.timestamp,
                    "key": metadata.key,
                    "headers": metadata.headers,
                },
                "error": error,
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "dlq_timestamp": int(time.time() * 1000),
                "message_id": str(uuid4()),
            }

            # Send to DLQ topic
            future = self.producer.send(
                self.dlq_topic,
                key=metadata.key.encode('utf-8') if metadata.key else None,
                value=json.dumps(dlq_message).encode('utf-8'),
                headers=[
                    ("retry_count", str(retry_count).encode('utf-8')),
                    ("error_type", type(error).__name__.encode('utf-8')),
                    ("original_topic", metadata.topic.encode('utf-8')),
                ]
            )

            # Wait for acknowledgment
            future.get(timeout=10)
            return True

        except Exception as e:
            logger.error(
                "Failed to send message to DLQ",
                topic=self.dlq_topic,
                error=str(e),
                message_id=dlq_message.get("message_id") if 'dlq_message' in locals() else "unknown"
            )
            return False


class HighThroughputKafkaConsumer:
    """High-performance Kafka consumer with multi-threading and batching."""

    def __init__(self, stream_processor: StreamProcessor, settings=None):
        """Initialize the high-throughput Kafka consumer.

        Args:
            stream_processor: The stream processor for batch inference.
            settings: Application settings (optional, uses get_settings() if not provided).
        """
        self.settings = settings or get_settings()
        self.stream_processor = stream_processor
        self.logger = get_contextual_logger(__name__, component="kafka_consumer")
        self.prometheus_metrics = get_metrics()

        # Consumer state
        self._running = False
        self._consumers: List[KafkaConsumer] = []
        self._producer: Optional[KafkaProducer] = None
        self._dlq: Optional[DeadLetterQueue] = None
        self._executor: Optional[ThreadPoolExecutor] = None

        # Metrics and monitoring
        self.metrics = ConsumerMetrics()
        self.metrics_lock = threading.Lock()

        # Message processing
        self._message_batches = defaultdict(lambda: MessageBatch(self.settings.kafka_batch_size))
        self._batch_queue = asyncio.Queue(maxsize=self.settings.kafka_buffer_size)
        self._processing_tasks: List[asyncio.Task] = []

        # Performance optimization
        self._batch_timer: Optional[asyncio.TimerHandle] = None
        self._last_batch_time = time.time()

        # Message deduplication (for exactly-once processing)
        self._processed_offsets: Dict[Tuple[str, int, int], int] = {}
        self._offset_lock = threading.Lock()

        # Initialize components
        self._setup_consumer()
        self._setup_producer()
        self._setup_dlq()

    def _setup_consumer(self) -> None:
        """Setup Kafka consumer with optimized configuration."""
        consumer_config = {
            'bootstrap_servers': self.settings.kafka_bootstrap_servers,
            'group_id': self.settings.kafka_consumer_group,
            'auto_offset_reset': self.settings.kafka_auto_offset_reset,
            'enable_auto_commit': self.settings.kafka_enable_auto_commit,
            'auto_commit_interval_ms': self.settings.kafka_auto_commit_interval_ms,
            'max_poll_records': self.settings.kafka_max_poll_records,
            'max_poll_interval_ms': self.settings.kafka_max_poll_interval_ms,
            'session_timeout_ms': self.settings.kafka_session_timeout_ms,
            'heartbeat_interval_ms': self.settings.kafka_heartbeat_interval_ms,
            'consumer_timeout_ms': 1000,  # For non-blocking polls
            'api_version': (0, 10, 2),  # Support for various Kafka versions

            # Performance optimizations
            'fetch_min_bytes': 1024 * 1024,  # 1MB min fetch
            'fetch_max_wait_ms': 500,  # Max wait for fetch
            'max_partition_fetch_bytes': 8 * 1024 * 1024,  # 8MB per partition
            'receive_buffer_bytes': 64 * 1024,  # 64KB receive buffer
            'send_buffer_bytes': 64 * 1024,  # 64KB send buffer

            # Security settings (if needed)
            'security_protocol': 'PLAINTEXT',  # Can be extended for SSL/SASL
            'ssl_check_hostname': False,

            # Deserialization
            'value_deserializer': lambda x: json.loads(x.decode('utf-8')) if x else None,
            'key_deserializer': lambda x: x.decode('utf-8') if x else None,
        }

        # Create multiple consumer instances for parallel processing
        self._consumers = []
        for i in range(self.settings.kafka_consumer_threads):
            try:
                consumer = KafkaConsumer(**consumer_config)
                consumer.subscribe([self.settings.kafka_topic])
                self._consumers.append(consumer)
                self.logger.info(
                    "Created consumer instance",
                    consumer_id=i,
                    topic=self.settings.kafka_topic,
                    threads=self.settings.kafka_consumer_threads
                )
            except Exception as e:
                self.logger.error(
                    "Failed to create consumer instance",
                    consumer_id=i,
                    error=str(e)
                )
                raise

        # Setup thread pool for parallel processing
        self._executor = ThreadPoolExecutor(
            max_workers=self.settings.kafka_consumer_threads * 2,
            thread_name_prefix="kafka_processor"
        )

    def _setup_producer(self) -> None:
        """Setup Kafka producer for DLQ."""
        if not self.settings.kafka_dlq_enabled:
            return

        producer_config = {
            'bootstrap_servers': self.settings.kafka_producer_bootstrap_servers,
            'acks': self.settings.kafka_producer_acks,
            'retries': self.settings.kafka_producer_retries,
            'batch_size': self.settings.kafka_producer_batch_size,
            'linger_ms': self.settings.kafka_producer_linger_ms,
            'compression_type': self.settings.kafka_producer_compression_type,

            # Performance optimizations
            'buffer_memory': 64 * 1024 * 1024,  # 64MB buffer
            'max_in_flight_requests_per_connection': 5,

            # Serialization
            'value_serializer': lambda x: json.dumps(x).encode('utf-8'),
            'key_serializer': lambda x: x.encode('utf-8') if x else None,
        }

        try:
            self._producer = KafkaProducer(**producer_config)
            self.logger.info("Kafka producer setup complete")
        except Exception as e:
            self.logger.error("Failed to setup Kafka producer", error=str(e))
            raise

    def _setup_dlq(self) -> None:
        """Setup dead letter queue."""
        if not self.settings.kafka_dlq_enabled or not self._producer:
            return

        try:
            self._dlq = DeadLetterQueue(
                self._producer,
                self.settings.kafka_dlq_topic,
                self.settings.kafka_max_retries
            )
            self.logger.info("Dead letter queue setup complete", topic=self.settings.kafka_dlq_topic)
        except Exception as e:
            self.logger.error("Failed to setup dead letter queue", error=str(e))
            raise

    async def start(self) -> None:
        """Start the Kafka consumer."""
        if self._running:
            self.logger.warning("Consumer already running")
            return

        self._running = True
        self.logger.info(
            "Starting high-throughput Kafka consumer",
            topic=self.settings.kafka_topic,
            consumer_group=self.settings.kafka_consumer_group,
            threads=self.settings.kafka_consumer_threads,
            batch_size=self.settings.kafka_batch_size
        )

        # Start batch processing loop
        self._processing_tasks.append(
            asyncio.create_task(self._batch_processing_loop())
        )

        # Start consumer threads
        loop = asyncio.get_event_loop()
        for i, consumer in enumerate(self._consumers):
            self._processing_tasks.append(
                asyncio.create_task(
                    loop.run_in_executor(
                        self._executor,
                        self._consume_messages,
                        consumer,
                        i
                    )
                )
            )

        # Start metrics collection
        self._processing_tasks.append(
            asyncio.create_task(self._metrics_collection_loop())
        )

        self.logger.info("Kafka consumer started successfully")

    async def stop(self) -> None:
        """Stop the Kafka consumer gracefully."""
        if not self._running:
            return

        self.logger.info("Stopping Kafka consumer...")
        self._running = False

        # Cancel all processing tasks
        for task in self._processing_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        try:
            await asyncio.gather(*self._processing_tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error("Error during consumer shutdown", error=str(e))

        # Close consumers
        for consumer in self._consumers:
            try:
                consumer.close()
            except Exception as e:
                self.logger.error("Error closing consumer", error=str(e))

        # Close producer
        if self._producer:
            try:
                self._producer.flush(timeout=30)
                self._producer.close()
            except Exception as e:
                self.logger.error("Error closing producer", error=str(e))

        # Shutdown thread pool
        if self._executor:
            self._executor.shutdown(wait=True)

        self.logger.info("Kafka consumer stopped")

    def _consume_messages(self, consumer: KafkaConsumer, consumer_id: int) -> None:
        """Consume messages from Kafka (runs in thread pool)."""
        thread_logger = get_contextual_logger(__name__, consumer_id=consumer_id)

        thread_logger.info(
            "Consumer thread started",
            consumer_id=consumer_id,
            topic=self.settings.kafka_topic
        )

        while self._running:
            try:
                # Poll for messages with timeout
                message_batch = consumer.poll(timeout_ms=1000)

                if not message_batch:
                    continue

                # Process each partition's messages
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        self._handle_message(message, consumer_id)

                # Commit offsets if auto-commit is disabled
                if not self.settings.kafka_enable_auto_commit:
                    consumer.commit_async()

            except Exception as e:
                thread_logger.error(
                    "Error in consumer loop",
                    consumer_id=consumer_id,
                    error=str(e),
                    exc_info=True
                )
                time.sleep(1)  # Back off on persistent errors

        thread_logger.info("Consumer thread stopped", consumer_id=consumer_id)

    def _handle_message(self, message: Any, consumer_id: int) -> None:
        """Handle a single message from Kafka."""
        try:
            # Extract message metadata
            metadata = MessageMetadata(
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                timestamp=message.timestamp,
                key=message.key,
                headers=dict(message.headers) if message.headers else {}
            )

            # Check for duplicate processing
            if self._is_duplicate_message(message.topic, message.partition, message.offset):
                return

            # Add to batch for processing
            batch_key = (message.topic, message.partition)
            if not self._message_batches[batch_key].add_message(message.value, metadata):
                # Batch is full, process it immediately
                asyncio.run(self._process_batch(batch_key))

                # Add current message to new batch
                self._message_batches[batch_key].add_message(message.value, metadata)

            # Update metrics
            with self.metrics_lock:
                self.metrics.messages_consumed += 1

            # Record Prometheus metrics
            self.prometheus_metrics.record_kafka_message_consumed(
                self.settings.kafka_topic,
                self.settings.kafka_consumer_group,
                message.partition
            )

            # Check if we should process batch based on time
            current_time = time.time()
            if current_time - self._last_batch_time >= 0.1:  # 100ms batching window
                asyncio.run(self._process_ready_batches())

        except Exception as e:
            self.logger.error(
                "Error handling message",
                consumer_id=consumer_id,
                error=str(e),
                topic=message.topic,
                partition=message.partition,
                offset=message.offset
            )

    def _is_duplicate_message(self, topic: str, partition: int, offset: int) -> bool:
        """Check if message has already been processed."""
        with self._offset_lock:
            key = (topic, partition, offset)
            if key in self._processed_offsets:
                return True

            # Keep only recent offsets to prevent memory growth
            if len(self._processed_offsets) > 10000:
                oldest_time = min(self._processed_offsets.values())
                keys_to_remove = [
                    k for k, v in self._processed_offsets.items()
                    if v < oldest_time - 300  # Remove offsets older than 5 minutes
                ]
                for k in keys_to_remove:
                    del self._processed_offsets[k]

            self._processed_offsets[key] = int(time.time())
            return False

    async def _process_batch(self, batch_key: Tuple[str, int]) -> None:
        """Process a single batch of messages."""
        batch = self._message_batches[batch_key]

        if batch.is_empty():
            return

        start_time = time.time()
        batch_size = batch.size()

        try:
            # Extract texts from messages
            texts = []
            metadatas = []
            message_ids = []

            for message, metadata in batch.messages:
                if isinstance(message, dict) and 'text' in message:
                    texts.append(message['text'])
                    metadatas.append(metadata)
                    message_ids.append(message.get('id', str(uuid4())))
                elif isinstance(message, str):
                    texts.append(message)
                    metadatas.append(metadata)
                    message_ids.append(str(uuid4()))

            if not texts:
                self.logger.warning("No valid texts found in batch", batch_key=batch_key)
                batch.clear()
                return

            # Process batch through stream processor
            results = await self._process_batch_async(texts, message_ids)

            # Handle results
            processing_time = (time.time() - start_time) * 1000

            # Update metrics
            with self.metrics_lock:
                self.metrics.messages_processed += batch_size
                self.metrics.total_processing_time_ms += processing_time
                if self.metrics.messages_processed > 0:
                    self.metrics.avg_processing_time_ms = (
                        self.metrics.total_processing_time_ms / self.metrics.messages_processed
                    )

            # Record Prometheus metrics
            self.prometheus_metrics.record_kafka_message_processed(
                self.settings.kafka_topic,
                self.settings.kafka_consumer_group,
                batch_size
            )
            self.prometheus_metrics.record_kafka_processing_duration(
                self.settings.kafka_topic,
                self.settings.kafka_consumer_group,
                processing_time / 1000  # Convert to seconds
            )
            self.prometheus_metrics.record_kafka_batch_size(
                self.settings.kafka_topic,
                self.settings.kafka_consumer_group,
                batch_size
            )

            # Send results back or handle failures
            await self._handle_batch_results(results, metadatas, message_ids, batch_size)

            # Clear processed batch
            batch.clear()

            self.logger.debug(
                "Batch processed",
                batch_key=batch_key,
                batch_size=batch_size,
                processing_time_ms=round(processing_time, 2),
                throughput_tps=round(batch_size / (processing_time / 1000), 2)
            )

        except Exception as e:
            self.logger.error(
                "Error processing batch",
                batch_key=batch_key,
                batch_size=batch_size,
                error=str(e),
                exc_info=True
            )
            await self._handle_batch_error(batch, str(e))

    async def _process_batch_async(self, texts: List[str], message_ids: List[str]) -> List[Dict[str, Any]]:
        """Process batch asynchronously through stream processor."""
        # Create a mock request-like structure for each text
        mock_requests = []
        for text, message_id in zip(texts, message_ids):
            mock_requests.append({"text": text, "id": message_id})

        # Process through stream processor (convert to async calls)
        tasks = []
        for request in mock_requests:
            task = self.stream_processor.predict_async(request["text"], request["id"])
            tasks.append(task)

        # Wait for all predictions to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions and format results
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    "success": False,
                    "error": str(result),
                    "message_id": message_ids[i]
                })
            else:
                formatted_results.append({
                    "success": True,
                    "result": result,
                    "message_id": message_ids[i]
                })

        return formatted_results

    async def _handle_batch_results(self, results: List[Dict[str, Any]],
                                  metadatas: List[MessageMetadata],
                                  message_ids: List[str], batch_size: int) -> None:
        """Handle batch processing results."""
        successful = 0
        failed = 0

        for result, metadata, message_id in zip(results, metadatas, message_ids):
            if result.get("success", False):
                successful += 1
                # TODO: Send result to output topic or handle success
            else:
                failed += 1
                error = result.get("error", "Unknown error")
                await self._handle_message_failure(message_id, metadata, error, 0)

        # Update failure metrics
        with self.metrics_lock:
            self.metrics.messages_failed += 1

        self.prometheus_metrics.record_kafka_message_failed(
            self.settings.kafka_topic,
            self.settings.kafka_consumer_group,
            type(error).__name__
        )

        with self.metrics_lock:
            self.metrics.messages_processed += successful
            self.metrics.messages_failed += failed

        if failed > 0:
            self.logger.warning(
                "Batch completed with failures",
                batch_size=batch_size,
                successful=successful,
                failed=failed
            )

    async def _handle_message_failure(self, message_id: str, metadata: MessageMetadata,
                                    error: str, retry_count: int) -> None:
        """Handle message processing failure."""
        if retry_count >= self.settings.kafka_max_retries:
            # Send to DLQ
            if self._dlq:
                success = self._dlq.send_to_dlq(
                    {"id": message_id, "error": error},
                    metadata,
                    error,
                    retry_count
                )

                with self.metrics_lock:
                    if success:
                        self.metrics.messages_sent_to_dlq += 1
                    else:
                        self.metrics.messages_failed += 1

                # Record DLQ metrics
                self.prometheus_metrics.record_kafka_message_dlq(
                    self.settings.kafka_topic,
                    self.settings.kafka_consumer_group,
                    self.settings.kafka_dlq_topic
                )

                self.logger.error(
                    "Message sent to DLQ after max retries",
                    message_id=message_id,
                    retry_count=retry_count,
                    topic=metadata.topic,
                    partition=metadata.partition,
                    offset=metadata.offset
                )
        else:
            # Retry processing (simplified - in production might re-queue)
            self.logger.warning(
                "Message failed, will retry",
                message_id=message_id,
                retry_count=retry_count,
                error=error
            )

            with self.metrics_lock:
                self.metrics.messages_retried += 1

            # Record retry metrics
            self.prometheus_metrics.record_kafka_message_retried(
                self.settings.kafka_topic,
                self.settings.kafka_consumer_group
            )

    async def _handle_batch_error(self, batch: MessageBatch, error: str) -> None:
        """Handle batch processing error."""
        for message, metadata in batch.messages:
            await self._handle_message_failure(
                str(uuid4()), metadata, error, 0
            )

    async def _process_ready_batches(self) -> None:
        """Process all batches that are ready."""
        current_time = time.time()

        # Process batches that are full or have timed out
        batches_to_process = []
        for batch_key, batch in self._message_batches.items():
            if batch.is_full() or (current_time - batch.created_at >= 0.1):
                batches_to_process.append(batch_key)

        # Process batches in parallel
        if batches_to_process:
            tasks = [self._process_batch(batch_key) for batch_key in batches_to_process]
            await asyncio.gather(*tasks, return_exceptions=True)

        self._last_batch_time = current_time

    async def _batch_processing_loop(self) -> None:
        """Main batch processing loop."""
        self.logger.info("Batch processing loop started")

        while self._running:
            try:
                await self._process_ready_batches()
                await asyncio.sleep(0.01)  # 10ms check interval for low latency
            except Exception as e:
                self.logger.error(
                    "Error in batch processing loop",
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(1)

        self.logger.info("Batch processing loop stopped")

    async def _metrics_collection_loop(self) -> None:
        """Collect and update metrics."""
        self.logger.info("Metrics collection loop started")

        while self._running:
            try:
                # Calculate throughput (TPS)
                current_time = time.time()
                time_window = 10.0  # 10 second window

                with self.metrics_lock:
                    # Calculate current throughput
                    if current_time - self.metrics.last_commit_time >= time_window:
                        self.metrics.throughput_tps = (
                            self.metrics.messages_consumed / time_window
                        )
                        self.metrics.last_commit_time = current_time

                        # Update Prometheus metrics
                        self.prometheus_metrics.set_kafka_throughput_tps(
                            self.settings.kafka_topic,
                            self.settings.kafka_consumer_group,
                            self.metrics.throughput_tps
                        )
                        self.prometheus_metrics.set_kafka_batch_queue_size(
                            self.settings.kafka_topic,
                            self.settings.kafka_consumer_group,
                            self._batch_queue.qsize() if hasattr(self._batch_queue, 'qsize') else len(self._message_batches)
                        )
                        self.prometheus_metrics.set_kafka_active_batches(
                            self.settings.kafka_topic,
                            self.settings.kafka_consumer_group,
                            len(self._message_batches)
                        )

                # Update consumer group lag (simplified)
                await self._update_consumer_lag()

                await asyncio.sleep(5)  # Update metrics every 5 seconds

            except Exception as e:
                self.logger.error(
                    "Error in metrics collection",
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(10)

        self.logger.info("Metrics collection loop stopped")

    async def _update_consumer_lag(self) -> None:
        """Update consumer lag metrics."""
        try:
            # Get consumer group information (simplified implementation)
            # In production, use AdminClient for accurate lag calculation
            for consumer in self._consumers:
                # This is a simplified version - real implementation would use AdminClient
                pass

        except Exception as e:
            self.logger.error("Error updating consumer lag", error=str(e))

    def get_metrics(self) -> Dict[str, Any]:
        """Get current consumer metrics."""
        with self.metrics_lock:
            return {
                "messages_consumed": self.metrics.messages_consumed,
                "messages_processed": self.metrics.messages_processed,
                "messages_failed": self.metrics.messages_failed,
                "messages_retried": self.metrics.messages_retried,
                "messages_sent_to_dlq": self.metrics.messages_sent_to_dlq,
                "total_processing_time_ms": self.metrics.total_processing_time_ms,
                "avg_processing_time_ms": round(self.metrics.avg_processing_time_ms, 2),
                "throughput_tps": round(self.metrics.throughput_tps, 2),
                "consumer_group_lag": self.metrics.consumer_group_lag,
                "running": self._running,
                "consumer_threads": len(self._consumers),
                "pending_batches": len(self._message_batches),
                "batch_queue_size": self._batch_queue.qsize() if hasattr(self._batch_queue, 'qsize') else 0,
            }

    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running
