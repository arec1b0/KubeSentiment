"""
Asynchronous batch processing service for high-throughput sentiment analysis.

The service coordinates four collaborators with clear responsibilities:
- BatchJobManager: Creates jobs, tracks lifecycle/metrics, enforces timeouts.
- PriorityQueueManager: Owns priority queues and worker lifecycle.
- StreamProcessor: Executes model inference in batches.
- ResultCacheManager: Caches completed job payloads for fast reads.

Only interact with the AsyncBatchCoordinator interface exposed here; avoid
reaching into managers directly to keep responsibilities decoupled.
"""

import asyncio
import time
from typing import Any, Protocol

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


class AsyncBatchCoordinator(Protocol):
    """Minimal surface area for orchestrating async batch work."""

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def submit_batch_job(
        self,
        texts: list[str],
        priority: str | Priority | None = None,
        max_batch_size: int | None = None,
        timeout_seconds: int | None = None,
    ) -> BatchJob: ...

    async def get_job_status(self, job_id: str) -> BatchJob | None: ...

    async def get_job_results(
        self, job_id: str, page: int = 1, page_size: int = 100
    ) -> BatchPredictionResults | None: ...

    async def cancel_job(self, job_id: str) -> bool: ...

    async def get_batch_metrics(self) -> AsyncBatchMetricsResponse: ...

    def get_job_queue_status(self) -> dict[str, int]: ...


logger = get_logger(__name__)


