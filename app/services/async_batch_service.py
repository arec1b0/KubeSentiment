"""
Asynchronous batch processing service for high-throughput sentiment analysis.

This service provides a robust and scalable solution for processing large
volumes of text data asynchronously. It features a priority-based queueing
system, intelligent batching for efficient model inference, and result
caching to improve performance for repeated requests.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.api.schemas.responses import (
    AsyncBatchMetricsResponse,
    BatchPredictionResults,
    PredictionResponse,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.prediction import PredictionService
from app.services.stream_processor import StreamProcessor

logger = get_logger(__name__)


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


@dataclass
class ProcessingMetrics:
    """Holds metrics for the async batch processing service."""

    total_jobs: int = 0
    active_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_processing_time_seconds: float = 0.0
    average_processing_time_seconds: float = 0.0
    average_throughput_tps: float = 0.0
    queue_size: int = 0
    total_texts_processed: int = 0
    average_batch_size: float = 0.0
    processing_efficiency: float = 0.0

    def update_averages(self):
        """Updates calculated average metrics."""
        if self.completed_jobs > 0:
            self.average_processing_time_seconds = (
                self.total_processing_time_seconds / self.completed_jobs
            )
            if self.total_processing_time_seconds > 0:
                self.average_throughput_tps = (
                    self.total_texts_processed / self.total_processing_time_seconds
                )
            else:
                self.average_throughput_tps = 0.0
        else:
            self.average_processing_time_seconds = 0.0
            self.average_throughput_tps = 0.0

        if self.total_jobs > 0:
            self.processing_efficiency = (self.completed_jobs / self.total_jobs) * 100.0
        else:
            self.processing_efficiency = 0.0


class AsyncBatchService:
    """A service for asynchronous, high-throughput batch processing.

    This service manages a system of priority queues and background workers to
    process large batches of text for sentiment analysis. It is designed to be
    highly available and resilient, with features for job tracking, result
    caching, and performance monitoring.
    """

    def __init__(
        self,
        prediction_service: PredictionService,
        stream_processor: StreamProcessor,
        settings=None,
    ):
        """Initializes the async batch service.

        Args:
            prediction_service: The prediction service for batch processing.
            stream_processor: The stream processor for efficient batching.
            settings: Application settings.
        """
        self.prediction_service = prediction_service
        self.stream_processor = stream_processor
        self.settings = settings or get_settings()

        # Initialize priority queues lazily (created in start() when event loop is active)
        self._priority_queues: Optional[Dict[Priority, asyncio.Queue]] = None

        # Job storage
        self._jobs: Dict[str, BatchJob] = {}

        # Metrics
        self._metrics = ProcessingMetrics()

        # Result cache: {job_id: {"job_info": dict, "results": list, "cached_at": float}}
        self._result_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = self.settings.performance.async_batch_cache_ttl_seconds

        # Background tasks
        self._worker_tasks: List[asyncio.Task] = []
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        self._shutdown_event: Optional[asyncio.Event] = None

        # Lock for thread-safe operations (created lazily when event loop is active)
        self._lock: Optional[asyncio.Lock] = None

    def _ensure_lock(self) -> asyncio.Lock:
        """Ensures the lock is initialized, creating it if necessary.

        This allows methods to work even if start() hasn't been called yet,
        as long as there's an active event loop.

        Returns:
            The initialized lock.
        """
        if self._lock is None:
            try:
                self._lock = asyncio.Lock()
            except RuntimeError:
                raise RuntimeError(
                    "AsyncBatchService requires an active event loop. "
                    "Either call start() first or ensure you're in an async context."
                )
        return self._lock

    async def start(self) -> None:
        """Starts the background workers and cleanup tasks for the service."""
        if self._running:
            logger.warning("AsyncBatchService is already running")
            return

        # Initialize asyncio objects now that event loop is guaranteed to be active
        if self._priority_queues is None:
            self._priority_queues = {
                Priority.HIGH: asyncio.Queue(
                    maxsize=self.settings.performance.async_batch_priority_high_limit
                ),
                Priority.MEDIUM: asyncio.Queue(
                    maxsize=self.settings.performance.async_batch_priority_medium_limit
                ),
                Priority.LOW: asyncio.Queue(
                    maxsize=self.settings.performance.async_batch_priority_low_limit
                ),
            }

        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()

        if self._lock is None:
            self._lock = asyncio.Lock()

        self._running = True
        self._shutdown_event.clear()

        # Start worker tasks for each priority queue
        for priority in [Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
            task = asyncio.create_task(self._process_priority_queue(priority))
            self._worker_tasks.append(task)
            logger.info(f"Started worker task for {priority.value} priority queue")

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_jobs())
        logger.info("Started cleanup task for expired jobs")

        logger.info("AsyncBatchService started successfully")

    async def stop(self) -> None:
        """Gracefully stops the service and its background tasks."""
        if not self._running:
            logger.warning("AsyncBatchService is not running")
            return

        logger.info("Stopping AsyncBatchService...")
        self._running = False
        shutdown_event = self._shutdown_event
        if shutdown_event:
            shutdown_event.set()

        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Wait for tasks to complete cancellation
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        if self._cleanup_task:
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        self._worker_tasks.clear()
        self._cleanup_task = None

        logger.info("AsyncBatchService stopped successfully")

    async def submit_batch_job(
        self,
        texts: List[str],
        priority: str = "medium",
        max_batch_size: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ) -> BatchJob:
        """Submits a new batch job for processing.

        Args:
            texts: A list of texts to be analyzed.
            priority: Processing priority (high, medium, low).
            max_batch_size: Maximum batch size for processing.
            timeout_seconds: Job timeout in seconds.

        Returns:
            A `BatchJob` instance representing the submitted job.

        Raises:
            ValueError: If texts list is empty or invalid.
        """
        if not texts or len(texts) == 0:
            raise ValueError("Texts list cannot be empty")

        # Validate and normalize priority
        try:
            priority_enum = Priority(priority.lower())
        except ValueError:
            priority_enum = Priority.MEDIUM
            logger.warning(f"Invalid priority '{priority}', defaulting to medium")

        # Set defaults from settings
        max_batch_size = max_batch_size or self.settings.performance.async_batch_max_batch_size
        timeout_seconds = (
            timeout_seconds or self.settings.performance.async_batch_default_timeout_seconds
        )

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Create job
        job = BatchJob(
            job_id=job_id,
            texts=texts,
            priority=priority_enum,
            max_batch_size=max_batch_size,
            timeout_seconds=timeout_seconds,
        )

        # Store job
        async with self._ensure_lock():
            self._jobs[job_id] = job
            self._metrics.total_jobs += 1
            self._metrics.active_jobs += 1
            self._metrics.queue_size += 1

        # Ensure queues are initialized (they should be initialized in start(), but check for safety)
        if self._priority_queues is None:
            # Try to initialize queues if we have an event loop
            try:
                self._priority_queues = {
                    Priority.HIGH: asyncio.Queue(
                        maxsize=self.settings.performance.async_batch_priority_high_limit
                    ),
                    Priority.MEDIUM: asyncio.Queue(
                        maxsize=self.settings.performance.async_batch_priority_medium_limit
                    ),
                    Priority.LOW: asyncio.Queue(
                        maxsize=self.settings.performance.async_batch_priority_low_limit
                    ),
                }
            except RuntimeError:
                raise RuntimeError(
                    "AsyncBatchService queues not initialized. Call start() first or ensure you're in an async context."
                )

        # Enqueue job (type checker knows queues is not None after the check above)
        assert self._priority_queues is not None  # Type narrowing for type checker
        queue = self._priority_queues[priority_enum]
        try:
            # Use put_nowait() which raises QueueFull if queue is full
            queue.put_nowait(job)
            logger.info(
                f"Submitted batch job {job_id}",
                priority=priority_enum.value,
                batch_size=len(texts),
            )
        except asyncio.QueueFull:
            async with self._ensure_lock():
                self._metrics.active_jobs -= 1
                self._metrics.queue_size -= 1
                job.status = BatchJobStatus.FAILED
                job.error = f"Queue full for priority {priority_enum.value}"
            logger.error(f"Failed to enqueue job {job_id}: queue full")
            raise ValueError(f"Queue full for priority {priority_enum.value}")

        return job

    async def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Retrieves the status of a specific batch job.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            A `BatchJob` instance if the job is found, `None` otherwise.
        """
        async with self._ensure_lock():
            job = self._jobs.get(job_id)

            if job is None:
                return None

            # Check if job has expired (all modifications inside lock)
            # Only update status and metrics if not already EXPIRED to avoid double-counting
            if self._is_job_expired(job) and job.status != BatchJobStatus.EXPIRED:
                job.status = BatchJobStatus.EXPIRED
                job.error = "Job expired due to timeout"
                job.completed_at = time.time()
                self._metrics.active_jobs -= 1
                self._metrics.failed_jobs += 1

        return job

    async def get_job_results(
        self, job_id: str, page: int = 1, page_size: int = 100
    ) -> Optional[BatchPredictionResults]:
        """Retrieves the results of a completed batch job with pagination.

        Args:
            job_id: The unique identifier of the job.
            page: The page number of the results to retrieve.
            page_size: The number of results per page.

        Returns:
            A `BatchPredictionResults` object if the job is complete, `None`
            otherwise.
        """
        # Check cache first (protected by lock)
        cached_results = None
        async with self._ensure_lock():
            if job_id in self._result_cache:
                cache_entry = self._result_cache[job_id]
                if time.time() - cache_entry["cached_at"] < self._cache_ttl:
                    # Copy results reference while holding lock
                    cached_results = cache_entry["results"]

            # Get job while holding lock
            job = self._jobs.get(job_id)

        # If cached results found, paginate outside lock (no shared state modification)
        if cached_results is not None:
            return self._paginate_results(job_id, cached_results, page, page_size)

        if job is None:
            return None

        # Check if job is completed
        if job.status != BatchJobStatus.COMPLETED:
            return None

        if job.results is None:
            return None

        # Paginate results (outside lock, no shared state modification)
        return self._paginate_results(job_id, job.results, page, page_size)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancels a pending or in-progress batch job.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            `True` if the job was successfully cancelled, `False` otherwise.
        """
        async with self._ensure_lock():
            job = self._jobs.get(job_id)

            if job is None:
                return False

            # Check if job can be cancelled and update atomically
            if job.status not in [BatchJobStatus.PENDING, BatchJobStatus.PROCESSING]:
                return False

            # Store original status before modifying (needed for metrics update)
            was_pending = job.status == BatchJobStatus.PENDING

            # Update job status (all modifications inside lock)
            job.status = BatchJobStatus.CANCELLED
            job.error = "Job cancelled by user"
            job.completed_at = time.time()

            # Update metrics
            self._metrics.active_jobs -= 1
            # Only decrement queue_size if job was PENDING (still in queue)
            # PROCESSING jobs already had queue_size decremented when processing started
            if was_pending:
                self._metrics.queue_size -= 1

        logger.info(f"Cancelled batch job {job_id}")
        return True

    async def get_batch_metrics(self) -> AsyncBatchMetricsResponse:
        """Retrieves performance metrics for the batch processing service.

        Returns:
            An `AsyncBatchMetricsResponse` object with detailed metrics.
        """
        async with self._ensure_lock():
            # Update calculated averages
            self._metrics.update_averages()
            if self._priority_queues:
                self._metrics.queue_size = sum(q.qsize() for q in self._priority_queues.values())
            else:
                self._metrics.queue_size = 0

            return AsyncBatchMetricsResponse(
                total_jobs=self._metrics.total_jobs,
                active_jobs=self._metrics.active_jobs,
                completed_jobs=self._metrics.completed_jobs,
                failed_jobs=self._metrics.failed_jobs,
                average_processing_time_seconds=self._metrics.average_processing_time_seconds,
                average_throughput_tps=self._metrics.average_throughput_tps,
                queue_size=self._metrics.queue_size,
                average_batch_size=self._metrics.average_batch_size,
                processing_efficiency=self._metrics.processing_efficiency,
            )

    def get_job_queue_status(self) -> Dict[str, int]:
        """Returns the current status of all priority queues.

        Returns:
            A dictionary with queue sizes for each priority level.
        """
        if self._priority_queues is None:
            return {
                "high_priority": 0,
                "medium_priority": 0,
                "low_priority": 0,
                "total": 0,
            }
        return {
            "high_priority": self._priority_queues[Priority.HIGH].qsize(),
            "medium_priority": self._priority_queues[Priority.MEDIUM].qsize(),
            "low_priority": self._priority_queues[Priority.LOW].qsize(),
            "total": sum(q.qsize() for q in self._priority_queues.values()),
        }

    def _get_optimal_batch_size(self, total_texts: int) -> int:
        """Calculates the optimal batch size for processing.

        Args:
            total_texts: Total number of texts to process.

        Returns:
            Optimal batch size, capped at max_batch_size.
        """
        max_size = self.settings.performance.async_batch_max_batch_size
        return min(total_texts, max_size)

    def _is_job_valid(self, job: BatchJob) -> bool:
        """Checks if a job is valid and not expired or cancelled.

        Args:
            job: The job to validate.

        Returns:
            True if job is valid, False otherwise.
        """
        if job.status in [BatchJobStatus.CANCELLED, BatchJobStatus.EXPIRED]:
            return False

        if self._is_job_expired(job):
            job.status = BatchJobStatus.EXPIRED
            job.error = "Job expired due to timeout"
            return False

        return True

    def _is_job_expired(self, job: BatchJob) -> bool:
        """Checks if a job has expired based on its timeout.

        Args:
            job: The job to check.

        Returns:
            True if job has expired, False otherwise.
        """
        elapsed = time.time() - job.created_at
        return elapsed > job.timeout_seconds

    async def _process_priority_queue(self, priority: Priority) -> None:
        """Processes jobs from a priority queue.

        Args:
            priority: The priority level to process.
        """
        priority_queues = self._priority_queues
        if priority_queues is None:
            raise RuntimeError("Priority queues not initialized. Call start() first.")
        queue = priority_queues[priority]
        logger.info(f"Started processing {priority.value} priority queue")

        while self._running:
            try:
                # Wait for job with timeout to allow checking shutdown event
                try:
                    job = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Check if job is still valid
                if not self._is_job_valid(job):
                    continue

                # Process the job
                await self._process_job(job)

            except asyncio.CancelledError:
                logger.info(f"Processing queue for {priority.value} priority cancelled")
                break
            except Exception as e:
                logger.error(
                    f"Error processing job from {priority.value} queue",
                    error=str(e),
                    exc_info=True,
                )

        logger.info(f"Stopped processing {priority.value} priority queue")

    async def _process_job(self, job: BatchJob) -> None:
        """Processes a single batch job.

        Args:
            job: The job to process.
        """
        start_time = time.time()

        # Update job status atomically
        async with self._ensure_lock():
            job.status = BatchJobStatus.PROCESSING
            job.started_at = start_time
            self._metrics.queue_size -= 1

        try:
            # Split texts into batches, respecting job-specific max_batch_size
            batch_size = min(len(job.texts), job.max_batch_size)
            all_results = []

            for i in range(0, len(job.texts), batch_size):
                batch_texts = job.texts[i : i + batch_size]
                batch_id = f"{job.job_id}_batch_{i // batch_size}"

                # Process batch using stream processor
                batch_results = await self.stream_processor.predict_async_batch(
                    batch_texts, batch_id
                )
                all_results.extend(batch_results)

                # Update progress atomically
                async with self._ensure_lock():
                    job.processed_count += len(batch_texts)
                    job.progress = job.processed_count / len(job.texts)

            # Mark job as completed atomically
            # Check if job was cancelled before updating status to avoid overwriting CANCELLED
            completed_at = time.time()
            processing_time = completed_at - start_time

            async with self._ensure_lock():
                # Only update to COMPLETED if job wasn't cancelled
                if job.status != BatchJobStatus.CANCELLED:
                    job.status = BatchJobStatus.COMPLETED
                    job.results = all_results
                    job.completed_at = completed_at
                    job.progress = 1.0

                    # Update metrics only if job wasn't cancelled
                    # (cancelled jobs already had metrics updated in cancel_job)
                    self._metrics.active_jobs -= 1
                    self._metrics.completed_jobs += 1
                    self._metrics.total_processing_time_seconds += processing_time
                    self._metrics.total_texts_processed += len(job.texts)
                    batch_size_avg = (
                        self._metrics.average_batch_size * (self._metrics.completed_jobs - 1)
                        + len(job.texts)
                    ) / self._metrics.completed_jobs
                    self._metrics.average_batch_size = batch_size_avg
                else:
                    # Job was cancelled, just store results but don't update status or metrics
                    job.results = all_results
                    logger.info(
                        f"Job {job.job_id} was cancelled during processing, "
                        "results stored but status remains CANCELLED"
                    )

            # Cache results (outside lock to avoid deadlock, but _cache_result acquires its own lock)
            await self._cache_result(job.job_id, job.to_dict(), all_results)

            logger.info(
                f"Completed batch job {job.job_id}",
                processing_time_seconds=processing_time,
                total_texts=len(job.texts),
            )

        except Exception as e:
            # Mark job as failed atomically (all modifications inside lock)
            # Check if job was cancelled before updating status
            failed_at = time.time()
            async with self._ensure_lock():
                # Only update to FAILED if job wasn't cancelled
                if job.status != BatchJobStatus.CANCELLED:
                    job.status = BatchJobStatus.FAILED
                    job.error = str(e)
                    job.completed_at = failed_at

                    # Update metrics only if job wasn't cancelled
                    self._metrics.active_jobs -= 1
                    self._metrics.failed_jobs += 1

            logger.error(
                f"Failed to process batch job {job.job_id}",
                error=str(e),
                exc_info=True,
            )

    def _paginate_results(
        self, job_id: str, results: List[Dict[str, Any]], page: int, page_size: int
    ) -> BatchPredictionResults:
        """Paginates job results.

        Args:
            job_id: The job ID.
            results: List of all results.
            page: Page number (1-based).
            page_size: Number of results per page.

        Returns:
            A BatchPredictionResults object with paginated results.
        """
        total_results = len(results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = results[start_idx:end_idx]

        # Convert to PredictionResponse objects
        prediction_responses = [
            PredictionResponse(**result) if isinstance(result, dict) else result
            for result in paginated_results
        ]

        # Calculate summary statistics
        summary = {
            "total_texts": total_results,
            "successful_predictions": sum(
                1 for r in results if r.get("label") not in ["ERROR", None]
            ),
            "failed_predictions": sum(1 for r in results if r.get("label") == "ERROR"),
            "success_rate": (
                sum(1 for r in results if r.get("label") not in ["ERROR", None]) / total_results
                if total_results > 0
                else 0.0
            ),
        }

        return BatchPredictionResults(
            job_id=job_id,
            results=prediction_responses,
            total_results=total_results,
            page=page,
            page_size=page_size,
            has_more=end_idx < total_results,
            summary=summary,
        )

    async def _cache_result(
        self, job_id: str, job_info: Dict[str, Any], results: List[Dict[str, Any]]
    ) -> None:
        """Caches job results.

        Args:
            job_id: The job ID.
            job_info: Job metadata dictionary.
            results: List of prediction results.
        """
        current_time = time.time()

        async with self._ensure_lock():
            # Cleanup expired cache entries
            expired_keys = [
                k
                for k, v in self._result_cache.items()
                if current_time - v["cached_at"] > self._cache_ttl
            ]
            for key in expired_keys:
                del self._result_cache[key]

            # Check cache size limit
            max_cache_size = self.settings.performance.async_batch_result_cache_max_size
            if len(self._result_cache) >= max_cache_size:
                # Remove oldest entries
                sorted_cache = sorted(self._result_cache.items(), key=lambda x: x[1]["cached_at"])
                num_to_remove = len(self._result_cache) - max_cache_size + 1
                for key, _ in sorted_cache[:num_to_remove]:
                    del self._result_cache[key]

            # Cache the result
            self._result_cache[job_id] = {
                "job_info": job_info,
                "results": results,
                "cached_at": current_time,
            }

    async def _cleanup_expired_jobs(self) -> None:
        """Background task to clean up expired jobs."""
        cleanup_interval = self.settings.performance.async_batch_cleanup_interval_seconds

        while self._running:
            try:
                await asyncio.sleep(cleanup_interval)

                async with self._ensure_lock():
                    expired_jobs = [
                        job_id
                        for job_id, job in self._jobs.items()
                        if self._is_job_expired(job)
                        and job.status
                        not in [
                            BatchJobStatus.COMPLETED,
                            BatchJobStatus.FAILED,
                            BatchJobStatus.EXPIRED,
                        ]
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
