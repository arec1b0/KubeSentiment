"""Data models for Kafka consumer implementation."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


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
