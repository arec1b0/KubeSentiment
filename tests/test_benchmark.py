"""
Unit tests for the benchmark utilities module.

Tests the PerformanceBenchmark class and related dataclasses,
including benchmarking methods, result comparisons, and metrics calculations.
"""

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from app.utils.benchmark import (
    BenchmarkResult,
    ComparisonResult,
    PerformanceBenchmark,
)


class MockModel:
    """Mock model for testing benchmark operations."""

    def __init__(self, latency_ms: float = 10.0, should_fail: bool = False):
        """
        Initialize mock model.

        Args:
            latency_ms: Latency to simulate for each prediction.
            should_fail: Whether predictions should raise exceptions.
        """
        self.latency_ms = latency_ms
        self.should_fail = should_fail
        self.predict_calls = 0
        self.predict_batch_calls = 0

    def predict(self, text: str) -> Dict[str, Any]:
        """Synchronous predict method."""
        self.predict_calls += 1
        if self.should_fail:
            raise ValueError("Model prediction failed")
        time.sleep(self.latency_ms / 1000)
        return {"label": "positive", "score": 0.95}

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Batch predict method."""
        self.predict_batch_calls += 1
        if self.should_fail:
            raise ValueError("Batch prediction failed")
        time.sleep(self.latency_ms / 1000)
        return [{"label": "positive", "score": 0.95} for _ in texts]


class TestBenchmarkResult:
    """Tests for the BenchmarkResult dataclass."""

    def test_creation(self):
        """Test creating a BenchmarkResult."""
        result = BenchmarkResult(
            method="test_method",
            total_requests=100,
            total_time_ms=1000.0,
            avg_latency_ms=10.0,
            min_latency_ms=5.0,
            max_latency_ms=20.0,
            throughput_rps=100.0,
            p50_latency_ms=10.0,
            p95_latency_ms=15.0,
            p99_latency_ms=18.0,
        )

        assert result.method == "test_method"
        assert result.total_requests == 100
        assert result.total_time_ms == 1000.0
        assert result.avg_latency_ms == 10.0
        assert result.min_latency_ms == 5.0
        assert result.max_latency_ms == 20.0
        assert result.throughput_rps == 100.0
        assert result.p50_latency_ms == 10.0
        assert result.p95_latency_ms == 15.0
        assert result.p99_latency_ms == 18.0


class TestComparisonResult:
    """Tests for the ComparisonResult dataclass."""

    def test_creation(self):
        """Test creating a ComparisonResult."""
        baseline = BenchmarkResult(
            method="baseline",
            total_requests=100,
            total_time_ms=2000.0,
            avg_latency_ms=20.0,
            min_latency_ms=10.0,
            max_latency_ms=30.0,
            throughput_rps=50.0,
            p50_latency_ms=20.0,
            p95_latency_ms=25.0,
            p99_latency_ms=28.0,
        )

        optimized = BenchmarkResult(
            method="optimized",
            total_requests=100,
            total_time_ms=1000.0,
            avg_latency_ms=10.0,
            min_latency_ms=5.0,
            max_latency_ms=15.0,
            throughput_rps=100.0,
            p50_latency_ms=10.0,
            p95_latency_ms=12.0,
            p99_latency_ms=14.0,
        )

        comparison = ComparisonResult(
            baseline=baseline,
            optimized=optimized,
            latency_reduction_pct=50.0,
            throughput_improvement_pct=100.0,
            speedup_factor=2.0,
        )

        assert comparison.baseline == baseline
        assert comparison.optimized == optimized
        assert comparison.latency_reduction_pct == 50.0
        assert comparison.throughput_improvement_pct == 100.0
        assert comparison.speedup_factor == 2.0


class TestPerformanceBenchmark:
    """Tests for the PerformanceBenchmark class."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock model for testing."""
        return MockModel(latency_ms=5.0)

    @pytest.fixture
    def benchmark(self, mock_model):
        """Create a benchmark instance."""
        return PerformanceBenchmark(mock_model)

    def test_initialization(self, mock_model):
        """Test PerformanceBenchmark initialization."""
        benchmark = PerformanceBenchmark(mock_model)
        assert benchmark.model is mock_model
        assert benchmark.logger is not None

    def test_calculate_percentiles_empty_list(self, benchmark):
        """Test percentile calculation with empty list."""
        result = benchmark._calculate_percentiles([])
        assert result["p50"] == 0.0
        assert result["p95"] == 0.0
        assert result["p99"] == 0.0

    def test_calculate_percentiles_single_value(self, benchmark):
        """Test percentile calculation with single value."""
        result = benchmark._calculate_percentiles([10.0])
        assert result["p50"] == 10.0
        assert result["p95"] == 10.0
        assert result["p99"] == 10.0

    def test_calculate_percentiles_sorted_list(self, benchmark):
        """Test percentile calculation with sorted values."""
        latencies = list(range(1, 101))  # 1 to 100
        result = benchmark._calculate_percentiles(latencies)

        # For a list of 100 values, percentiles should be close to:
        # p50 = 50th value, p95 = 95th value, p99 = 99th value
        assert result["p50"] == 50
        assert result["p95"] == 95
        assert result["p99"] == 99

    def test_calculate_percentiles_unsorted_list(self, benchmark):
        """Test percentile calculation with unsorted values."""
        latencies = [10.0, 5.0, 15.0, 20.0, 8.0]
        result = benchmark._calculate_percentiles(latencies)

        # Values should be: [5.0, 8.0, 10.0, 15.0, 20.0]
        assert result["p50"] == 10.0  # Middle value
        assert result["p95"] == 20.0  # 95th percentile
        assert result["p99"] == 20.0  # 99th percentile

    def test_benchmark_single_predictions_basic(self, benchmark, mock_model):
        """Test basic single prediction benchmark."""
        texts = ["test text 1", "test text 2", "test text 3"]

        result = benchmark.benchmark_single_predictions(texts, warmup_runs=0)

        assert result.method == "single_predictions"
        assert result.total_requests == 3
        assert result.total_time_ms > 0
        assert result.avg_latency_ms > 0
        assert result.min_latency_ms > 0
        assert result.max_latency_ms > 0
        assert result.throughput_rps > 0
        assert mock_model.predict_calls == 3

    def test_benchmark_single_predictions_with_warmup(self, benchmark, mock_model):
        """Test single prediction benchmark with warmup."""
        texts = ["text"] * 10

        result = benchmark.benchmark_single_predictions(texts, warmup_runs=3)

        # Should have 3 warmup calls + 10 measured calls
        assert mock_model.predict_calls == 13
        assert result.total_requests == 10

    def test_benchmark_single_predictions_large_dataset(self, benchmark):
        """Test single prediction benchmark with larger dataset."""
        texts = [f"test text {i}" for i in range(50)]

        result = benchmark.benchmark_single_predictions(texts, warmup_runs=2)

        assert result.total_requests == 50
        assert result.avg_latency_ms > 0
        assert result.p50_latency_ms > 0
        assert result.p95_latency_ms >= result.p50_latency_ms
        assert result.p99_latency_ms >= result.p95_latency_ms

    def test_benchmark_batch_predictions_basic(self, benchmark, mock_model):
        """Test basic batch prediction benchmark."""
        texts = [f"test text {i}" for i in range(10)]

        result = benchmark.benchmark_batch_predictions(texts, batch_size=5, warmup_runs=0)

        assert result.method == "batch_predictions_5"
        assert result.total_requests == 10
        assert result.total_time_ms > 0
        assert result.avg_latency_ms > 0
        # Should have 2 batches (10 texts / batch_size of 5)
        assert mock_model.predict_batch_calls == 2

    def test_benchmark_batch_predictions_with_warmup(self, benchmark, mock_model):
        """Test batch prediction benchmark with warmup."""
        texts = [f"test {i}" for i in range(20)]

        result = benchmark.benchmark_batch_predictions(texts, batch_size=10, warmup_runs=1)

        # Should have 1 warmup batch + 2 measured batches
        assert mock_model.predict_batch_calls == 3
        assert result.total_requests == 20

    def test_benchmark_batch_predictions_uneven_batches(self, benchmark, mock_model):
        """Test batch predictions with uneven batch sizes."""
        texts = [f"test {i}" for i in range(25)]

        result = benchmark.benchmark_batch_predictions(texts, batch_size=10, warmup_runs=0)

        # Should have 3 batches: 10, 10, 5
        assert mock_model.predict_batch_calls == 3
        assert result.total_requests == 25

    def test_benchmark_batch_predictions_different_batch_sizes(self, benchmark):
        """Test benchmark with different batch sizes."""
        texts = [f"test {i}" for i in range(32)]

        result1 = benchmark.benchmark_batch_predictions(texts, batch_size=8, warmup_runs=0)
        result2 = benchmark.benchmark_batch_predictions(texts, batch_size=16, warmup_runs=0)

        assert result1.method == "batch_predictions_8"
        assert result2.method == "batch_predictions_16"
        assert result1.total_requests == result2.total_requests == 32

    @pytest.mark.asyncio
    async def test_benchmark_stream_processing_basic(self):
        """Test basic stream processing benchmark."""
        mock_model = MockModel(latency_ms=5.0)
        benchmark = PerformanceBenchmark(mock_model)

        texts = [f"test {i}" for i in range(10)]

        result = await benchmark.benchmark_stream_processing(
            texts, batch_config=None, concurrency=5
        )

        assert result.method == "stream_processing_c5"
        assert result.total_requests == 10
        assert result.total_time_ms > 0
        assert result.avg_latency_ms > 0
        assert result.throughput_rps > 0

    @pytest.mark.asyncio
    async def test_benchmark_stream_processing_different_concurrency(self):
        """Test stream processing with different concurrency levels."""
        mock_model = MockModel(latency_ms=5.0)
        benchmark = PerformanceBenchmark(mock_model)

        texts = [f"test {i}" for i in range(20)]

        result1 = await benchmark.benchmark_stream_processing(texts, concurrency=5)
        result2 = await benchmark.benchmark_stream_processing(texts, concurrency=10)

        assert result1.method == "stream_processing_c5"
        assert result2.method == "stream_processing_c10"
        assert result1.total_requests == result2.total_requests == 20

    def test_compare_results_latency_reduction(self, benchmark):
        """Test comparison with latency reduction."""
        baseline = BenchmarkResult(
            method="baseline",
            total_requests=100,
            total_time_ms=2000.0,
            avg_latency_ms=20.0,
            min_latency_ms=10.0,
            max_latency_ms=30.0,
            throughput_rps=50.0,
            p50_latency_ms=20.0,
            p95_latency_ms=25.0,
            p99_latency_ms=28.0,
        )

        optimized = BenchmarkResult(
            method="optimized",
            total_requests=100,
            total_time_ms=1000.0,
            avg_latency_ms=10.0,
            min_latency_ms=5.0,
            max_latency_ms=15.0,
            throughput_rps=100.0,
            p50_latency_ms=10.0,
            p95_latency_ms=12.0,
            p99_latency_ms=14.0,
        )

        comparison = benchmark.compare_results(baseline, optimized)

        assert comparison.latency_reduction_pct == 50.0
        assert comparison.throughput_improvement_pct == 100.0
        assert comparison.speedup_factor == 2.0

    def test_compare_results_no_improvement(self, benchmark):
        """Test comparison with no improvement."""
        baseline = BenchmarkResult(
            method="baseline",
            total_requests=100,
            total_time_ms=1000.0,
            avg_latency_ms=10.0,
            min_latency_ms=5.0,
            max_latency_ms=15.0,
            throughput_rps=100.0,
            p50_latency_ms=10.0,
            p95_latency_ms=12.0,
            p99_latency_ms=14.0,
        )

        optimized = BenchmarkResult(
            method="optimized",
            total_requests=100,
            total_time_ms=1000.0,
            avg_latency_ms=10.0,
            min_latency_ms=5.0,
            max_latency_ms=15.0,
            throughput_rps=100.0,
            p50_latency_ms=10.0,
            p95_latency_ms=12.0,
            p99_latency_ms=14.0,
        )

        comparison = benchmark.compare_results(baseline, optimized)

        assert comparison.latency_reduction_pct == 0.0
        assert comparison.throughput_improvement_pct == 0.0
        assert comparison.speedup_factor == 1.0

    def test_compare_results_regression(self, benchmark):
        """Test comparison with performance regression."""
        baseline = BenchmarkResult(
            method="baseline",
            total_requests=100,
            total_time_ms=1000.0,
            avg_latency_ms=10.0,
            min_latency_ms=5.0,
            max_latency_ms=15.0,
            throughput_rps=100.0,
            p50_latency_ms=10.0,
            p95_latency_ms=12.0,
            p99_latency_ms=14.0,
        )

        regressed = BenchmarkResult(
            method="regressed",
            total_requests=100,
            total_time_ms=2000.0,
            avg_latency_ms=20.0,
            min_latency_ms=10.0,
            max_latency_ms=30.0,
            throughput_rps=50.0,
            p50_latency_ms=20.0,
            p95_latency_ms=25.0,
            p99_latency_ms=28.0,
        )

        comparison = benchmark.compare_results(baseline, regressed)

        # Negative reduction means increase
        assert comparison.latency_reduction_pct == -100.0
        assert comparison.throughput_improvement_pct == -50.0
        assert comparison.speedup_factor == 0.5

    def test_compare_results_edge_case_zero_baseline(self, benchmark):
        """Test comparison with zero baseline latency."""
        baseline = BenchmarkResult(
            method="baseline",
            total_requests=100,
            total_time_ms=0.0,
            avg_latency_ms=0.0,
            min_latency_ms=0.0,
            max_latency_ms=0.0,
            throughput_rps=0.0,
            p50_latency_ms=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
        )

        optimized = BenchmarkResult(
            method="optimized",
            total_requests=100,
            total_time_ms=1000.0,
            avg_latency_ms=10.0,
            min_latency_ms=5.0,
            max_latency_ms=15.0,
            throughput_rps=100.0,
            p50_latency_ms=10.0,
            p95_latency_ms=12.0,
            p99_latency_ms=14.0,
        )

        comparison = benchmark.compare_results(baseline, optimized)

        # Should handle division by zero gracefully
        assert comparison.latency_reduction_pct == 0.0
        assert comparison.speedup_factor == float("inf")

    def test_print_results(self, benchmark, capsys):
        """Test printing benchmark results."""
        result = BenchmarkResult(
            method="test_method",
            total_requests=100,
            total_time_ms=1000.0,
            avg_latency_ms=10.0,
            min_latency_ms=5.0,
            max_latency_ms=20.0,
            throughput_rps=100.0,
            p50_latency_ms=10.0,
            p95_latency_ms=15.0,
            p99_latency_ms=18.0,
        )

        benchmark.print_results(result)

        captured = capsys.readouterr()
        assert "test_method" in captured.out
        assert "100" in captured.out  # total requests
        assert "1000.00" in captured.out  # total time
        assert "10.00" in captured.out  # avg latency

    def test_print_comparison(self, benchmark, capsys):
        """Test printing comparison results."""
        baseline = BenchmarkResult(
            method="baseline",
            total_requests=100,
            total_time_ms=2000.0,
            avg_latency_ms=20.0,
            min_latency_ms=10.0,
            max_latency_ms=30.0,
            throughput_rps=50.0,
            p50_latency_ms=20.0,
            p95_latency_ms=25.0,
            p99_latency_ms=28.0,
        )

        optimized = BenchmarkResult(
            method="optimized",
            total_requests=100,
            total_time_ms=1000.0,
            avg_latency_ms=10.0,
            min_latency_ms=5.0,
            max_latency_ms=15.0,
            throughput_rps=100.0,
            p50_latency_ms=10.0,
            p95_latency_ms=12.0,
            p99_latency_ms=14.0,
        )

        comparison = ComparisonResult(
            baseline=baseline,
            optimized=optimized,
            latency_reduction_pct=50.0,
            throughput_improvement_pct=100.0,
            speedup_factor=2.0,
        )

        benchmark.print_comparison(comparison)

        captured = capsys.readouterr()
        assert "baseline" in captured.out
        assert "optimized" in captured.out
        assert "50.00" in captured.out  # latency reduction
        assert "100.00" in captured.out  # throughput improvement
        assert "2.00" in captured.out  # speedup factor


