"""
Performance benchmarking utilities for measuring optimization improvements.

This module provides a comprehensive suite of tools to benchmark and compare
the performance of different prediction strategies, including single, batch,
and stream processing. It is designed to demonstrate the significant latency
reduction and throughput gains achieved through vectorization and dynamic
batching.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.models.base import ModelStrategy
from app.models.stream_models import BatchConfig
from app.services.stream_processor import StreamProcessor

logger = get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Represents the results from a single benchmark run.

    This data class stores a comprehensive set of performance metrics
    captured during a benchmark test, providing a detailed snapshot of
    the system's performance under a specific load.

    Attributes:
        method: The name of the method or strategy being benchmarked.
        total_requests: The total number of requests processed.
        total_time_ms: The total time taken for the benchmark in milliseconds.
        avg_latency_ms: The average latency per request in milliseconds.
        min_latency_ms: The minimum latency observed for a single request.
        max_latency_ms: The maximum latency observed for a single request.
        throughput_rps: The overall throughput in requests per second.
        p50_latency_ms: The 50th percentile (median) latency.
        p95_latency_ms: The 95th percentile latency.
        p99_latency_ms: The 99th percentile latency.
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
    """Represents the comparison of two benchmark results.

    This data class is used to quantify the performance difference between a
    baseline and an optimized method, highlighting improvements in latency,
    throughput, and overall speed.

    Attributes:
        baseline: The BenchmarkResult for the baseline method.
        optimized: The BenchmarkResult for the optimized method.
        latency_reduction_pct: The percentage reduction in average latency from
                               baseline to optimized.
        throughput_improvement_pct: The percentage improvement in throughput from
                                    baseline to optimized.
        speedup_factor: The factor by which the optimized method is faster
                        (e.g., 2.5x speedup).
    """

    baseline: BenchmarkResult
    optimized: BenchmarkResult
    latency_reduction_pct: float
    throughput_improvement_pct: float
    speedup_factor: float


class PerformanceBenchmark:
    """A class for benchmarking prediction performance.

    This class provides a suite of methods to conduct comprehensive performance
    benchmarks on different prediction strategies, such as single predictions,
    batch processing, and asynchronous stream processing. It is designed to
    help quantify the benefits of optimization techniques.

    Attributes:
        model: The model strategy to be benchmarked.
    """

    def __init__(self, model: ModelStrategy):
        """Initializes the PerformanceBenchmark.

        Args:
            model: An instance of a model strategy (e.g., ONNX, scikit-learn)
                   that will be used for making predictions.
        """
        self.model = model
        self.logger = get_logger(__name__)

    def _calculate_percentiles(self, latencies: List[float]) -> Dict[str, float]:
        """Calculates the 50th, 95th, and 99th percentiles for a list of latencies.

        Args:
            latencies: A list of latency measurements in milliseconds.

        Returns:
            A dictionary containing the p50, p95, and p99 latency values.
        """
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        if n == 0:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        return {
            "p50": sorted_latencies[int(n * 0.50)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)],
        }

    def benchmark_single_predictions(
        self, texts: List[str], warmup_runs: int = 5
    ) -> BenchmarkResult:
        """Benchmarks the performance of sequential, single predictions.

        Args:
            texts: A list of texts to use for the benchmark.
            warmup_runs: The number of initial predictions to make before starting
                         the measurement, to account for model loading and caching.

        Returns:
            A BenchmarkResult object containing the performance metrics.
        """
        self.logger.info(
            "Starting single prediction benchmark", num_texts=len(texts), warmup_runs=warmup_runs
        )
        for i in range(min(warmup_runs, len(texts))):
            self.model.predict(texts[i])

        latencies = []
        start_time = time.time()
        for text in texts:
            req_start = time.time()
            self.model.predict(text)
            latencies.append((time.time() - req_start) * 1000)
        total_time = (time.time() - start_time) * 1000

        percentiles = self._calculate_percentiles(latencies)
        result = BenchmarkResult(
            method="single_predictions",
            total_requests=len(texts),
            total_time_ms=round(total_time, 2),
            avg_latency_ms=round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            min_latency_ms=round(min(latencies), 2) if latencies else 0.0,
            max_latency_ms=round(max(latencies), 2) if latencies else 0.0,
            throughput_rps=round(len(texts) / (total_time / 1000), 2)
            if total_time > 0
            else float("inf"),
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
        self, texts: List[str], batch_size: int = 32, warmup_runs: int = 1
    ) -> BenchmarkResult:
        """Benchmarks the performance of vectorized batch predictions.

        Args:
            texts: A list of texts to use for the benchmark.
            batch_size: The number of texts to include in each batch.
            warmup_runs: The number of warmup batches to process before measurement.

        Returns:
            A BenchmarkResult object containing the performance metrics.
        """
        self.logger.info(
            "Starting batch prediction benchmark",
            num_texts=len(texts),
            batch_size=batch_size,
            warmup_runs=warmup_runs,
        )
        for _ in range(warmup_runs):
            self.model.predict_batch(texts[:batch_size])

        latencies = []
        start_time = time.time()
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_start = time.time()
            self.model.predict_batch(batch)
            batch_time = (time.time() - batch_start) * 1000
            per_request_latency = batch_time / len(batch)
            latencies.extend([per_request_latency] * len(batch))
        total_time = (time.time() - start_time) * 1000

        percentiles = self._calculate_percentiles(latencies)
        result = BenchmarkResult(
            method=f"batch_predictions_{batch_size}",
            total_requests=len(texts),
            total_time_ms=round(total_time, 2),
            avg_latency_ms=round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            min_latency_ms=round(min(latencies), 2) if latencies else 0.0,
            max_latency_ms=round(max(latencies), 2) if latencies else 0.0,
            throughput_rps=round(len(texts) / (total_time / 1000), 2)
            if total_time > 0
            else float("inf"),
            p50_latency_ms=round(percentiles["p50"], 2),
            p95_latency_ms=round(percentiles["p95"], 2),
            p99_latency_ms=round(percentiles["p99"], 2),
        )
        self.logger.info(
            "Batch prediction benchmark complete",
            avg_latency_ms=result.avg_latency_ms,
            throughput_rps=result.throughput_rps,
        )
        return result

    async def benchmark_stream_processing(
        self, texts: List[str], batch_config: Optional[BatchConfig] = None, concurrency: int = 10
    ) -> BenchmarkResult:
        """Benchmarks the stream processor with dynamic batching under concurrent load.

        Args:
            texts: A list of texts to use for the benchmark.
            batch_config: An optional configuration for the stream processor's batching behavior.
            concurrency: The number of concurrent requests to simulate.

        Returns:
            A BenchmarkResult object containing the performance metrics.
        """
        self.logger.info(
            "Starting stream processing benchmark", num_texts=len(texts), concurrency=concurrency
        )
        config = batch_config or BatchConfig()
        processor = StreamProcessor(self.model, config)
        await processor.predict_async(texts[0])

        latencies = []
        start_time = time.time()

        async def process_text(text: str) -> float:
            req_start = time.time()
            await processor.predict_async(text)
            return (time.time() - req_start) * 1000

        for i in range(0, len(texts), concurrency):
            batch_texts = texts[i : i + concurrency]
            tasks = [process_text(text) for text in batch_texts]
            latencies.extend(await asyncio.gather(*tasks))
        total_time = (time.time() - start_time) * 1000

        processor.get_stats()
        percentiles = self._calculate_percentiles(latencies)
        result = BenchmarkResult(
            method=f"stream_processing_c{concurrency}",
            total_requests=len(texts),
            total_time_ms=round(total_time, 2),
            avg_latency_ms=round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            min_latency_ms=round(min(latencies), 2) if latencies else 0.0,
            max_latency_ms=round(max(latencies), 2) if latencies else 0.0,
            throughput_rps=round(len(texts) / (total_time / 1000), 2)
            if total_time > 0
            else float("inf"),
            p50_latency_ms=round(percentiles["p50"], 2),
            p95_latency_ms=round(percentiles["p95"], 2),
            p99_latency_ms=round(percentiles["p99"], 2),
        )
        self.logger.info(
            "Stream processing benchmark complete",
            avg_latency_ms=result.avg_latency_ms,
            throughput_rps=result.throughput_rps,
        )
        await processor.shutdown()
        return result

    def compare_results(
        self, baseline: BenchmarkResult, optimized: BenchmarkResult
    ) -> ComparisonResult:
        """Compares two benchmark results and calculates improvement metrics.

        Args:
            baseline: The BenchmarkResult of the baseline method.
            optimized: The BenchmarkResult of the optimized method.

        Returns:
            A ComparisonResult object with the calculated improvement metrics.
        """
        latency_reduction = (
            (baseline.avg_latency_ms - optimized.avg_latency_ms) / baseline.avg_latency_ms * 100
            if baseline.avg_latency_ms > 0
            else 0.0
        )
        throughput_improvement = (
            (optimized.throughput_rps - baseline.throughput_rps) / baseline.throughput_rps * 100
            if baseline.throughput_rps > 0
            else float("inf")
        )
        speedup = (
            baseline.total_time_ms / optimized.total_time_ms
            if optimized.total_time_ms > 0
            else float("inf")
        )
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
        )
        return comparison

    def print_results(self, result: BenchmarkResult) -> None:
        """Prints the benchmark results in a formatted and readable table.

        Args:
            result: The BenchmarkResult object to be printed.
        """
        print(f"\n{'='*60}\nBenchmark Results: {result.method}\n{'='*60}")
        print(f"{'Total Requests:':<20} {result.total_requests}")
        print(f"{'Total Time:':<20} {result.total_time_ms:.2f} ms")
        print(f"{'Throughput:':<20} {result.throughput_rps:.2f} req/s")
        print("\nLatency Statistics:")
        print(f"  {'Average:':<15} {result.avg_latency_ms:.2f} ms")
        print(f"  {'Min:':<15} {result.min_latency_ms:.2f} ms")
        print(f"  {'Max:':<15} {result.max_latency_ms:.2f} ms")
        print(f"  {'P50:':<15} {result.p50_latency_ms:.2f} ms")
        print(f"  {'P95:':<15} {result.p95_latency_ms:.2f} ms")
        print(f"  {'P99:':<15} {result.p99_latency_ms:.2f} ms")
        print(f"{'='*60}\n")

    def print_comparison(self, comparison: ComparisonResult) -> None:
        """Prints the comparison results in a formatted and readable table.

        Args:
            comparison: The ComparisonResult object to be printed.
        """
        print(f"\n{'='*60}\nPerformance Comparison\n{'='*60}")
        print(f"{'Baseline Method:':<20} {comparison.baseline.method}")
        print(f"{'Optimized Method:':<20} {comparison.optimized.method}")
        print("\nImprovements:")
        print(f"  {'Latency Reduction:':<20} {comparison.latency_reduction_pct:.2f}%")
        print(
            f"  ({comparison.baseline.avg_latency_ms:.2f}ms → {comparison.optimized.avg_latency_ms:.2f}ms)"
        )
        print(f"\n  {'Throughput Gain:':<20} {comparison.throughput_improvement_pct:.2f}%")
        print(
            f"  ({comparison.baseline.throughput_rps:.2f} → {comparison.optimized.throughput_rps:.2f} req/s)"
        )
        print(f"\n  {'Speedup Factor:':<20} {comparison.speedup_factor:.2f}x")
        print(f"{'='*60}\n")
