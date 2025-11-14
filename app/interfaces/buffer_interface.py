"""
Interface for Anomaly Buffer

Defines the contract for anomaly storage services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AnomalyEntry:
    """Anomaly detection entry"""
    id: str
    timestamp: datetime
    text: str
    prediction: str
    anomaly_score: float
    anomaly_type: str
    metadata: Dict[str, Any]

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if entry has exceeded TTL"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        pass


class IAnomalyBuffer(ABC):
    """
    Interface for anomaly buffer services.

    Provides temporary in-memory storage for anomaly detection results.
    """

    @abstractmethod
    def add(
        self,
        text: str,
        prediction: str,
        anomaly_score: float,
        anomaly_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add an anomaly entry to the buffer.

        Args:
            text: Input text
            prediction: Predicted label
            anomaly_score: Anomaly score (0-1)
            anomaly_type: Type of anomaly detected
            metadata: Optional additional metadata

        Returns:
            Entry ID

        Raises:
            ValueError: If inputs are invalid
        """
        pass

    @abstractmethod
    def get(self, entry_id: str) -> Optional[AnomalyEntry]:
        """
        Retrieve an anomaly entry by ID.

        Args:
            entry_id: Entry identifier

        Returns:
            AnomalyEntry if found and not expired, None otherwise
        """
        pass

    @abstractmethod
    def get_all(self) -> List[AnomalyEntry]:
        """
        Get all non-expired anomaly entries.

        Returns:
            List of active anomaly entries
        """
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from buffer.

        Returns:
            Number of entries removed
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get buffer utilization statistics.

        Returns:
            Dictionary containing:
                - total_entries: Current number of entries
                - max_size: Maximum buffer size
                - utilization: Buffer utilization percentage
                - oldest_entry: Timestamp of oldest entry
        """
        pass
