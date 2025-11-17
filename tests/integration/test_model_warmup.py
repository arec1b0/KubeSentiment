"""
Unit tests for the ModelWarmup monitoring module.

Tests the ModelWarmupManager and WarmupHealthCheck classes,
including model warm-up operations, health checks, and singleton behavior.
"""

import pytest


import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.monitoring.model_warmup import (
    ModelWarmupManager,
    WarmupHealthCheck,
    get_warmup_manager,
    reset_warmup_manager,
)


class MockModel:
    """Mock model for testing warm-up operations."""

    def __init__(self, prediction_time: float = 0.01, should_fail: bool = False):
        """
        Initialize mock model.

        Args:
            prediction_time: Time to simulate for each prediction.
            should_fail: Whether predictions should raise exceptions.
        """
        self.prediction_time = prediction_time
        self.should_fail = should_fail
        self.predict_calls = 0

    def predict(self, text: str) -> Dict[str, Any]:
        """Synchronous predict method."""
        self.predict_calls += 1
        if self.should_fail:
            raise ValueError("Model prediction failed")
        import time

        time.sleep(self.prediction_time)
        return {"label": "positive", "score": 0.95}


class MockAsyncModel:
    """Mock async model for testing async warm-up operations."""

    def __init__(self, prediction_time: float = 0.01, should_fail: bool = False):
        """
        Initialize mock async model.

        Args:
            prediction_time: Time to simulate for each prediction.
            should_fail: Whether predictions should raise exceptions.
        """
        self.prediction_time = prediction_time
        self.should_fail = should_fail
        self.predict_calls = 0

    async def predict(self, text: str) -> Dict[str, Any]:
        """Asynchronous predict method."""
        self.predict_calls += 1
        if self.should_fail:
            raise ValueError("Async model prediction failed")
        await asyncio.sleep(self.prediction_time)
        return {"label": "positive", "score": 0.95}


