"""
Bounded Anomaly Buffer with TTL

This module provides a thread-safe, bounded buffer for storing anomaly detection results
with automatic expiration (TTL) to prevent memory leaks.

Features:
- Bounded capacity with configurable max size
- Time-to-live (TTL) for automatic cleanup
- Thread-safe operations using locks
- Metrics integration for monitoring
- Efficient eviction of expired entries
"""

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
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
    """Represents a single anomaly detection entry."""

    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: float = field(default_factory=time.time)
    text: str = ""
    prediction: Dict[str, Any] = field(default_factory=dict)
    anomaly_score: float = 0.0
    anomaly_type: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl_seconds: int = 3600

    def is_expired(self) -> bool:
        """Check if this entry has expired based on TTL."""
        return time.time() - self.timestamp > self.ttl_seconds

    def age_seconds(self) -> float:
        """Get the age of this entry in seconds."""
        return time.time() - self.timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary representation."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "age_seconds": self.age_seconds(),
            "text": self.text,
            "prediction": self.prediction,
            "anomaly_score": self.anomaly_score,
            "anomaly_type": self.anomaly_type,
            "metadata": self.metadata,
            "ttl_seconds": self.ttl_seconds,
            "expired": self.is_expired(),
        }


class BoundedAnomalyBuffer:
    """
    Thread-safe bounded buffer for storing anomalies with TTL.

    This buffer automatically evicts expired entries and enforces a maximum size
    to prevent memory leaks. When the buffer is full, the oldest entries are removed.

    Attributes:
        max_size: Maximum number of entries to store
        default_ttl: Default TTL in seconds for new entries
        cleanup_interval: How often to run cleanup in seconds
    """

    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: int = 3600,
        cleanup_interval: int = 300,
    ):
        """
        Initialize the bounded anomaly buffer.

        Args:
            max_size: Maximum number of anomalies to store (default: 10000)
            default_ttl: Default time-to-live in seconds (default: 3600 = 1 hour)
            cleanup_interval: Interval for automatic cleanup in seconds (default: 300 = 5 min)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._buffer: OrderedDict[str, AnomalyEntry] = OrderedDict()
        self._lock = Lock()
        self._last_cleanup = time.time()
        self._total_added = 0
        self._total_evicted = 0

        logger.info(
            f"Initialized BoundedAnomalyBuffer with max_size={max_size}, "
            f"default_ttl={default_ttl}s, cleanup_interval={cleanup_interval}s"
        )

    def add(
        self,
        text: str,
        prediction: Dict[str, Any],
        anomaly_score: float,
        anomaly_type: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """
        Add an anomaly to the buffer.

        Args:
            text: The input text that caused the anomaly
            prediction: The prediction result dictionary
            anomaly_score: Anomaly score (higher = more anomalous)
            anomaly_type: Type of anomaly detected
            metadata: Additional metadata to store
            ttl_seconds: Custom TTL for this entry (uses default if None)

        Returns:
            The ID of the added entry
        """
        entry = AnomalyEntry(
            text=text,
            prediction=prediction,
            anomaly_score=anomaly_score,
            anomaly_type=anomaly_type,
            metadata=metadata or {},
            ttl_seconds=ttl_seconds or self.default_ttl,
        )

        with self._lock:
            # Add the entry
            self._buffer[entry.id] = entry
            self._total_added += 1

            # Record metrics
            record_anomaly_detected(anomaly_type)

            # Enforce max size by removing oldest entries if needed
            while len(self._buffer) > self.max_size:
                oldest_id, oldest_entry = self._buffer.popitem(last=False)
                self._total_evicted += 1
                record_anomaly_buffer_eviction("size_limit")
                logger.debug(
                    f"Evicted oldest entry {oldest_id} due to size limit "
                    f"(age: {oldest_entry.age_seconds():.1f}s)"
                )

            # Perform periodic cleanup
            if time.time() - self._last_cleanup > self.cleanup_interval:
                self._cleanup_expired()

            # Update buffer size metric
            record_anomaly_buffer_size(len(self._buffer))

        logger.debug(
            f"Added anomaly {entry.id} (type: {anomaly_type}, "
            f"score: {anomaly_score:.3f}, buffer_size: {len(self._buffer)})"
        )

        return entry.id

    def get(self, entry_id: str) -> Optional[AnomalyEntry]:
        """
        Get an anomaly entry by ID.

        Args:
            entry_id: The ID of the entry to retrieve

        Returns:
            The AnomalyEntry if found and not expired, None otherwise
        """
        with self._lock:
            entry = self._buffer.get(entry_id)
            if entry and entry.is_expired():
                # Remove expired entry
                del self._buffer[entry_id]
                self._total_evicted += 1
                record_anomaly_buffer_eviction("expired")
                record_anomaly_buffer_size(len(self._buffer))
                return None
            return entry

    def get_all(self, include_expired: bool = False) -> List[AnomalyEntry]:
        """
        Get all anomaly entries.

        Args:
            include_expired: If True, include expired entries

        Returns:
            List of AnomalyEntry objects
        """
        with self._lock:
            if include_expired:
                return list(self._buffer.values())
            return [entry for entry in self._buffer.values() if not entry.is_expired()]

    def get_by_type(
        self, anomaly_type: str, include_expired: bool = False
    ) -> List[AnomalyEntry]:
        """
        Get all anomalies of a specific type.

        Args:
            anomaly_type: The type of anomalies to retrieve
            include_expired: If True, include expired entries

        Returns:
            List of matching AnomalyEntry objects
        """
        with self._lock:
            entries = [
                entry
                for entry in self._buffer.values()
                if entry.anomaly_type == anomaly_type
            ]
            if not include_expired:
                entries = [entry for entry in entries if not entry.is_expired()]
            return entries

    def get_recent(
        self, limit: int = 100, min_score: float = 0.0
    ) -> List[AnomalyEntry]:
        """
        Get the most recent anomalies.

        Args:
            limit: Maximum number of entries to return
            min_score: Minimum anomaly score threshold

        Returns:
            List of recent AnomalyEntry objects, newest first
        """
        with self._lock:
            # Get non-expired entries above threshold
            entries = [
                entry
                for entry in self._buffer.values()
                if not entry.is_expired() and entry.anomaly_score >= min_score
            ]
            # Sort by timestamp descending (newest first)
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            return entries[:limit]

    def remove(self, entry_id: str) -> bool:
        """
        Remove an entry from the buffer.

        Args:
            entry_id: The ID of the entry to remove

        Returns:
            True if the entry was removed, False if not found
        """
        with self._lock:
            if entry_id in self._buffer:
                del self._buffer[entry_id]
                record_anomaly_buffer_size(len(self._buffer))
                return True
            return False

    def clear(self) -> int:
        """
        Clear all entries from the buffer.

        Returns:
            The number of entries that were cleared
        """
        with self._lock:
            count = len(self._buffer)
            self._buffer.clear()
            record_anomaly_buffer_size(0)
            logger.info(f"Cleared {count} entries from anomaly buffer")
            return count

    def cleanup_expired(self) -> int:
        """
        Manually trigger cleanup of expired entries.

        Returns:
            The number of entries that were removed
        """
        with self._lock:
            return self._cleanup_expired()

    def _cleanup_expired(self) -> int:
        """
        Internal method to cleanup expired entries (must be called with lock held).

        Returns:
            The number of entries that were removed
        """
        expired_ids = [
            entry_id
            for entry_id, entry in self._buffer.items()
            if entry.is_expired()
        ]

        for entry_id in expired_ids:
            del self._buffer[entry_id]
            self._total_evicted += 1
            record_anomaly_buffer_eviction("expired")

        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired anomaly entries")
            record_anomaly_buffer_size(len(self._buffer))

        self._last_cleanup = time.time()
        return len(expired_ids)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get buffer statistics.

        Returns:
            Dictionary containing buffer statistics
        """
        with self._lock:
            current_size = len(self._buffer)
            expired_count = sum(1 for entry in self._buffer.values() if entry.is_expired())

            # Count by type
            type_counts: Dict[str, int] = {}
            for entry in self._buffer.values():
                if not entry.is_expired():
                    type_counts[entry.anomaly_type] = type_counts.get(entry.anomaly_type, 0) + 1

            return {
                "current_size": current_size,
                "max_size": self.max_size,
                "utilization_percent": (current_size / self.max_size * 100) if self.max_size > 0 else 0,
                "expired_count": expired_count,
                "active_count": current_size - expired_count,
                "total_added": self._total_added,
                "total_evicted": self._total_evicted,
                "default_ttl_seconds": self.default_ttl,
                "cleanup_interval_seconds": self.cleanup_interval,
                "seconds_since_last_cleanup": time.time() - self._last_cleanup,
                "anomalies_by_type": type_counts,
            }

    def __len__(self) -> int:
        """Get the current buffer size (including expired entries)."""
        with self._lock:
            return len(self._buffer)

    def __repr__(self) -> str:
        """String representation of the buffer."""
        return (
            f"BoundedAnomalyBuffer(size={len(self)}/{self.max_size}, "
            f"ttl={self.default_ttl}s)"
        )


