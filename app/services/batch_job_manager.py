"""
Batch Job Manager - Handles job creation, status tracking, and lifecycle.

This module provides a focused class for managing batch job lifecycle,
including creation, status updates, expiration checks, and cleanup.
"""

import asyncio
import time
import uuid

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.batch_job import BatchJob, BatchJobStatus, Priority
from app.models.batch_metrics import ProcessingMetrics

logger = get_logger(__name__)


class BatchJobManager:
    """Manages batch job lifecycle: creation, tracking, and cleanup.

    Responsibilities:
    - Job creation and storage
    - Status tracking and updates
    - Job expiration detection
    - Job validation
    - Expired job cleanup
    """

    def __init__(self, settings: Settings):
        """Initialize the batch job manager.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self._jobs: dict[str, BatchJob] = {}
        self._metrics = ProcessingMetrics()
        self._lock: asyncio.Lock | None = None
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

    def _ensure_lock(self) -> asyncio.Lock:
        """Ensure the lock is initialized.

        Returns:
            The initialized lock.

        Raises:
            RuntimeError: If no event loop is available.
        """
        if self._lock is None:
            try:
                self._lock = asyncio.Lock()
            except RuntimeError:
                raise RuntimeError(
                    "BatchJobManager requires an active event loop. "
                    "Ensure you're in an async context."
                )
        return self._lock

    async def start(self) -> None:
        """Start the job manager and cleanup task."""
        if self._running:
            logger.warning("BatchJobManager is already running")
            return

        if self._lock is None:
            self._lock = asyncio.Lock()

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_jobs())
        logger.info("BatchJobManager started successfully")

    async def stop(self) -> None:
        """Stop the job manager and cleanup task."""
        if not self._running:
            logger.warning("BatchJobManager is not running")
            return

        logger.info("Stopping BatchJobManager...")
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        logger.info("BatchJobManager stopped successfully")

    async def create_job(
        self,
        texts: list[str],
        priority: Priority,
        max_batch_size: int | None = None,
        timeout_seconds: int | None = None,
    ) -> BatchJob:
        """Create a new batch job.

        Args:
            texts: List of texts to process.
            priority: Job priority level.
            max_batch_size: Maximum batch size for processing.
            timeout_seconds: Job timeout in seconds.

        Returns:
            Created BatchJob instance.

        Raises:
            ValueError: If texts list is empty.
        """
        if not texts or len(texts) == 0:
            raise ValueError("Texts list cannot be empty")

        # Set defaults from settings
        default_batch_size = self.settings.performance.async_batch_max_batch_size
        max_batch_size = max(
            1,
            max_batch_size or default_batch_size,
        )
        default_timeout = self.settings.performance.async_batch_default_timeout_seconds
        timeout_seconds = max(1, timeout_seconds or default_timeout)

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Create job
        job = BatchJob(
            job_id=job_id,
            texts=texts,
            priority=priority,
            max_batch_size=max_batch_size,
            timeout_seconds=timeout_seconds,
        )

        # Store job (always use async lock)
        async with self._ensure_lock():
            self._jobs[job_id] = job
            self._metrics.total_jobs += 1
            self._metrics.active_jobs += 1
            self._metrics.queue_size += 1

        logger.info(
            f"Created batch job {job_id}",
            priority=priority.value,
            batch_size=len(texts),
        )

        return job

    async def get_job(self, job_id: str) -> BatchJob | None:
        """Retrieve a job by ID.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            BatchJob instance if found, None otherwise.
        """
        async with self._ensure_lock():
            job = self._jobs.get(job_id)

            if job is None:
                return None

            # Check if job has expired
            if self.is_job_expired(job) and job.status != BatchJobStatus.EXPIRED:
                previous_status = job.status
                job.status = BatchJobStatus.EXPIRED
                job.error = "Job expired due to timeout"
                job.completed_at = time.time()
                if previous_status == BatchJobStatus.PENDING:
                    self._metrics.queue_size -= 1
                if previous_status in (BatchJobStatus.PENDING, BatchJobStatus.PROCESSING):
                    self._metrics.active_jobs -= 1
                self._metrics.failed_jobs += 1

        return job

    async def update_job_status(
        self,
        job_id: str,
        status: BatchJobStatus,
        error: str | None = None,
        results: list[dict] | None = None,
        started_at: float | None = None,
        completed_at: float | None = None,
        progress: float | None = None,
        processed_count: int | None = None,
        failed_count: int | None = None,
    ) -> bool:
        """Update job status and related fields.

        Args:
            job_id: The unique identifier of the job.
            status: New status to set.
            error: Error message if status is FAILED.
            results: Job results if status is COMPLETED.
            started_at: Timestamp when processing started.
            completed_at: Timestamp when job completed.
            progress: Progress percentage (0.0-1.0).
            processed_count: Number of texts processed.
            failed_count: Number of failed texts.

        Returns:
            True if job was updated, False if job not found.
        """
        async with self._ensure_lock():
            job = self._jobs.get(job_id)
            if job is None:
                return False

            # Store original status for metrics updates
            old_status = job.status

            # Update job fields
            job.status = status
            if error is not None:
                job.error = error
            if results is not None:
                job.results = results
            if started_at is not None:
                job.started_at = started_at
            if completed_at is not None:
                job.completed_at = completed_at
            if progress is not None:
                job.progress = progress
            if processed_count is not None:
                job.processed_count = processed_count
            if failed_count is not None:
                job.failed_count = failed_count

            # Update metrics based on status transitions
            if old_status == BatchJobStatus.PENDING and status == BatchJobStatus.PROCESSING:
                self._metrics.queue_size -= 1
            elif status == BatchJobStatus.COMPLETED:
                if old_status != BatchJobStatus.CANCELLED:
                    self._metrics.active_jobs -= 1
                    self._metrics.completed_jobs += 1
            elif status == BatchJobStatus.FAILED:
                if old_status != BatchJobStatus.CANCELLED:
                    self._metrics.active_jobs -= 1
                    self._metrics.failed_jobs += 1
                    # Decrement queue_size if job was PENDING (e.g., enqueueing failed)
                    if old_status == BatchJobStatus.PENDING:
                        self._metrics.queue_size -= 1
            elif status == BatchJobStatus.CANCELLED:
                if old_status == BatchJobStatus.PENDING:
                    self._metrics.active_jobs -= 1
                    self._metrics.queue_size -= 1

            return True

    def is_job_expired(self, job: BatchJob) -> bool:
        """Check if a job has expired based on its timeout.

        Args:
            job: The job to check.

        Returns:
            True if job has expired, False otherwise.
        """
        elapsed = time.time() - job.created_at
        return elapsed > job.timeout_seconds

    def is_job_valid(self, job: BatchJob) -> bool:
        """Check if a job is valid and not expired or cancelled.

        Args:
            job: The job to validate.

        Returns:
            True if job is valid, False otherwise.
        """
        if job.status in [BatchJobStatus.CANCELLED, BatchJobStatus.EXPIRED]:
            return False

        if self.is_job_expired(job):
            previous_status = job.status
            job.status = BatchJobStatus.EXPIRED
            job.error = "Job expired due to timeout"
            job.completed_at = time.time()
            if previous_status == BatchJobStatus.PENDING:
                self._metrics.queue_size -= 1
            if previous_status in (BatchJobStatus.PENDING, BatchJobStatus.PROCESSING):
                self._metrics.active_jobs -= 1
            self._metrics.failed_jobs += 1
            return False

        return True

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or in-progress job.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            True if job was cancelled, False otherwise.
        """
        async with self._ensure_lock():
            job = self._jobs.get(job_id)

            if job is None:
                return False

            # Check if job can be cancelled
            if job.status not in [BatchJobStatus.PENDING, BatchJobStatus.PROCESSING]:
                return False

            # Store original status for metrics update
            was_pending = job.status == BatchJobStatus.PENDING

            # Update job status
            job.status = BatchJobStatus.CANCELLED
            job.error = "Job cancelled by user"
            job.completed_at = time.time()

            # Update metrics
            self._metrics.active_jobs -= 1
            if was_pending:
                self._metrics.queue_size -= 1

        logger.info(f"Cancelled batch job {job_id}")
        return True

    def get_metrics(self) -> ProcessingMetrics:
        """Get current processing metrics.

        Returns:
            ProcessingMetrics instance.
        """
        return self._metrics

    async def record_processing_stats(
        self, job_id: str, texts_processed: int, processing_time_seconds: float
    ) -> BatchJob | None:
        """Safely update processing metrics for a completed job."""
        async with self._ensure_lock():
            job = self._jobs.get(job_id)
            if job is None or job.status != BatchJobStatus.COMPLETED:
                return None

            metrics = self._metrics
            metrics.total_processing_time_seconds += processing_time_seconds
            metrics.total_texts_processed += texts_processed

            # Recompute average batch size across completed jobs
            if metrics.completed_jobs > 0:
                metrics.average_batch_size = (
                    (metrics.average_batch_size * (metrics.completed_jobs - 1))
                    + texts_processed
                ) / metrics.completed_jobs

            metrics.update_averages()
            return job

    async def _cleanup_expired_jobs(self) -> None:
        """Background task to clean up expired jobs."""
        cleanup_interval = (
            self.settings.performance.async_batch_cleanup_interval_seconds
        )

        while self._running:
            try:
                await asyncio.sleep(cleanup_interval)

                async with self._ensure_lock():
                    expired_jobs = [
                        job_id
                        for job_id, job in self._jobs.items()
                        if self.is_job_expired(job)
                        and job.status
                        not in (
                            BatchJobStatus.COMPLETED,
                            BatchJobStatus.FAILED,
                            BatchJobStatus.EXPIRED,
                        )
                    ]

                    for job_id in expired_jobs:
                        job = self._jobs[job_id]
                        job.status = BatchJobStatus.EXPIRED
                        job.error = "Job expired due to timeout"
                        job.completed_at = time.time()
                        self._metrics.active_jobs -= 1
                        self._metrics.failed_jobs += 1

                if expired_jobs:
                    logger.info(f"Cleaned up {len(expired_jobs)} expired jobs")

            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}", exc_info=True)
