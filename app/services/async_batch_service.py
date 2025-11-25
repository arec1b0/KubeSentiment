"""
Asynchronous batch processing service for high-throughput sentiment analysis.

This service orchestrates three focused managers to provide a robust and
scalable solution for processing large volumes of text data asynchronously.
It features a priority-based queueing system, intelligent batching for
efficient model inference, and result caching to improve performance.
"""

import time
from typing import Any

from app.api.schemas.responses import (
    AsyncBatchMetricsResponse,
    BatchPredictionResults,
    PredictionResponse,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.interfaces.batch_interface import IAsyncBatchService
from app.models.batch_job import BatchJob, BatchJobStatus, Priority
from app.services.batch_job_manager import BatchJobManager
from app.services.prediction import PredictionService
from app.services.priority_queue_manager import PriorityQueueManager
from app.services.result_cache_manager import ResultCacheManager
from app.services.stream_processor import StreamProcessor

logger = get_logger(__name__)


class AsyncBatchService(IAsyncBatchService):
    """A service for asynchronous, high-throughput batch processing.

    This service orchestrates three focused managers:
    - BatchJobManager: Job creation, status tracking, lifecycle
    - PriorityQueueManager: Queue coordination, task ordering
    - ResultCacheManager: Result caching and cleanup

    It provides a unified interface for batch processing while maintaining
    clear separation of concerns.
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

        # Initialize managers
        self.job_manager = BatchJobManager(self.settings)
        self.queue_manager = PriorityQueueManager(self.settings)
        self.cache_manager = ResultCacheManager(self.settings)

        self._running = False

    async def start(self) -> None:
        """Starts the background workers and cleanup tasks for the service."""
        if self._running:
            logger.warning("AsyncBatchService is already running")
            return

        # Initialize queues
        await self.queue_manager.initialize_queues()

        # Start job manager (includes cleanup task)
        await self.job_manager.start()

        # Start queue workers
        await self.queue_manager.start_workers(
            process_job_callback=self._process_job,
            is_job_valid_callback=self.job_manager.is_job_valid,
        )

        self._running = True
        logger.info("AsyncBatchService started successfully")

    async def stop(self) -> None:
        """Gracefully stops the service and its background tasks."""
        if not self._running:
            logger.warning("AsyncBatchService is not running")
            return

        logger.info("Stopping AsyncBatchService...")
        self._running = False

        # Stop queue workers
        await self.queue_manager.stop_workers()

        # Stop job manager (includes cleanup task)
        await self.job_manager.stop()

        logger.info("AsyncBatchService stopped successfully")

    async def submit_batch_job(
        self,
        texts: list[str],
        priority: str = "medium",
        max_batch_size: int | None = None,
        timeout_seconds: int | None = None,
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
            ValueError: If texts list is empty or queue is full.
        """
        # Validate and normalize priority
        try:
            priority_enum = Priority(priority.lower())
        except ValueError:
            priority_enum = Priority.MEDIUM
            logger.warning(f"Invalid priority '{priority}', defaulting to medium")

        # Create job via job manager
        job = await self.job_manager.create_job(
            texts=texts,
            priority=priority_enum,
            max_batch_size=max_batch_size,
            timeout_seconds=timeout_seconds,
        )

        # Ensure queues are initialized
        if self.queue_manager._priority_queues is None:
            await self.queue_manager.initialize_queues()

        # Enqueue job
        try:
            await self.queue_manager.enqueue_job(job)
            logger.info(
                f"Submitted batch job {job.job_id}",
                priority=priority_enum.value,
                batch_size=len(texts),
            )
        except ValueError as e:
            # Update job status to failed if queue is full
            await self.job_manager.update_job_status(
                job.job_id,
                BatchJobStatus.FAILED,
                error=str(e),
            )
            raise

        return job

    async def get_job_status(self, job_id: str) -> BatchJob | None:
        """Retrieves the status of a specific batch job.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            A `BatchJob` instance if the job is found, `None` otherwise.
        """
        return await self.job_manager.get_job(job_id)

    async def get_job_results(
        self, job_id: str, page: int = 1, page_size: int = 100
    ) -> BatchPredictionResults | None:
        """Retrieves the results of a completed batch job with pagination.

        Args:
            job_id: The unique identifier of the job.
            page: The page number of the results to retrieve.
            page_size: The number of results per page.

        Returns:
            A `BatchPredictionResults` object if the job is complete, `None`
            otherwise.
        """
        # Check cache first
        cached_results = await self.cache_manager.get_cached_result(job_id)
        if cached_results is not None:
            job = await self.job_manager.get_job(job_id)
            # Only return cached results if job is actually completed
            if job and job.status == BatchJobStatus.COMPLETED:
                return self._paginate_results(job_id, cached_results, page, page_size)

        # Get job from job manager
        job = await self.job_manager.get_job(job_id)
        if job is None:
            return None

        # Check if job is completed
        if job.status != BatchJobStatus.COMPLETED:
            return None

        if job.results is None:
            return None

        # Paginate results
        return self._paginate_results(job_id, job.results, page, page_size)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancels a pending or in-progress batch job.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            `True` if the job was successfully cancelled, `False` otherwise.
        """
        return await self.job_manager.cancel_job(job_id)

    async def get_batch_metrics(self) -> AsyncBatchMetricsResponse:
        """Retrieves performance metrics for the batch processing service.

        Returns:
            An `AsyncBatchMetricsResponse` object with detailed metrics.
        """
        metrics = self.job_manager.get_metrics()

        # Update calculated averages
        metrics.update_averages()

        # Update queue size from queue manager
        queue_status = self.queue_manager.get_queue_status()
        metrics.queue_size = queue_status["total"]

        return AsyncBatchMetricsResponse(
            total_jobs=metrics.total_jobs,
            active_jobs=metrics.active_jobs,
            completed_jobs=metrics.completed_jobs,
            failed_jobs=metrics.failed_jobs,
            average_processing_time_seconds=metrics.average_processing_time_seconds,
            average_throughput_tps=metrics.average_throughput_tps,
            queue_size=metrics.queue_size,
            average_batch_size=metrics.average_batch_size,
            processing_efficiency=metrics.processing_efficiency,
        )

    def get_job_queue_status(self) -> dict[str, int]:
        """Returns the current status of all priority queues.

        Returns:
            A dictionary with queue sizes for each priority level.
        """
        return self.queue_manager.get_queue_status()

    async def _process_job(self, job: BatchJob) -> None:
        """Processes a single batch job.

        Args:
            job: The job to process.
        """
        start_time = time.time()

        # Update job status to processing
        await self.job_manager.update_job_status(
            job.job_id,
            BatchJobStatus.PROCESSING,
            started_at=start_time,
        )

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

                # Update progress
                processed_count = len(all_results)
                progress = processed_count / len(job.texts)
                await self.job_manager.update_job_status(
                    job.job_id,
                    BatchJobStatus.PROCESSING,
                    progress=progress,
                    processed_count=processed_count,
                )

            # Mark job as completed
            completed_at = time.time()
            processing_time = completed_at - start_time

            # Get current job to check status
            current_job = await self.job_manager.get_job(job.job_id)
            if current_job and current_job.status != BatchJobStatus.CANCELLED:
                await self.job_manager.update_job_status(
                    job.job_id,
                    BatchJobStatus.COMPLETED,
                    results=all_results,
                    completed_at=completed_at,
                    progress=1.0,
                    processed_count=len(job.texts),
                )

                # Update metrics for processing time
                metrics = self.job_manager.get_metrics()
                metrics.total_processing_time_seconds += processing_time
                metrics.total_texts_processed += len(job.texts)
                if metrics.completed_jobs > 0:
                    batch_size_avg = (
                        metrics.average_batch_size * (metrics.completed_jobs - 1) + len(job.texts)
                    ) / metrics.completed_jobs
                    metrics.average_batch_size = batch_size_avg

                    # Cache results only for successfully completed jobs
                    await self.cache_manager.cache_result(
                        job.job_id, current_job.to_dict(), all_results
                    )

            logger.info(
                f"Completed batch job {job.job_id}",
                processing_time_seconds=processing_time,
                total_texts=len(job.texts),
            )

        except Exception as e:
            # Mark job as failed
            failed_at = time.time()
            current_job = await self.job_manager.get_job(job.job_id)
            if current_job and current_job.status != BatchJobStatus.CANCELLED:
                await self.job_manager.update_job_status(
                    job.job_id,
                    BatchJobStatus.FAILED,
                    error=str(e),
                    completed_at=failed_at,
                )

            logger.error(
                f"Failed to process batch job {job.job_id}",
                error=str(e),
                exc_info=True,
            )

    def _paginate_results(
        self, job_id: str, results: list[dict[str, Any]], page: int, page_size: int
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
