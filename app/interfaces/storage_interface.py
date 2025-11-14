"""
Interface for Data Writer

Defines the contract for data persistence services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IDataWriter(ABC):
    """
    Interface for data persistence services.

    Provides streaming writes to cloud storage in analytics-ready formats.
    """

    @abstractmethod
    async def start(self) -> None:
        """
        Start the data writer service.

        Initializes batch flush tasks and cloud storage connections.

        Raises:
            RuntimeError: If service fails to start
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the data writer and flush remaining data.

        Ensures all buffered data is written before shutdown.
        """
        pass

    @abstractmethod
    async def write_prediction(self, prediction_data: Dict[str, Any]) -> None:
        """
        Queue a prediction for writing to storage.

        Args:
            prediction_data: Prediction data to persist

        Raises:
            ValueError: If prediction_data is invalid
            RuntimeError: If buffer is full
        """
        pass

    @abstractmethod
    async def flush(self) -> None:
        """
        Manually flush buffered data to storage.

        Raises:
            RuntimeError: If flush operation fails
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get buffer and write statistics.

        Returns:
            Dictionary containing:
                - buffer_size: Current buffer size
                - total_writes: Total write operations
                - total_records: Total records written
                - last_flush: Last flush timestamp
        """
        pass
