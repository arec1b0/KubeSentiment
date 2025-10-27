"""
Performance benchmarking utilities for measuring optimization improvements.

This module provides tools to benchmark and compare single vs. batch prediction
performance, demonstrating the significant latency reduction achieved through
stream processing vectorization.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.models.base import ModelStrategy
from app.services.stream_processor import BatchConfig, StreamProcessor

logger = get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Results from a benchmark run.

    Attributes:
        method: Name of the method being benchmarked.
        total_requests: Total number of requests processed.
        total_time_ms: Total time taken in milliseconds.
        avg_latency_ms: Average latency per request in milliseconds.
        min_latency_ms: Minimum latency observed.
        max_latency_ms: Maximum latency observed.
        throughput_rps: Throughput in requests per second.
        p50_latency_ms: 50th percentile latency.
        p95_latency_ms: 95th percentile latency.
        p99_latency_ms: 99th percentile latency.
    """
    method: str
    total_requests: int
    total_time_ms: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_rps: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


@dataclass
class ComparisonResult:
    """Comparison of two benchmark results.

    Attributes:
        baseline: Baseline benchmark result.
        optimized: Optimized benchmark result.
        latency_reduction_pct: Percentage reduction in latency.
        throughput_improvement_pct: Percentage improvement in throughput.
        speedup_factor: Speedup factor (baseline_time / optimized_time).
    """
    baseline: BenchmarkResult
    optimized: BenchmarkResult
    latency_reduction_pct: float
    throughput_improvement_pct: float
    speedup_factor: float