class TestBenchmarkIntegration:
    """Integration tests for benchmark functionality."""

    def test_full_benchmark_workflow(self):
        """Test complete benchmark workflow."""
        mock_model = MockModel(latency_ms=5.0)
        benchmark = PerformanceBenchmark(mock_model)

        texts = [f"test {i}" for i in range(20)]

        # Run single prediction benchmark
        single_result = benchmark.benchmark_single_predictions(texts, warmup_runs=2)
        assert single_result.total_requests == 20

        # Run batch prediction benchmark
        batch_result = benchmark.benchmark_batch_predictions(texts, batch_size=10, warmup_runs=1)
        assert batch_result.total_requests == 20

        # Compare results
        comparison = benchmark.compare_results(single_result, batch_result)
        assert comparison.baseline == single_result
        assert comparison.optimized == batch_result

    def test_benchmark_consistency(self):
        """Test that benchmarks produce consistent results."""
        mock_model = MockModel(latency_ms=5.0)
        benchmark = PerformanceBenchmark(mock_model)

        texts = ["test"] * 10

        # Run same benchmark multiple times
        results = [
            benchmark.benchmark_single_predictions(texts, warmup_runs=0)
            for _ in range(3)
        ]

        # Results should be similar (within reasonable variance)
        avg_latencies = [r.avg_latency_ms for r in results]
        max_variance = max(avg_latencies) - min(avg_latencies)

        # Variance should be relatively small (less than 50% of average)
        avg_of_avgs = sum(avg_latencies) / len(avg_latencies)
        assert max_variance < avg_of_avgs * 0.5