@pytest.mark.integration
class TestModelWarmupManager:
    """Tests for the ModelWarmupManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        with patch("app.monitoring.model_warmup.get_settings"):
            return ModelWarmupManager()

    def test_initialization(self, manager):
        """Test manager initialization with default values."""
        assert not manager.is_warmed_up()
        assert manager.get_warmup_stats()["complete"] is False
        assert manager.get_warmup_stats()["timestamp"] is None
        assert manager.get_warmup_stats()["stats"] == {}

    def test_is_warmed_up_initially_false(self, manager):
        """Test that is_warmed_up returns False initially."""
        assert not manager.is_warmed_up()

    def test_get_warmup_stats_structure(self, manager):
        """Test that get_warmup_stats returns correct structure."""
        stats = manager.get_warmup_stats()

        assert "complete" in stats
        assert "timestamp" in stats
        assert "stats" in stats
        assert isinstance(stats["complete"], bool)

    @pytest.mark.asyncio
    async def test_warmup_model_sync_model(self, manager):
        """Test warming up a synchronous model."""
        mock_model = MockModel(prediction_time=0.001)

        result = await manager.warmup_model(mock_model, num_iterations=5)

        assert "total_warmup_time_ms" in result
        assert "avg_inference_time_ms" in result
        assert result["total_warmup_time_ms"] > 0
        assert result["avg_inference_time_ms"] > 0
        assert mock_model.predict_calls == 5

    @pytest.mark.asyncio
    async def test_warmup_model_async_model(self, manager):
        """Test warming up an asynchronous model."""
        mock_model = MockAsyncModel(prediction_time=0.001)

        result = await manager.warmup_model(mock_model, num_iterations=5)

        assert "total_warmup_time_ms" in result
        assert "avg_inference_time_ms" in result
        assert result["total_warmup_time_ms"] > 0
        assert result["avg_inference_time_ms"] > 0
        assert mock_model.predict_calls == 5

    @pytest.mark.asyncio
    async def test_warmup_model_sets_complete_flag(self, manager):
        """Test that warmup sets the complete flag correctly."""
        mock_model = MockModel(prediction_time=0.001)

        assert not manager.is_warmed_up()

        await manager.warmup_model(mock_model, num_iterations=3)

        # Should be warmed up if avg latency < 100ms
        assert manager.is_warmed_up()

    @pytest.mark.asyncio
    async def test_warmup_model_not_complete_on_slow_model(self, manager):
        """Test that warmup is not marked complete for slow models."""
        # Model with prediction time > 100ms
        mock_model = MockModel(prediction_time=0.15)

        await manager.warmup_model(mock_model, num_iterations=3)

        # Should not be warmed up if avg latency >= 100ms
        assert not manager.is_warmed_up()

    @pytest.mark.asyncio
    async def test_warmup_model_sets_timestamp(self, manager):
        """Test that warmup sets the timestamp."""
        mock_model = MockModel(prediction_time=0.001)

        stats_before = manager.get_warmup_stats()
        assert stats_before["timestamp"] is None

        await manager.warmup_model(mock_model, num_iterations=3)

        stats_after = manager.get_warmup_stats()
        assert stats_after["timestamp"] is not None
        assert stats_after["timestamp"] > 0

    @pytest.mark.asyncio
    async def test_warmup_model_handles_failures(self, manager):
        """Test that warmup handles model failures gracefully."""
        mock_model = MockModel(should_fail=True)

        # Should not raise exception
        result = await manager.warmup_model(mock_model, num_iterations=5)

        # Result should have stats even with failures
        assert "total_warmup_time_ms" in result
        assert "avg_inference_time_ms" in result
        # Average should be 0 since all predictions failed
        assert result["avg_inference_time_ms"] == 0

    @pytest.mark.asyncio
    async def test_warmup_model_partial_failures(self, manager):
        """Test warmup with partial failures."""
        # Create a model that fails on first 2 calls
        call_count = 0

        class PartialFailModel:
            async def predict(self, text):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise ValueError("Failure")
                await asyncio.sleep(0.001)
                return {"label": "positive"}

        partial_fail_model = PartialFailModel()

        result = await manager.warmup_model(partial_fail_model, num_iterations=5)

        # Should have some successful predictions
        assert result["avg_inference_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_warmup_model_different_iterations(self, manager):
        """Test warmup with different iteration counts."""
        mock_model = MockModel(prediction_time=0.001)

        # Test with different iteration counts
        for iterations in [1, 5, 10, 20]:
            result = await manager.warmup_model(mock_model, num_iterations=iterations)
            assert result["total_warmup_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_warmup_model_uses_different_texts(self, manager):
        """Test that warmup cycles through different test texts."""
        texts_used = []

        class TextCapturingModel:
            def predict(self, text):
                texts_used.append(text)
                return {"label": "positive"}

        text_model = TextCapturingModel()

        await manager.warmup_model(text_model, num_iterations=10)

        # Should use all 3 different warmup texts
        unique_texts = set(texts_used)
        assert len(unique_texts) == 3

    @pytest.mark.asyncio
    async def test_warmup_multiple_models_sync(self, manager):
        """Test warming up multiple synchronous models."""
        models = {
            "model1": MockModel(prediction_time=0.001),
            "model2": MockModel(prediction_time=0.001),
            "model3": MockModel(prediction_time=0.001),
        }

        results = await manager.warmup_multiple_models(models, iterations_per_model=3)

        assert len(results) == 3
        assert "model1" in results
        assert "model2" in results
        assert "model3" in results

        for model_name, result in results.items():
            if not isinstance(result, Exception):
                assert "total_warmup_time_ms" in result
                assert "avg_inference_time_ms" in result

    @pytest.mark.asyncio
    async def test_warmup_multiple_models_async(self, manager):
        """Test warming up multiple asynchronous models."""
        models = {
            "model1": MockAsyncModel(prediction_time=0.001),
            "model2": MockAsyncModel(prediction_time=0.001),
        }

        results = await manager.warmup_multiple_models(models, iterations_per_model=2)

        assert len(results) == 2
        for result in results.values():
            if not isinstance(result, Exception):
                assert "total_warmup_time_ms" in result

    @pytest.mark.asyncio
    async def test_warmup_multiple_models_with_failures(self, manager):
        """Test warmup of multiple models when some fail."""
        models = {
            "good_model": MockModel(prediction_time=0.001),
            "bad_model": MockModel(should_fail=True),
        }

        results = await manager.warmup_multiple_models(models, iterations_per_model=2)

        # Good model should have valid results
        assert "good_model" in results
        # Both should return results (even if failed)
        assert "bad_model" in results

    @pytest.mark.asyncio
    async def test_warmup_multiple_models_empty_dict(self, manager):
        """Test warmup with empty models dictionary."""
        results = await manager.warmup_multiple_models({}, iterations_per_model=2)
        assert results == {}

    @pytest.mark.asyncio
    async def test_warmup_stats_updated_after_warmup(self, manager):
        """Test that get_warmup_stats returns updated stats after warmup."""
        mock_model = MockModel(prediction_time=0.001)

        stats_before = manager.get_warmup_stats()
        assert stats_before["stats"] == {}

        await manager.warmup_model(mock_model, num_iterations=3)

        stats_after = manager.get_warmup_stats()
        assert "total_warmup_time_ms" in stats_after["stats"]
        assert "avg_inference_time_ms" in stats_after["stats"]


@pytest.mark.integration
class TestWarmupHealthCheck:
    """Tests for the WarmupHealthCheck class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        with patch("app.monitoring.model_warmup.get_settings"):
            return ModelWarmupManager()

    @pytest.fixture
    def health_check(self, manager):
        """Create a health check with a manager."""
        return WarmupHealthCheck(manager)

    def test_initialization(self, manager):
        """Test health check initialization."""
        health_check = WarmupHealthCheck(manager)
        assert health_check.warmup_manager is manager

    def test_check_warmup_status_not_ready(self, health_check):
        """Test check_warmup_status when not warmed up."""
        status = health_check.check_warmup_status()

        assert status["status"] == "warming_up"
        assert status["warmed_up"] is False
        assert "performance" in status

    @pytest.mark.asyncio
    async def test_check_warmup_status_ready(self, manager, health_check):
        """Test check_warmup_status when warmed up."""
        mock_model = MockModel(prediction_time=0.001)

        # Warm up the model
        await manager.warmup_model(mock_model, num_iterations=3)

        status = health_check.check_warmup_status()

        assert status["status"] == "ready"
        assert status["warmed_up"] is True
        assert "performance" in status

    def test_is_ready_initially_false(self, health_check):
        """Test is_ready returns False initially."""
        assert not health_check.is_ready()

    @pytest.mark.asyncio
    async def test_is_ready_after_warmup(self, manager, health_check):
        """Test is_ready returns True after successful warmup."""
        mock_model = MockModel(prediction_time=0.001)

        await manager.warmup_model(mock_model, num_iterations=3)

        assert health_check.is_ready()

    @pytest.mark.asyncio
    async def test_is_ready_false_for_slow_model(self, manager, health_check):
        """Test is_ready returns False if warmup fails (slow model)."""
        mock_model = MockModel(prediction_time=0.15)

        await manager.warmup_model(mock_model, num_iterations=3)

        assert not health_check.is_ready()

    def test_check_warmup_status_performance_empty_initially(self, health_check):
        """Test that performance is empty initially."""
        status = health_check.check_warmup_status()
        assert status["performance"] == {}

    @pytest.mark.asyncio
    async def test_check_warmup_status_performance_populated(self, manager, health_check):
        """Test that performance is populated after warmup."""
        mock_model = MockModel(prediction_time=0.001)

        await manager.warmup_model(mock_model, num_iterations=3)

        status = health_check.check_warmup_status()
        perf = status["performance"]

        assert "total_warmup_time_ms" in perf
        assert "avg_inference_time_ms" in perf


