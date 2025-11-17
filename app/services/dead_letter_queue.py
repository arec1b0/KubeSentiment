"""Dead Letter Queue implementation for failed message handling."""

import json
import time
from typing import Any

from kafka import KafkaProducer

from app.models.kafka_models import MessageMetadata

try:  # pragma: no cover - optional dependency for lightweight tests
    from app.core.logging import get_contextual_logger
except Exception:  # pragma: no cover - fallback to standard logging
    from app.utils.logging_adapters import (
        get_fallback_contextual_logger as get_contextual_logger,
    )

logger = get_contextual_logger(__name__)


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

        backoff_base = (
            0.002  # seconds; keeps retries fast in tests while honouring exponential backoff
        )
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
