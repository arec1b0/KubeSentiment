"""
Priority Queue Manager - Handles queue coordination and task ordering.

This module provides a focused class for managing priority-based queues,
including initialization, enqueueing, dequeueing, and worker processing.
"""

import asyncio

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.batch_job import BatchJob, Priority

logger = get_logger(__name__)


class PriorityQueueManager:
    """Manages priority-based queues for batch job processing.

    Responsibilities:
    - Queue initialization and management
    - Job enqueueing with priority handling
    - Job dequeueing for processing
    - Queue status reporting
    - Worker task coordination
    """

    def __init__(self, settings: Settings):
        """Initialize the priority queue manager.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self._priority_queues: dict[Priority, asyncio.Queue] | None = None
        self._worker_tasks: list[asyncio.Task] = []
        self._shutdown_event: asyncio.Event | None = None
        self._running = False

    async def initialize_queues(self) -> None:
        """Initialize priority queues for all priority levels."""
        if self._priority_queues is not None:
            logger.warning("Priority queues already initialized")
            return

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

        logger.info("Priority queues initialized")

    def get_queue(self, priority: Priority) -> asyncio.Queue:
        """Get the queue for a specific priority level.

        Args:
            priority: Priority level.

        Returns:
            The asyncio.Queue for the priority level.

        Raises:
            RuntimeError: If queues are not initialized.
        """
        if self._priority_queues is None:
            raise RuntimeError(
                "Priority queues not initialized. Call initialize_queues() first."
            )
        return self._priority_queues[priority]

    async def enqueue_job(self, job: BatchJob) -> None:
        """Enqueue a job to the appropriate priority queue.

        Args:
            job: The batch job to enqueue.

        Raises:
            RuntimeError: If queues are not initialized.
            ValueError: If queue is full.
        """
        if self._priority_queues is None:
            raise RuntimeError(
                "Priority queues not initialized. Call initialize_queues() first."
            )

        queue = self._priority_queues[job.priority]
        try:
            queue.put_nowait(job)
            logger.info(
                f"Enqueued batch job {job.job_id}",
                priority=job.priority.value,
                batch_size=len(job.texts),
            )
        except asyncio.QueueFull:
            logger.error(
                f"Failed to enqueue job {job.job_id}: queue full",
                priority=job.priority.value,
            )
            raise ValueError(f"Queue full for priority {job.priority.value}")

    async def dequeue_job(self, priority: Priority, timeout: float = 1.0) -> BatchJob | None:
        """Dequeue a job from the specified priority queue.

        Args:
            priority: Priority level to dequeue from.
            timeout: Timeout in seconds for waiting for a job.

        Returns:
            BatchJob if available, None if timeout.
        """
        if self._priority_queues is None:
            raise RuntimeError(
                "Priority queues not initialized. Call initialize_queues() first."
            )

        queue = self._priority_queues[priority]
        try:
            job = await asyncio.wait_for(queue.get(), timeout=timeout)
            return job
        except asyncio.TimeoutError:
            return None

    def get_queue_status(self) -> dict[str, int]:
        """Get current status of all priority queues.

        Returns:
            Dictionary with queue sizes for each priority level.
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

    async def start_workers(
        self,
        process_job_callback,
        is_job_valid_callback,
    ) -> None:
        """Start worker tasks for each priority queue.

        Args:
            process_job_callback: Async function to process a job (job: BatchJob) -> None.
            is_job_valid_callback: Function to check if job is valid (job: BatchJob) -> bool.
        """
        if self._running:
            logger.warning("Priority queue workers already running")
            return

        if self._priority_queues is None:
            await self.initialize_queues()

        self._running = True
        if self._shutdown_event:
            self._shutdown_event.clear()

        # Start worker tasks for each priority queue
        for priority in [Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
            task = asyncio.create_task(
                self._process_priority_queue(
                    priority, process_job_callback, is_job_valid_callback
                )
            )
            self._worker_tasks.append(task)
            logger.info(f"Started worker task for {priority.value} priority queue")

        logger.info("Priority queue workers started successfully")

    async def stop_workers(self) -> None:
        """Stop all worker tasks."""
        if not self._running:
            logger.warning("Priority queue workers are not running")
            return

        logger.info("Stopping priority queue workers...")
        self._running = False

        if self._shutdown_event:
            self._shutdown_event.set()

        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()

        # Wait for tasks to complete cancellation
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        self._worker_tasks.clear()
        logger.info("Priority queue workers stopped successfully")

    async def _process_priority_queue(
        self,
        priority: Priority,
        process_job_callback,
        is_job_valid_callback,
    ) -> None:
        """Process jobs from a priority queue.

        Args:
            priority: The priority level to process.
            process_job_callback: Async function to process a job.
            is_job_valid_callback: Function to check if job is valid.
        """
        if self._priority_queues is None:
            raise RuntimeError("Priority queues not initialized")

        queue = self._priority_queues[priority]
        logger.info(f"Started processing {priority.value} priority queue")

        while self._running:
            try:
                # Wait for job with timeout to allow checking shutdown event
                job = await self.dequeue_job(priority, timeout=1.0)

                if job is None:
                    continue

                # Check if job is still valid
                if not is_job_valid_callback(job):
                    continue

                # Process the job
                await process_job_callback(job)

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