@pytest.mark.integration
class TestGetWarmupManager:
    """Tests for the get_warmup_manager singleton function."""

    def teardown_method(self):
        """Reset the singleton after each test."""
        reset_warmup_manager()

    @patch("app.monitoring.model_warmup.get_settings")
    def test_singleton_initialization(self, mock_get_settings):
        """Test that get_warmup_manager creates a singleton instance."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        manager1 = get_warmup_manager()
        manager2 = get_warmup_manager()

        # Same instance
        assert manager1 is manager2

        # get_settings should only be called once
        assert mock_get_settings.call_count == 1

    @patch("app.monitoring.model_warmup.get_settings")
    def test_reset_warmup_manager(self, mock_get_settings):
        """Test that reset_warmup_manager creates a new instance."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        manager1 = get_warmup_manager()
        reset_warmup_manager()
        manager2 = get_warmup_manager()

        # Different instances after reset
        assert manager1 is not manager2


@pytest.mark.integration
class TestModelWarmupIntegration:
    """Integration tests for model warmup functionality."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        with patch("app.monitoring.model_warmup.get_settings"):
            return ModelWarmupManager()

    @pytest.mark.asyncio
    async def test_full_warmup_workflow(self, manager):
        """Test complete warmup workflow from start to health check."""
        # Create mock model and health check
        mock_model = MockModel(prediction_time=0.001)
        health_check = WarmupHealthCheck(manager)

        # Initial state
        assert not health_check.is_ready()
        initial_status = health_check.check_warmup_status()
        assert initial_status["status"] == "warming_up"

        # Perform warmup
        warmup_result = await manager.warmup_model(mock_model, num_iterations=5)
        assert warmup_result["avg_inference_time_ms"] > 0

        # Check health after warmup
        assert health_check.is_ready()
        final_status = health_check.check_warmup_status()
        assert final_status["status"] == "ready"
        assert final_status["warmed_up"] is True

    @pytest.mark.asyncio
    async def test_concurrent_warmup_calls(self, manager):
        """Test that concurrent warmup calls work correctly."""
        models = [MockAsyncModel(prediction_time=0.001) for _ in range(5)]

        # Run warmup concurrently
        tasks = [manager.warmup_model(model, num_iterations=3) for model in models]
        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 5
        for result in results:
            assert "avg_inference_time_ms" in result

    @pytest.mark.asyncio
    async def test_warmup_performance_metrics_accuracy(self, manager):
        """Test that performance metrics are reasonably accurate."""
        mock_model = MockModel(prediction_time=0.01)

        result = await manager.warmup_model(mock_model, num_iterations=10)

        # Average latency should be around 10ms (0.01s)
        # Allow for some variance due to system overhead
        assert 5 < result["avg_inference_time_ms"] < 50

        # Total time should be > avg time * iterations
        assert result["total_warmup_time_ms"] >= result["avg_inference_time_ms"] * 10
