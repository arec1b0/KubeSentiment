"""Batch job models and enumerations for asynchronous processing."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BatchJobStatus(str, Enum):
    """Enumeration of possible statuses for a batch job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Priority(str, Enum):
    """Enumeration of processing priority levels for batch jobs."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class BatchJob:
    """Represents a single batch processing job.

    This dataclass holds all information related to a batch job, including its
    status, priority, and the results of the analysis.
    """

    job_id: str
    texts: List[str]
    priority: Priority
    status: BatchJobStatus = BatchJobStatus.PENDING
    results: Optional[List[Dict[str, Any]]] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    progress: float = 0.0
    processed_count: int = 0
    failed_count: int = 0
    max_batch_size: int = 100
    timeout_seconds: int = 300

    def _estimate_completion_time(self) -> int:
        """Estimates the completion time in seconds based on current progress.

        Returns:
            Estimated completion time in seconds.
        """
        if self.status == BatchJobStatus.COMPLETED:
            return 0
        if self.status == BatchJobStatus.FAILED or self.status == BatchJobStatus.CANCELLED:
            return 0
        if self.status == BatchJobStatus.EXPIRED:
            return 0

        if self.status == BatchJobStatus.PENDING:
            return self.timeout_seconds

        if self.status == BatchJobStatus.PROCESSING and self.started_at:
            if self.progress > 0:
                elapsed = time.time() - self.started_at
                remaining = (elapsed / self.progress) * (1.0 - self.progress)
                return int(remaining)
            return self.timeout_seconds

        return self.timeout_seconds

    def to_dict(self) -> Dict:
        """Converts the batch job to a dictionary representation.

        Returns:
            A dictionary containing all job information.
        """
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "total_texts": len(self.texts),
            "processed_texts": self.processed_count,
            "failed_texts": self.failed_count,
            "priority": self.priority.value,
            "progress": self.progress,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "estimated_completion_seconds": self._estimate_completion_time(),
            "error": self.error,
        }