# Global buffer instance (initialized in app startup)
_anomaly_buffer: Optional[BoundedAnomalyBuffer] = None


def get_anomaly_buffer() -> BoundedAnomalyBuffer:
    """
    Get the global anomaly buffer instance.

    Returns:
        The global BoundedAnomalyBuffer instance

    Raises:
        RuntimeError: If the buffer has not been initialized
    """
    if _anomaly_buffer is None:
        raise RuntimeError(
            "Anomaly buffer not initialized. Call initialize_anomaly_buffer() first."
        )
    return _anomaly_buffer


def initialize_anomaly_buffer(
    max_size: int = 10000,
    default_ttl: int = 3600,
    cleanup_interval: int = 300,
) -> BoundedAnomalyBuffer:
    """
    Initialize the global anomaly buffer.

    Args:
        max_size: Maximum number of anomalies to store
        default_ttl: Default time-to-live in seconds
        cleanup_interval: Interval for automatic cleanup in seconds

    Returns:
        The initialized BoundedAnomalyBuffer instance
    """
    global _anomaly_buffer
    _anomaly_buffer = BoundedAnomalyBuffer(
        max_size=max_size,
        default_ttl=default_ttl,
        cleanup_interval=cleanup_interval,
    )
    logger.info("Global anomaly buffer initialized")
    return _anomaly_buffer


def shutdown_anomaly_buffer() -> None:
    """Shutdown and cleanup the global anomaly buffer."""
    global _anomaly_buffer
    if _anomaly_buffer is not None:
        stats = _anomaly_buffer.get_stats()
        logger.info(f"Shutting down anomaly buffer: {stats}")
        _anomaly_buffer.clear()
        _anomaly_buffer = None