class AsyncBatchService(IAsyncBatchService):
    """A service for asynchronous, high-throughput batch processing.

    This service orchestrates focused collaborators:
    - BatchJobManager: Job creation, status tracking, lifecycle, metrics
    - PriorityQueueManager: Queue coordination, task ordering
    - ResultCacheManager: Result caching and cleanup
    - StreamProcessor: High-throughput inference for each batch

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
        await self.queue_manager.ensure_initialized()

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
        priority: str | Priority | None = "medium",
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
        normalized_texts = self._sanitize_texts(texts)
        priority_enum = self._normalize_priority(priority)

        # Create job via job manager
        job = await self.job_manager.create_job(
            texts=normalized_texts,
            priority=priority_enum,
            max_batch_size=max_batch_size,
            timeout_seconds=timeout_seconds,
        )

        # Ensure queues are initialized
        await self.queue_manager.ensure_initialized()

        # Enqueue job
        try:
            await self.queue_manager.enqueue_job(job)
            logger.info(
                f"Submitted batch job {job.job_id}",
                priority=priority_enum.value,
                batch_size=len(normalized_texts),
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

    @property
    def coordinator(self) -> AsyncBatchCoordinator:
        """Minimal surface to share with collaborators instead of internals."""
        return self

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
            all_results, failed_count = await self._process_job_batches(job)

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
                    processed_count=len(all_results),
                    failed_count=failed_count,
                )

                # Update metrics and cache only for successfully completed jobs
                await self.job_manager.record_processing_stats(
                    job.job_id, len(all_results), processing_time
                )

                refreshed_job = await self.job_manager.get_job(job.job_id)
                if refreshed_job and refreshed_job.status == BatchJobStatus.COMPLETED:
                    await self.cache_manager.cache_result(
                        job.job_id, refreshed_job.to_dict(), all_results
                    )

            logger.info(
                f"Completed batch job {job.job_id}",
                processing_time_seconds=processing_time,
                total_texts=len(job.texts),
                failed_batches=failed_count,
            )

        except asyncio.CancelledError:
            logger.info(f"Processing cancelled for job {job.job_id}")
            raise
        except TimeoutError as e:
            failed_at = time.time()
            current_job = await self.job_manager.get_job(job.job_id)
            if current_job and current_job.status != BatchJobStatus.CANCELLED:
                await self.job_manager.update_job_status(
                    job.job_id,
                    BatchJobStatus.EXPIRED,
                    error=str(e),
                    completed_at=failed_at,
                )
            logger.error(
                f"Timed out while processing batch job {job.job_id}",
                error=str(e),
                exc_info=True,
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

    async def _process_job_batches(self, job: BatchJob) -> tuple[list[dict[str, Any]], int]:
        """Processes a job in batches with cancellation and timeout checkpoints."""
        all_results: list[dict[str, Any]] = []
        failed_count = 0
        total_texts = len(job.texts)

        # Ensure batch_size is never zero
        batch_size = max(1, min(total_texts or 1, job.max_batch_size or total_texts or 1))

        for i in range(0, total_texts, batch_size):
            current_job = await self.job_manager.get_job(job.job_id)
            if current_job is None:
                break

            # Cancellation checkpoint
            if current_job.status == BatchJobStatus.CANCELLED:
                logger.info("Job cancelled mid-processing", job_id=job.job_id)
                break

            # Timeout enforcement
            if self._has_job_timed_out(current_job):
                raise TimeoutError("Job timed out during processing")

            batch_texts = current_job.texts[i : i + batch_size]
            batch_id = f"{job.job_id}_batch_{i // batch_size}"

            try:
                batch_results = await self.stream_processor.predict_async_batch(
                    batch_texts, batch_id
                )
            except Exception as batch_err:  # Continue processing remaining batches
                logger.error(
                    "Batch processing failed",
                    job_id=job.job_id,
                    batch_id=batch_id,
                    error=str(batch_err),
                    exc_info=True,
                )
                batch_results = [
                    self._build_error_result(str(batch_err), text) for text in batch_texts
                ]

            failed_count += sum(1 for r in batch_results if self._is_error_result(r))
            all_results.extend(batch_results)

            # Update progress after each batch
            processed_count = len(all_results)
            progress = processed_count / total_texts if total_texts > 0 else 1.0
            await self.job_manager.update_job_status(
                job.job_id,
                BatchJobStatus.PROCESSING,
                progress=progress,
                processed_count=processed_count,
                failed_count=failed_count,
            )

        return all_results, failed_count

    def _has_job_timed_out(self, job: BatchJob) -> bool:
        """Determine if the job exceeded its timeout while processing."""
        if not job.timeout_seconds or job.timeout_seconds <= 0:
            return False
        return (time.time() - job.created_at) >= job.timeout_seconds

    def _build_error_result(self, error_message: str, text: str) -> dict[str, Any]:
        """Create a standardized error result entry for failed predictions."""
        return {
            "label": "ERROR",
            "score": 0.0,
            "error": error_message,
            "inference_time_ms": 0.0,
            "model_name": "async_batch_service",
            "text_length": len(text),
            "backend": "async_batch",
            "cached": False,
        }

    def _paginate_results(
        self, job_id: str, results: list[dict[str, Any]], page: int, page_size: int
    ) -> BatchPredictionResults:
        """Paginates job results with bounds and summary safeguards."""
        safe_page = max(1, page)
        safe_page_size = max(1, page_size)
        total_results = len(results)
        start_idx = (safe_page - 1) * safe_page_size

        # Calculate actual page number when requested page is beyond available pages
        actual_page = safe_page
        if start_idx >= total_results and total_results > 0:
            # Adjust to show last page and calculate actual page number
            start_idx = max(total_results - safe_page_size, 0)
            actual_page = (total_results + safe_page_size - 1) // safe_page_size  # Ceiling division
        end_idx = min(start_idx + safe_page_size, total_results)
        paginated_results = results[start_idx:end_idx]

        # Convert to PredictionResponse objects
        prediction_responses = [
            PredictionResponse(**result) if isinstance(result, dict) else result
            for result in paginated_results
        ]

        labels = [self._extract_label(r) for r in results]
        successful_predictions = sum(1 for label in labels if label not in ("ERROR", None))
        failed_predictions = sum(1 for label in labels if label == "ERROR")

        summary = {
            "total_texts": total_results,
            "successful_predictions": successful_predictions,
            "failed_predictions": failed_predictions,
            "success_rate": (successful_predictions / total_results if total_results > 0 else 0.0),
        }

        return BatchPredictionResults(
            job_id=job_id,
            results=prediction_responses,
            total_results=total_results,
            page=actual_page,
            page_size=safe_page_size,
            has_more=end_idx < total_results,
            summary=summary,
        )

    def _extract_label(self, result: Any) -> Any:
        """Safely extract label from dicts or response objects."""
        if isinstance(result, dict):
            return result.get("label")
        return getattr(result, "label", None)

    def _is_error_result(self, result: Any) -> bool:
        """Determine if a result represents an error."""
        return self._extract_label(result) == "ERROR"

    def _sanitize_texts(self, texts: list[str]) -> list[str]:
        """Normalize and validate text payloads."""
        if not isinstance(texts, list):
            raise ValueError("texts must be provided as a list of strings")

        cleaned = [t.strip() for t in texts if isinstance(t, str) and t.strip()]
        if not cleaned:
            raise ValueError("texts must contain at least one non-empty string")
        return cleaned

    def _normalize_priority(self, priority: str | Priority | None) -> Priority:
        """Normalize priority input to enum with safe default."""
        if isinstance(priority, Priority):
            return priority
        try:
            return Priority((priority or "medium").lower())
        except Exception:
            logger.warning(f"Invalid priority '{priority}', defaulting to medium")
            return Priority.MEDIUM

    def _is_job_valid(self, job: BatchJob) -> bool:
        """Public wrapper to avoid exposing the manager directly in tests."""
        return self.job_manager.is_job_valid(job)
