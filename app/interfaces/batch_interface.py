"""
Interface for Async Batch Service

Defines the contract for asynchronous batch processing services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum


class JobPriority(Enum):
    """Priority levels for batch jobs"""

    HIGH = 1
    MEDIUM = 2
    LOW = 3


class JobStatus(Enum):
    """Batch job status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class IAsyncBatchService(ABC):
    """
    Interface for asynchronous batch processing services.

    Provides high-throughput batch processing with priority queues,
    job tracking, and result pagination.
    """

    @abstractmethod
    async def start(self) -> None:
        """
        Start the batch processing service and worker tasks.

        Raises:
            RuntimeError: If service is already running or fails to start
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        Gracefully stop the batch processing service.

        Waits for in-flight jobs to complete before shutting down.
        """
        pass

    @abstractmethod
    async def submit_batch_job(
        self,
        texts: List[str],
        priority: JobPriority = JobPriority.MEDIUM,
        max_batch_size: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        """
        Submit a batch prediction job.

        Args:
            texts: List of texts to process
            priority: Job priority level
            max_batch_size: Maximum batch size for processing
            timeout_seconds: Job timeout in seconds

        Returns:
            Job ID for tracking

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If queue is full or service not running
        """
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of a batch job.

        Args:
            job_id: Job identifier

        Returns:
            Dictionary containing:
                - job_id: Job identifier
                - status: Current job status
                - progress: Progress information
                - created_at: Job creation timestamp
                - completed_at: Job completion timestamp (if applicable)

        Raises:
            KeyError: If job_id not found
        """
        pass

    @abstractmethod
    async def get_job_results(
        self, job_id: str, page: int = 1, page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get paginated results for a completed batch job.

        Args:
            job_id: Job identifier
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            Dictionary containing:
                - results: List of predictions
                - total: Total number of results
                - page: Current page
                - page_size: Results per page
                - has_more: Whether more results exist

        Raises:
            KeyError: If job_id not found
            ValueError: If job is not completed
        """
        pass

    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending batch job.

        Args:
            job_id: Job identifier

        Returns:
            True if job was cancelled, False if already processing/completed

        Raises:
            KeyError: If job_id not found
        """
        pass

    @abstractmethod
    async def get_batch_metrics(self) -> Dict[str, Any]:
        """
        Get batch processing performance metrics.

        Returns:
            Dictionary containing metrics like throughput, queue size,
            processing times, etc.
        """
        pass

    @abstractmethod
    def get_job_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status across all priority levels.

        Returns:
            Dictionary with queue sizes by priority
        """
        pass
