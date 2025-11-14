#!/usr/bin/env python3
"""A load testing script for measuring the performance of the model.

This script uses `asyncio` and `aiohttp` to send a high volume of concurrent
requests to the prediction endpoint. It simulates multiple users making
requests over a specified duration and collects detailed metrics on latency,
throughput, and error rates. The results are saved to a JSON file and a
graphical report is generated.
"""

import argparse
import asyncio
import json
import logging
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Represents the result of a single HTTP request.

    Attributes:
        timestamp: The time when the request was made.
        latency: The latency of the request in milliseconds.
        status_code: The HTTP status code of the response.
        success: A flag indicating if the request was successful.
        error: An error message, if any.
        response_size: The size of the response in bytes.
    """

    timestamp: float
    latency: float
    status_code: int
    success: bool
    error: Optional[str] = None
    response_size: int = 0


@dataclass
class BenchmarkMetrics:
    """Contains the aggregated metrics from a benchmark run.

    Attributes:
        instance_type: The type of instance that was benchmarked.
        concurrent_users: The number of concurrent users simulated.
        duration: The duration of the test in seconds.
        total_requests: The total number of requests made.
        successful_requests: The number of successful requests.
        failed_requests: The number of failed requests.
        requests_per_second: The average number of requests per second.
        avg_latency: The average request latency in milliseconds.
        p50_latency: The 50th percentile latency.
        p90_latency: The 90th percentile latency.
        p95_latency: The 95th percentile latency.
        p99_latency: The 99th percentile latency.
        min_latency: The minimum latency.
        max_latency: The maximum latency.
        error_rate: The percentage of failed requests.
        throughput: The number of successful requests per second.
        cpu_usage: The average CPU usage during the test.
        memory_usage: The average memory usage during the test.
        gpu_usage: The average GPU usage during the test, if applicable.
    """

    instance_type: str
    concurrent_users: int
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    avg_latency: float
    p50_latency: float
    p90_latency: float
    p95_latency: float
    p99_latency: float
    min_latency: float
    max_latency: float
    error_rate: float
    throughput: float
    cpu_usage: float
    memory_usage: float
    gpu_usage: Optional[float] = None


class LoadTester:
    """Handles the execution of the load test.

    This class manages the configuration, test data generation, request
    execution, and results analysis for the load test.

    Attributes:
        config: The configuration loaded from the YAML file.
        results: A list of `TestResult` objects.
        start_time: The start time of the test.
        end_time: The end time of the test.
    """

    def __init__(self, config_path: str):
        """Initializes the `LoadTester`.

        Args:
            config_path: The path to the benchmark configuration file.
        """
        self.config = self._load_config(config_path)
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Loads the YAML configuration file.

        Args:
            config_path: The path to the configuration file.

        Returns:
            A dictionary containing the configuration.
        """
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _generate_test_data(self) -> List[Dict[str, Any]]:
        """Generates a list of sample text data for the load test.

        Returns:
            A list of dictionaries, each representing a request payload.
        """
        test_texts = [
            "This product is simply magnificent! Very happy with the purchase.",
            "Terrible quality, a waste of money. I do not recommend.",
            "A normal product, nothing special, but worth the money.",
            "Excellent service and fast delivery!",
            "Complete disappointment, expected more from this brand.",
            "Excellent value for money.",
            "The product arrived damaged, very upset.",
            "I recommend it to everyone! The best purchase this year.",
            "Mediocre, there are better options for this price.",
            "A fantastic product, I will be ordering more!",
        ]

        samples_count = self.config["benchmark"]["test_data"]["samples_count"]
        test_data = []

        for i in range(samples_count):
            text = test_texts[i % len(test_texts)]
            test_data.append(
                {"text": text, "id": f"test_{i}", "timestamp": datetime.now().isoformat()}
            )

        return test_data

    async def _make_request(
        self, session: aiohttp.ClientSession, url: str, data: Dict[str, Any]
    ) -> TestResult:
        """Executes a single HTTP POST request.

        Args:
            session: The `aiohttp` client session.
            url: The URL of the endpoint to be tested.
            data: The JSON payload for the request.

        Returns:
            A `TestResult` object with the outcome of the request.
        """
        start_time = time.time()

        try:
            timeout = aiohttp.ClientTimeout(
                total=self.config["benchmark"]["load_test"]["request_timeout"]
            )

            async with session.post(url, json=data, timeout=timeout) as response:
                response_text = await response.text()
                end_time = time.time()

                return TestResult(
                    timestamp=start_time,
                    latency=(end_time - start_time) * 1000,  # in milliseconds
                    status_code=response.status,
                    success=response.status == 200,
                    response_size=len(response_text),
                )

        except Exception as e:
            end_time = time.time()
            return TestResult(
                timestamp=start_time,
                latency=(end_time - start_time) * 1000,
                status_code=0,
                success=False,
                error=str(e),
            )

    async def _user_simulation(
        self, user_id: int, url: str, test_data: List[Dict[str, Any]], duration: int
    ) -> List[TestResult]:
        """Simulates the behavior of a single concurrent user.

        This coroutine continuously sends requests to the endpoint for the
        specified duration, with a small delay between each request to mimic
        real-world user behavior.

        Args:
            user_id: The ID of the simulated user.
            url: The URL of the endpoint.
            test_data: The list of sample data to send.
            duration: The duration in seconds for the simulation.

        Returns:
            A list of `TestResult` objects from this user's simulation.
        """
        results = []
        end_time = time.time() + duration

        async with aiohttp.ClientSession() as session:
            request_count = 0

            while time.time() < end_time:
                # Select random test data
                data = test_data[request_count % len(test_data)]

                result = await self._make_request(session, url, data)
                results.append(result)

                request_count += 1

                # A small pause between requests (to simulate a real user)
                await asyncio.sleep(0.1)

        logger.info("User completed requests", extra={"user_id": user_id, "request_count": len(results)})
        return results

    async def run_load_test(
        self, instance_type: str, concurrent_users: int, duration: int, endpoint_url: str
    ) -> List[TestResult]:
        """Starts and manages the load test.

        This method creates and runs the user simulation tasks concurrently.

        Args:
            instance_type: The type of instance being tested.
            concurrent_users: The number of concurrent users to simulate.
            duration: The duration of the test in seconds.
            endpoint_url: The URL of the endpoint to be tested.

        Returns:
            A list containing all `TestResult` objects from the test.
        """
        logger.info(
            "Starting load test",
            extra={"concurrent_users": concurrent_users, "duration_seconds": duration}
        )

        test_data = self._generate_test_data()
        self.start_time = time.time()

        # Create tasks for all users
        tasks = []
        for user_id in range(concurrent_users):
            task = self._user_simulation(user_id, endpoint_url, test_data, duration)
            tasks.append(task)

        # Run all tasks in parallel
        user_results = await asyncio.gather(*tasks)

        # Combine the results of all users
        all_results = []
        for results in user_results:
            all_results.extend(results)

        self.end_time = time.time()
        self.results = all_results

        logger.info("Load test completed", extra={"total_requests": len(all_results)})
        return all_results

    def calculate_metrics(self, instance_type: str, concurrent_users: int) -> BenchmarkMetrics:
        """Calculates performance metrics from the raw test results.

        Args:
            instance_type: The type of instance that was tested.
            concurrent_users: The number of concurrent users simulated.

        Returns:
            A `BenchmarkMetrics` object with the aggregated results.

        Raises:
            ValueError: If no test results are available or if there were no
                successful requests.
        """
        if not self.results:
            raise ValueError("No test results available")

        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]

        latencies = [r.latency for r in successful_results]

        if not latencies:
            raise ValueError("No successful requests")

        duration = self.end_time - self.start_time

        metrics = BenchmarkMetrics(
            instance_type=instance_type,
            concurrent_users=concurrent_users,
            duration=duration,
            total_requests=len(self.results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            requests_per_second=len(self.results) / duration,
            avg_latency=statistics.mean(latencies),
            p50_latency=np.percentile(latencies, 50),
            p90_latency=np.percentile(latencies, 90),
            p95_latency=np.percentile(latencies, 95),
            p99_latency=np.percentile(latencies, 99),
            min_latency=min(latencies),
            max_latency=max(latencies),
            error_rate=(len(failed_results) / len(self.results)) * 100,
            throughput=len(successful_results) / duration,
            cpu_usage=0.0,  # To be filled in by monitoring
            memory_usage=0.0,  # To be filled in by monitoring
        )

        return metrics

    def save_results(self, metrics: BenchmarkMetrics, output_path: str):
        """Saves the benchmark results to JSON files.

        This method saves both the aggregated metrics and the detailed,
        per-request results.

        Args:
            metrics: The `BenchmarkMetrics` object to be saved.
            output_path: The path for the main results file.
        """
        # Create the directory if it does not exist
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Save metrics to JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(metrics), f, indent=2, ensure_ascii=False)

        # Save detailed results
        detailed_path = output_path.replace(".json", "_detailed.json")
        detailed_results = [asdict(r) for r in self.results]

        with open(detailed_path, "w", encoding="utf-8") as f:
            json.dump(detailed_results, f, indent=2, ensure_ascii=False)

        logger.info("Results saved", extra={"output_path": output_path})

    def generate_report(self, metrics: BenchmarkMetrics, output_dir: str):
        """Generates and saves a graphical report of the benchmark results.

        This method creates several plots to visualize the performance
        metrics, such as latency distribution and requests per second over
        time.

        Args:
            metrics: The `BenchmarkMetrics` from the test run.
            output_dir: The directory where the report image will be saved.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Latency plot
        plt.figure(figsize=(12, 8))

        # Latency histogram
        plt.subplot(2, 2, 1)
        latencies = [r.latency for r in self.results if r.success]
        plt.hist(latencies, bins=50, alpha=0.7, edgecolor="black")
        plt.xlabel("Latency (ms)")
        plt.ylabel("Frequency")
        plt.title("Latency Distribution")
        plt.grid(True, alpha=0.3)

        # RPS plot over time
        plt.subplot(2, 2, 2)
        timestamps = [r.timestamp for r in self.results]
        start_time = min(timestamps)
        time_buckets = {}

        for result in self.results:
            bucket = int((result.timestamp - start_time) // 10) * 10  # 10-second intervals
            if bucket not in time_buckets:
                time_buckets[bucket] = 0
            time_buckets[bucket] += 1

        times = sorted(time_buckets.keys())
        rps_values = [time_buckets[t] / 10 for t in times]  # RPS

        plt.plot(times, rps_values, marker="o")
        plt.xlabel("Time (seconds)")
        plt.ylabel("Requests per Second")
        plt.title("RPS Over Time")
        plt.grid(True, alpha=0.3)

        # Latency percentiles
        plt.subplot(2, 2, 3)
        percentiles = [50, 90, 95, 99]
        latency_percentiles = [np.percentile(latencies, p) for p in percentiles]

        plt.bar([f"P{p}" for p in percentiles], latency_percentiles)
        plt.xlabel("Percentile")
        plt.ylabel("Latency (ms)")
        plt.title("Latency Percentiles")
        plt.grid(True, alpha=0.3)

        # Status codes
        plt.subplot(2, 2, 4)
        status_codes = {}
        for result in self.results:
            code = result.status_code if result.status_code != 0 else "Error"
            status_codes[code] = status_codes.get(code, 0) + 1

        plt.pie(status_codes.values(), labels=status_codes.keys(), autopct="%1.1f%%")
        plt.title("Response Status Codes")

        plt.tight_layout()
        plt.savefig(
            output_dir
            / f"benchmark_report_{metrics.instance_type}_{metrics.concurrent_users}users.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

        logger.info("Report generated", extra={"output_dir": str(output_dir)})


async def main():
    """The main entry point for the load testing script."""
    parser = argparse.ArgumentParser(description="MLOps Sentiment Analysis Load Testing")
    parser.add_argument(
        "--config",
        default="configs/benchmark-config.yaml",
        help="Path to benchmark configuration file",
    )
    parser.add_argument(
        "--instance-type", required=True, help="Instance type to test (cpu-small, gpu-t4, etc.)"
    )
    parser.add_argument("--endpoint", required=True, help="API endpoint URL")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument(
        "--output", default="results/benchmark_results.json", help="Output file for results"
    )
    parser.add_argument(
        "--report-dir", default="results/reports", help="Directory for generated reports"
    )

    args = parser.parse_args()

    # Create the tester
    tester = LoadTester(args.config)

    try:
        # Start the load test
        results = await tester.run_load_test(
            instance_type=args.instance_type,
            concurrent_users=args.users,
            duration=args.duration,
            endpoint_url=args.endpoint,
        )

        # Calculate metrics
        metrics = tester.calculate_metrics(args.instance_type, args.users)

        # Print results
        print(f"\n{'='*60}")
        print(f"BENCHMARK RESULTS - {args.instance_type}")
        print(f"{'='*60}")
        print(f"Concurrent Users: {metrics.concurrent_users}")
        print(f"Duration: {metrics.duration:.2f}s")
        print(f"Total Requests: {metrics.total_requests}")
        print(f"Successful Requests: {metrics.successful_requests}")
        print(f"Failed Requests: {metrics.failed_requests}")
        print(f"Requests per Second: {metrics.requests_per_second:.2f}")
        print(f"Average Latency: {metrics.avg_latency:.2f}ms")
        print(f"P50 Latency: {metrics.p50_latency:.2f}ms")
        print(f"P95 Latency: {metrics.p95_latency:.2f}ms")
        print(f"P99 Latency: {metrics.p99_latency:.2f}ms")
        print(f"Error Rate: {metrics.error_rate:.2f}%")
        print(f"Throughput: {metrics.throughput:.2f} req/s")

        # Save results
        tester.save_results(metrics, args.output)

        # Generate report
        tester.generate_report(metrics, args.report_dir)

    except Exception as e:
        logger.error("Benchmark failed", extra={"error": str(e)}, exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
