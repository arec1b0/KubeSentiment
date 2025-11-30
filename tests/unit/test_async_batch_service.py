import asyncio
from typing import Any, Callable

import pytest

from app.models.batch_job import BatchJobStatus, Priority
from app.services.async_batch_service import AsyncBatchService


class DummyPredictionService:
    """Lightweight stand-in; AsyncBatchService doesn't invoke it directly."""

    model = None


class FakeStreamProcessor:
    """Async stream processor double with optional batch failure."""

    def __init__(self, fail_on_batch: int | None = None):
        self.fail_on_batch = fail_on_batch
        self._batch_calls = 0

    async def predict_async_batch(self, texts: list[str], batch_id: str) -> list[dict[str, Any]]:
        self._batch_calls += 1
        await asyncio.sleep(0)  # yield control for realistic scheduling

        if self.fail_on_batch and self._batch_calls == self.fail_on_batch:
            raise RuntimeError("synthetic failure")

        return [
            {"label": "POSITIVE", "score": 0.9, "text_length": len(text), "backend": batch_id}
            for text in texts
        ]


class PerfSettings:
    async_batch_enabled = True
    async_batch_max_jobs = 100
    async_batch_max_batch_size = 2
    async_batch_default_timeout_seconds = 5
    async_batch_priority_high_limit = 5
    async_batch_priority_medium_limit = 5
    async_batch_priority_low_limit = 5
    async_batch_cleanup_interval_seconds = 60
    async_batch_cache_ttl_seconds = 60
    async_batch_result_cache_max_size = 50


class FakeSettings:
    def __init__(self):
        self.performance = PerfSettings()


@pytest.fixture
def make_service() -> Callable[..., AsyncBatchService]:
    def _make(stream_processor: FakeStreamProcessor | None = None) -> AsyncBatchService:
        return AsyncBatchService(
            prediction_service=DummyPredictionService(),
            stream_processor=stream_processor or FakeStreamProcessor(),
            settings=FakeSettings(),
        )

    return _make


@pytest.mark.asyncio
async def test_submit_batch_job_strips_and_validates_texts(
    make_service: Callable[..., AsyncBatchService],
):
    service = make_service()

    job = await service.submit_batch_job(["  keep ", "", "drop", "   "], priority="HIGH")

    assert job.texts == ["keep", "drop"]
    assert job.priority == Priority.HIGH


@pytest.mark.asyncio
async def test_processing_loop_handles_partial_failures(
    make_service: Callable[..., AsyncBatchService],
):
    service = make_service(FakeStreamProcessor(fail_on_batch=2))
    texts = ["one", "two", "three", "four", "five"]

    job = await service.submit_batch_job(texts, priority="medium", max_batch_size=2)
    await service._process_job(job)

    assert job.status == BatchJobStatus.COMPLETED
    assert job.failed_count == 2
    assert sum(1 for result in job.results if result["label"] == "ERROR") == 2  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_pagination_bounds_and_summary(make_service: Callable[..., AsyncBatchService]):
    service = make_service()
    results = [
        {"label": "POSITIVE", "score": 0.9},
        {"label": "ERROR", "score": 0.0},
        {},
    ]

    paginated = service._paginate_results("job123", results, page=0, page_size=0)

    assert paginated.page == 1
    assert paginated.page_size == 1
    assert paginated.total_results == 3
    assert paginated.summary["successful_predictions"] == 1
    assert paginated.summary["failed_predictions"] == 1
    assert paginated.summary["success_rate"] == pytest.approx(1 / 3)


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_payload_when_job_results_missing(
    make_service: Callable[..., AsyncBatchService],
):
    service = make_service()
    job = await service.submit_batch_job(["alpha", "beta"], priority="medium")
    await service._process_job(job)

    # Simulate results being cleared while cache still holds data
    stored_job = await service.get_job_status(job.job_id)
    stored_job.results = None  # type: ignore[assignment]

    cached = await service.get_job_results(job.job_id, page=1, page_size=10)

    assert cached is not None
    assert len(cached.results) == 2
    assert cached.summary["total_texts"] == 2


