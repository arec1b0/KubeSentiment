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
async def test_submit_batch_job_strips_and_validates_texts(make_service: Callable[..., AsyncBatchService]):
    service = make_service()

    job = await service.submit_batch_job(["  keep ", "", "drop", "   "], priority="HIGH")

    assert job.texts == ["keep", "drop"]
    assert job.priority == Priority.HIGH


@pytest.mark.asyncio
async def test_processing_loop_handles_partial_failures(make_service: Callable[..., AsyncBatchService]):
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
    make_service: Callable[..., AsyncBatchService]
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
async def test_priority_integration_processes_high_before_low(make_service: Callable[..., AsyncBatchService]):
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