class PerformanceBenchmark:
    """Benchmarks prediction performance for single and batch methods.

    This class provides comprehensive benchmarking capabilities to measure
    and compare the performance of different prediction strategies.

    Attributes:
        model: The model strategy to benchmark.
    """

    def __init__(self, model: ModelStrategy):
        """Initializes the benchmark.

        Args:
            model: An instance of a model strategy for predictions.
        """
        self.model = model
        self.logger = get_logger(__name__)

    def _calculate_percentiles(self, latencies: List[float]) -> Dict[str, float]:
        """Calculates latency percentiles.

        Args:
            latencies: List of latency measurements in milliseconds.

        Returns:
            Dictionary with p50, p95, and p99 latencies.
        """
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        return {
            "p50": sorted_latencies[int(n * 0.50)] if n > 0 else 0.0,
            "p95": sorted_latencies[int(n * 0.95)] if n > 0 else 0.0,
            "p99": sorted_latencies[int(n * 0.99)] if n > 0 else 0.0,
        }

    def benchmark_single_predictions(
        self,
        texts: List[str],
        warmup_runs: int = 5
    ) -> BenchmarkResult:
        """Benchmarks sequential single predictions.

        Args:
            texts: List of texts to use for benchmarking.
            warmup_runs: Number of warmup predictions before measuring.

        Returns:
            BenchmarkResult containing performance metrics.
        """
        self.logger.info(
            "Starting single prediction benchmark",
            num_texts=len(texts),
            warmup_runs=warmup_runs,
        )

        # Warmup
        for i in range(min(warmup_runs, len(texts))):
            self.model.predict(texts[i])

        # Benchmark
        latencies = []
        start_time = time.time()

        for text in texts:
            req_start = time.time()
            self.model.predict(text)
            req_latency = (time.time() - req_start) * 1000
            latencies.append(req_latency)

        total_time = (time.time() - start_time) * 1000

        percentiles = self._calculate_percentiles(latencies)

        result = BenchmarkResult(
            method="single_predictions",
            total_requests=len(texts),
            total_time_ms=round(total_time, 2),
            avg_latency_ms=round(sum(latencies) / len(latencies), 2),
            min_latency_ms=round(min(latencies), 2),
            max_latency_ms=round(max(latencies), 2),
            throughput_rps=round(len(texts) / (total_time / 1000), 2),
            p50_latency_ms=round(percentiles["p50"], 2),
            p95_latency_ms=round(percentiles["p95"], 2),
            p99_latency_ms=round(percentiles["p99"], 2),
        )

        self.logger.info(
            "Single prediction benchmark complete",
            avg_latency_ms=result.avg_latency_ms,
            throughput_rps=result.throughput_rps,
        )

        return result

    def benchmark_batch_predictions(
        self,
        texts: List[str],
        batch_size: int = 32,
        warmup_runs: int = 1
    ) -> BenchmarkResult:
        """Benchmarks vectorized batch predictions.

        Args:
            texts: List of texts to use for benchmarking.
            batch_size: Size of batches for processing.
            warmup_runs: Number of warmup batches before measuring.

        Returns:
            BenchmarkResult containing performance metrics.
        """
        self.logger.info(
            "Starting batch prediction benchmark",
            num_texts=len(texts),
            batch_size=batch_size,
            warmup_runs=warmup_runs,
        )

        # Warmup
        for i in range(warmup_runs):
            warmup_batch = texts[:batch_size]
            self.model.predict_batch(warmup_batch)

        # Benchmark
        latencies = []
        start_time = time.time()

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            batch_start = time.time()
            results = self.model.predict_batch(batch)
            batch_time = (time.time() - batch_start) * 1000

            # Calculate per-request latency for this batch
            per_request_latency = batch_time / len(batch)
            latencies.extend([per_request_latency] * len(batch))

        total_time = (time.time() - start_time) * 1000

        percentiles = self._calculate_percentiles(latencies)

        result = BenchmarkResult(
            method=f"batch_predictions_{batch_size}",
            total_requests=len(texts),
            total_time_ms=round(total_time, 2),
            avg_latency_ms=round(sum(latencies) / len(latencies), 2),
            min_latency_ms=round(min(latencies), 2),
            max_latency_ms=round(max(latencies), 2),
            throughput_rps=round(len(texts) / (total_time / 1000), 2),
            p50_latency_ms=round(percentiles["p50"], 2),
            p95_latency_ms=round(percentiles["p95"], 2),
            p99_latency_ms=round(percentiles["p99"], 2),
        )

        self.logger.info(
            "Batch prediction benchmark complete",
            avg_latency_ms=result.avg_latency_ms,
            throughput_rps=result.throughput_rps,
            batch_size=batch_size,
        )

        return result

    async def benchmark_stream_processing(
        self,
        texts: List[str],
        batch_config: Optional[BatchConfig] = None,
        concurrency: int = 10
    ) -> BenchmarkResult:
        """Benchmarks stream processing with dynamic batching.

        Args:
            texts: List of texts to use for benchmarking.
            batch_config: Configuration for batch processing.
            concurrency: Number of concurrent requests to simulate.

        Returns:
            BenchmarkResult containing performance metrics.
        """
        self.logger.info(
            "Starting stream processing benchmark",
            num_texts=len(texts),
            concurrency=concurrency,
        )

        # Initialize stream processor
        config = batch_config or BatchConfig(
            max_batch_size=32,
            max_wait_time_ms=50.0,
            min_batch_size=1,
            dynamic_batching=True
        )

        processor = StreamProcessor(self.model, config)

        # Warmup
        await processor.predict_async(texts[0])

        # Benchmark
        latencies = []
        start_time = time.time()

        # Simulate concurrent requests
        async def process_text(text: str) -> float:
            req_start = time.time()
            await processor.predict_async(text)
            return (time.time() - req_start) * 1000

        # Process texts with controlled concurrency
        for i in range(0, len(texts), concurrency):
            batch_texts = texts[i:i + concurrency]
            tasks = [process_text(text) for text in batch_texts]
            batch_latencies = await asyncio.gather(*tasks)
            latencies.extend(batch_latencies)

        total_time = (time.time() - start_time) * 1000

        # Get processor stats
        stats = processor.get_stats()

        percentiles = self._calculate_percentiles(latencies)

        result = BenchmarkResult(
            method=f"stream_processing_c{concurrency}",
            total_requests=len(texts),
            total_time_ms=round(total_time, 2),
            avg_latency_ms=round(sum(latencies) / len(latencies), 2),
            min_latency_ms=round(min(latencies), 2),
            max_latency_ms=round(max(latencies), 2),
            throughput_rps=round(len(texts) / (total_time / 1000), 2),
            p50_latency_ms=round(percentiles["p50"], 2),
            p95_latency_ms=round(percentiles["p95"], 2),
            p99_latency_ms=round(percentiles["p99"], 2),
        )

        self.logger.info(
            "Stream processing benchmark complete",
            avg_latency_ms=result.avg_latency_ms,
            throughput_rps=result.throughput_rps,
            avg_batch_size=stats["avg_batch_size"],
            total_batches=stats["total_batches"],
        )

        # Cleanup
        await processor.shutdown()

        return result

    def compare_results(
        self,
        baseline: BenchmarkResult,
        optimized: BenchmarkResult
    ) -> ComparisonResult:
        """Compares two benchmark results.

        Args:
            baseline: Baseline benchmark result.
            optimized: Optimized benchmark result.

        Returns:
            ComparisonResult with improvement metrics.
        """
        latency_reduction = (
            (baseline.avg_latency_ms - optimized.avg_latency_ms) / baseline.avg_latency_ms * 100
        )

        throughput_improvement = (
            (optimized.throughput_rps - baseline.throughput_rps) / baseline.throughput_rps * 100
        )

        speedup = baseline.total_time_ms / optimized.total_time_ms

        comparison = ComparisonResult(
            baseline=baseline,
            optimized=optimized,
            latency_reduction_pct=round(latency_reduction, 2),
            throughput_improvement_pct=round(throughput_improvement, 2),
            speedup_factor=round(speedup, 2),
        )

        self.logger.info(
            "Performance comparison",
            latency_reduction_pct=comparison.latency_reduction_pct,
            throughput_improvement_pct=comparison.throughput_improvement_pct,
            speedup_factor=comparison.speedup_factor,
        )

        return comparison

    def print_results(self, result: BenchmarkResult) -> None:
        """Prints benchmark results in a formatted way.

        Args:
            result: The benchmark result to print.
        """
        print(f"\n{'='*60}")
        print(f"Benchmark Results: {result.method}")
        print(f"{'='*60}")
        print(f"Total Requests:      {result.total_requests}")
        print(f"Total Time:          {result.total_time_ms:.2f} ms")
        print(f"Throughput:          {result.throughput_rps:.2f} req/s")
        print(f"\nLatency Statistics:")
        print(f"  Average:           {result.avg_latency_ms:.2f} ms")
        print(f"  Min:               {result.min_latency_ms:.2f} ms")
        print(f"  Max:               {result.max_latency_ms:.2f} ms")
        print(f"  P50:               {result.p50_latency_ms:.2f} ms")
        print(f"  P95:               {result.p95_latency_ms:.2f} ms")
        print(f"  P99:               {result.p99_latency_ms:.2f} ms")
        print(f"{'='*60}\n")

    def print_comparison(self, comparison: ComparisonResult) -> None:
        """Prints comparison results in a formatted way.

        Args:
            comparison: The comparison result to print.
        """
        print(f"\n{'='*60}")
        print(f"Performance Comparison")
        print(f"{'='*60}")
        print(f"Baseline Method:     {comparison.baseline.method}")
        print(f"Optimized Method:    {comparison.optimized.method}")
        print(f"\nImprovements:")
        print(f"  Latency Reduction: {comparison.latency_reduction_pct:.2f}%")
        print(f"  ({comparison.baseline.avg_latency_ms:.2f}ms → {comparison.optimized.avg_latency_ms:.2f}ms)")
        print(f"\n  Throughput Gain:   {comparison.throughput_improvement_pct:.2f}%")
        print(f"  ({comparison.baseline.throughput_rps:.2f} → {comparison.optimized.throughput_rps:.2f} req/s)")
        print(f"\n  Speedup Factor:    {comparison.speedup_factor:.2f}x")
        print(f"{'='*60}\n")