@pytest.mark.asyncio
async def test_priority_integration_processes_high_before_low(
    make_service: Callable[..., AsyncBatchService],
):
    service = make_service()
    high_job = await service.submit_batch_job(["high"], priority="high")
    low_job = await service.submit_batch_job(["low"], priority="low")

    dequeued_high = await service.queue_manager.dequeue_job(Priority.HIGH, timeout=0.1)
    assert dequeued_high.job_id == high_job.job_id  # type: ignore[union-attr]
    await service._process_job(dequeued_high)  # type: ignore[arg-type]

    high_status = await service.get_job_status(high_job.job_id)
    low_status = await service.get_job_status(low_job.job_id)

    assert high_status.status == BatchJobStatus.COMPLETED
    assert low_status.status == BatchJobStatus.PENDING


@pytest.mark.asyncio
async def test_start_stop_service_lifecycle(make_service: Callable[..., AsyncBatchService]):
    """Test service start/stop lifecycle."""
    service = make_service()

    # Start service
    await service.start()
    assert service._running is True

    # Try starting again (should warn but not fail)
    await service.start()

    # Stop service
    await service.stop()
    assert service._running is False

    # Try stopping again (should warn but not fail)
    await service.stop()


@pytest.mark.asyncio
async def test_submit_empty_texts_raises_error(make_service: Callable[..., AsyncBatchService]):
    """Test that submitting empty texts raises ValueError."""
    service = make_service()

    with pytest.raises(ValueError, match="at least one non-empty string"):
        await service.submit_batch_job([])

    with pytest.raises(ValueError, match="at least one non-empty string"):
        await service.submit_batch_job(["", "   ", "\t"])


@pytest.mark.asyncio
async def test_submit_invalid_texts_type_raises_error(
    make_service: Callable[..., AsyncBatchService],
):
    """Test that submitting non-list texts raises ValueError."""
    service = make_service()

    with pytest.raises(ValueError, match="must be provided as a list"):
        await service.submit_batch_job("not a list")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_job_timeout_during_processing(make_service: Callable[..., AsyncBatchService]):
    """Test that jobs timeout correctly during processing."""
    import time

    from app.models.batch_job import BatchJob

    service = make_service()

    # Create a job with very short timeout
    job = await service.submit_batch_job(["text1", "text2"], timeout_seconds=0.1)

    # Manually set created_at to simulate timeout
    job.created_at = time.time() - 1.0  # 1 second ago

    # Process job - should timeout
    await service._process_job(job)

    # Check job status
    updated_job = await service.get_job_status(job.job_id)
    assert updated_job is not None
    assert updated_job.status == BatchJobStatus.EXPIRED


@pytest.mark.asyncio
async def test_cancel_job_during_processing(make_service: Callable[..., AsyncBatchService]):
    """Test cancelling a job during processing."""
    service = make_service()

    job = await service.submit_batch_job(["text1", "text2", "text3"], priority="medium")

    # Start processing
    process_task = asyncio.create_task(service._process_job(job))

    # Cancel job
    cancelled = await service.cancel_job(job.job_id)
    assert cancelled is True

    # Wait for processing to finish
    await process_task

    # Check job status
    updated_job = await service.get_job_status(job.job_id)
    assert updated_job is not None
    assert updated_job.status == BatchJobStatus.CANCELLED


@pytest.mark.asyncio
async def test_get_job_results_nonexistent_job(make_service: Callable[..., AsyncBatchService]):
    """Test getting results for non-existent job returns None."""
    service = make_service()

    results = await service.get_job_results("nonexistent-job-id")
    assert results is None


@pytest.mark.asyncio
async def test_get_job_results_pending_job_returns_none(
    make_service: Callable[..., AsyncBatchService],
):
    """Test getting results for pending job returns None."""
    service = make_service()

    job = await service.submit_batch_job(["text1"], priority="medium")

    # Job should still be pending
    results = await service.get_job_results(job.job_id)
    assert results is None


@pytest.mark.asyncio
async def test_get_batch_metrics(make_service: Callable[..., AsyncBatchService]):
    """Test getting batch metrics."""
    service = make_service()
    await service.start()

    # Submit and process a job
    job = await service.submit_batch_job(["text1", "text2"], priority="medium")
    await service._process_job(job)

    # Get metrics
    metrics = await service.get_batch_metrics()

    assert metrics.total_jobs >= 1
    assert metrics.completed_jobs >= 1
    assert metrics.queue_size >= 0
    assert metrics.average_processing_time_seconds >= 0

    await service.stop()


