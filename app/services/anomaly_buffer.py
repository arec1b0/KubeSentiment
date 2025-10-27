"""
Bounded Anomaly Buffer with Time-to-Live (TTL) Expiration.

This module provides a thread-safe, in-memory buffer for storing anomaly
detection results. It is designed to be bounded in size to prevent memory
leaks and supports automatic expiration of entries based on a configurable
TTL. This is useful for temporarily storing anomaly data for monitoring or
short-term analysis without the need for a persistent database.
"""

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.logging import get_logger
from app.monitoring.prometheus import (
    record_anomaly_buffer_eviction,
    record_anomaly_buffer_size,
    record_anomaly_detected,
)

logger = get_logger(__name__)


@dataclass
class AnomalyEntry:
    """Represents a single anomaly detection entry in the buffer.

    This dataclass holds all relevant information about a detected anomaly,
    including the original text, the model's prediction, the anomaly score,
    and metadata. It also includes a TTL to control its lifespan in the buffer.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: float = field(default_factory=time.time)
    text: str = ""
    prediction: Dict[str, Any] = field(default_factory=dict)
    anomaly_score: float = 0.0
    anomaly_type: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl_seconds: int = 3600

    def is_expired(self) -> bool:
        """Checks if this entry has expired based on its TTL.

        Returns:
            `True` if the entry's age exceeds its TTL, `False` otherwise.
        """
        return time.time() - self.timestamp > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Converts the anomaly entry to a dictionary.

        Returns:
            A dictionary representation of the anomaly entry, including its
            age and expiration status.
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "age_seconds": time.time() - self.timestamp,
            "text": self.text,
            "prediction": self.prediction,
            "anomaly_score": self.anomaly_score,
            "anomaly_type": self.anomaly_type,
            "metadata": self.metadata,
            "expired": self.is_expired(),
        }


class BoundedAnomalyBuffer:
    """A thread-safe, bounded buffer for storing anomalies with TTL.

    This buffer is implemented using an `OrderedDict` to efficiently manage a
    fixed-size collection of anomaly entries. It automatically evicts the
    oldest entries when the buffer is full and periodically cleans up expired
    entries to manage memory usage. All public methods are thread-safe.

    Attributes:
        max_size: The maximum number of entries to store.
        default_ttl: The default TTL in seconds for new entries.
    """

    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        """Initializes the bounded anomaly buffer.

        Args:
            max_size: The maximum number of anomalies to store.
            default_ttl: The default time-to-live in seconds for new entries.
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._buffer: OrderedDict[str, AnomalyEntry] = OrderedDict()
        self._lock = Lock()

    def add(self, **kwargs) -> str:
        """Adds an anomaly to the buffer.

        If the buffer is full, the oldest entry is evicted.

        Args:
            **kwargs: Attributes for the `AnomalyEntry`.

        Returns:
            The unique ID of the added entry.
        """
        entry = AnomalyEntry(**kwargs)
        with self._lock:
            if len(self._buffer) >= self.max_size:
                self._buffer.popitem(last=False)
                record_anomaly_buffer_eviction("size_limit")
            self._buffer[entry.id] = entry
            record_anomaly_detected(entry.anomaly_type)
            record_anomaly_buffer_size(len(self._buffer))
        return entry.id

    def get(self, entry_id: str) -> Optional[AnomalyEntry]:
        """Retrieves a non-expired anomaly entry by its ID.

        If the entry is found but has expired, it is removed from the buffer.

        Args:
            entry_id: The ID of the entry to retrieve.

        Returns:
            The `AnomalyEntry` if found and not expired, `None` otherwise.
        """
        with self._lock:
            entry = self._buffer.get(entry_id)
            if entry:
                if entry.is_expired():
                    del self._buffer[entry_id]
                    record_anomaly_buffer_eviction("expired")
                    record_anomaly_buffer_size(len(self._buffer))
                    return None
                return entry
        return None

    def get_all(self) -> List[AnomalyEntry]:
        """Retrieves all non-expired entries from the buffer.

        Returns:
            A list of all active `AnomalyEntry` objects.
        """
        with self._lock:
            return [entry for entry in self._buffer.values() if not entry.is_expired()]

    def cleanup_expired(self) -> int:
        """Manually triggers the cleanup of expired entries.

        Returns:
            The number of entries that were removed.
        """
        with self._lock:
            initial_size = len(self._buffer)
            self._buffer = OrderedDict(
                (k, v) for k, v in self._buffer.items() if not v.is_expired()
            )
            removed_count = initial_size - len(self._buffer)
            if removed_count > 0:
                record_anomaly_buffer_eviction("expired")
                record_anomaly_buffer_size(len(self._buffer))
        return removed_count

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics about the buffer.

        Returns:
            A dictionary containing buffer statistics, such as its current
            size and utilization.
        """
        with self._lock:
            return {
                "current_size": len(self._buffer),
                "max_size": self.max_size,
                "utilization": (len(self._buffer) / self.max_size) * 100,
            }


_anomaly_buffer: Optional[BoundedAnomalyBuffer] = None


def get_anomaly_buffer() -> BoundedAnomalyBuffer:
    """Provides a singleton instance of the `BoundedAnomalyBuffer`.

    This factory function ensures that the anomaly buffer is initialized only
    once, creating a single, shared instance that can be used throughout the
    application.

    Returns:
        The singleton `BoundedAnomalyBuffer` instance.
    """
    global _anomaly_buffer
    if _anomaly_buffer is None:
        from app.core.config import get_settings

        settings = get_settings()
        _anomaly_buffer = BoundedAnomalyBuffer(
            max_size=settings.anomaly_buffer_max_size,
            default_ttl=settings.anomaly_buffer_default_ttl,
        )
    return _anomaly_buffer
