"""
Interface for Kafka Consumer

Defines the contract for Kafka message consumption services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IKafkaConsumer(ABC):
    """
    Interface for Kafka consumer services.

    Provides message consumption with batching, retry, and DLQ support.
    """

    @abstractmethod
    async def start(self) -> None:
        """
        Start the Kafka consumer.

        Begins consuming messages from configured topics.

        Raises:
            RuntimeError: If consumer fails to start
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        Gracefully stop the Kafka consumer.

        Processes remaining batched messages and commits offsets.
        """
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get consumer performance metrics.

        Returns:
            Dictionary containing:
                - messages_consumed: Total messages consumed
                - messages_processed: Successfully processed messages
                - messages_failed: Failed messages
                - batches_processed: Number of batches
                - average_batch_size: Average batch size
                - error_rate: Error rate percentage
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if consumer is running.

        Returns:
            True if consumer is active, False otherwise
        """
        pass