@pytest.mark.asyncio
async def test_get_job_queue_status(make_service: Callable[..., AsyncBatchService]):
    """Test getting queue status."""
    service = make_service()
    await service.start()

    # Submit jobs with different priorities
    await service.submit_batch_job(["high1"], priority="high")
    await service.submit_batch_job(["medium1"], priority="medium")
    await service.submit_batch_job(["low1"], priority="low")

    queue_status = service.get_job_queue_status()

    assert "high" in queue_status
    assert "medium" in queue_status
    assert "low" in queue_status
    assert queue_status["high"] >= 0
    assert queue_status["medium"] >= 0
    assert queue_status["low"] >= 0

    await service.stop()


@pytest.mark.asyncio
async def test_normalize_priority_variations(make_service: Callable[..., AsyncBatchService]):
    """Test priority normalization handles various inputs."""
    service = make_service()

    # Test string priorities
    job1 = await service.submit_batch_job(["text"], priority="HIGH")
    assert job1.priority == Priority.HIGH

    job2 = await service.submit_batch_job(["text"], priority="low")
    assert job2.priority == Priority.LOW

    job3 = await service.submit_batch_job(["text"], priority="MEDIUM")
    assert job3.priority == Priority.MEDIUM

    # Test enum priority
    job4 = await service.submit_batch_job(["text"], priority=Priority.HIGH)
    assert job4.priority == Priority.HIGH

    # Test None (should default to medium)
    job5 = await service.submit_batch_job(["text"], priority=None)
    assert job5.priority == Priority.MEDIUM

    # Test invalid priority (should default to medium)
    job6 = await service.submit_batch_job(["text"], priority="invalid")  # type: ignore[arg-type]
    assert job6.priority == Priority.MEDIUM


@pytest.mark.asyncio
async def test_pagination_edge_cases(make_service: Callable[..., AsyncBatchService]):
    """Test pagination handles edge cases."""
    service = make_service()

    results = [{"label": "POSITIVE", "score": 0.9} for _ in range(10)]

    # Test page 0 (should normalize to 1)
    paginated = service._paginate_results("job1", results, page=0, page_size=5)
    assert paginated.page == 1

    # Test negative page (should normalize to 1)
    paginated = service._paginate_results("job1", results, page=-1, page_size=5)
    assert paginated.page == 1

    # Test page beyond results (should return last page)
    paginated = service._paginate_results("job1", results, page=100, page_size=5)
    assert (
        paginated.page == 2
    )  # Should return last available page (10 results / 5 per page = 2 pages)
    assert len(paginated.results) == 5  # Last page should have 5 results

    # Test empty results
    paginated = service._paginate_results("job1", [], page=1, page_size=10)
    assert paginated.total_results == 0
    assert paginated.summary["success_rate"] == 0.0


@pytest.mark.asyncio
async def test_build_error_result(make_service: Callable[..., AsyncBatchService]):
    """Test error result building."""
    service = make_service()

    error_result = service._build_error_result("Test error", "test text")

    assert error_result["label"] == "ERROR"
    assert error_result["score"] == 0.0
    assert error_result["error"] == "Test error"
    assert error_result["text_length"] == len("test text")
    assert error_result["backend"] == "async_batch"


@pytest.mark.asyncio
async def test_is_error_result(make_service: Callable[..., AsyncBatchService]):
    """Test error result detection."""
    service = make_service()

    assert service._is_error_result({"label": "ERROR"}) is True
    assert service._is_error_result({"label": "POSITIVE"}) is False
    assert service._is_error_result({}) is False


@pytest.mark.asyncio
async def test_extract_label(make_service: Callable[..., AsyncBatchService]):
    """Test label extraction from various result formats."""
    service = make_service()

    assert service._extract_label({"label": "POSITIVE"}) == "POSITIVE"
    assert service._extract_label({"label": "ERROR"}) == "ERROR"
    assert service._extract_label({}) is None

    # Test with object-like dict
    class MockResult:
        label = "POSITIVE"

    assert service._extract_label(MockResult()) == "POSITIVE"
    assert service._extract_label(MockResult()) == "POSITIVE"
