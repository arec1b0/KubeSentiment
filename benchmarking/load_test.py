#!/usr/bin/env python3
"""
Realistic Load Testing Script for KubeSentiment
Simulates realistic traffic patterns with varying load profiles
"""

import asyncio
import time
import random
import statistics
from typing import List, Dict, Tuple
from dataclasses import dataclass
import aiohttp
import argparse
import json
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Configuration for load test"""
    base_url: str
    duration_seconds: int
    rps_target: int
    traffic_pattern: str  # constant, ramp, spike, wave
    num_workers: int
    timeout: int


@dataclass
class RequestResult:
    """Result of a single request"""
    success: bool
    latency_ms: float
    status_code: int
    timestamp: float
    error: str = None


class RealisticDataGenerator:
    """Generate realistic sentiment analysis test data"""

    # Realistic text samples across different sentiment categories
    POSITIVE_TEXTS = [
        "I absolutely love this product! It exceeded all my expectations.",
        "Amazing service! The team was incredibly helpful and professional.",
        "Best purchase I've made this year. Highly recommend to everyone!",
        "Wonderful experience from start to finish. Will definitely come back.",
        "Outstanding quality! Worth every penny and more.",
        "Fantastic! This has made my life so much easier.",
        "Brilliant work! Exactly what I was looking for.",
        "Exceptional customer support and great product quality.",
    ]

    NEGATIVE_TEXTS = [
        "Very disappointed with this purchase. Not worth the money.",
        "Terrible experience. Would not recommend to anyone.",
        "Poor quality and even worse customer service.",
        "Complete waste of time and money. Avoid at all costs.",
        "Horrible! Nothing worked as advertised.",
        "Worst purchase ever. Returning immediately.",
        "Awful experience from beginning to end.",
        "Completely unsatisfied. This is unacceptable.",
    ]

    NEUTRAL_TEXTS = [
        "The product arrived on time and matches the description.",
        "It works as expected. Nothing special, nothing terrible.",
        "Standard quality for the price point.",
        "Met basic expectations. Average overall.",
        "It does what it's supposed to do.",
        "Normal product, similar to competitors.",
        "Acceptable quality and delivery time.",
        "As described in the listing.",
    ]

    @classmethod
    def generate_text(cls) -> str:
        """Generate a random realistic text sample"""
        category = random.choices(
            [cls.POSITIVE_TEXTS, cls.NEGATIVE_TEXTS, cls.NEUTRAL_TEXTS],
            weights=[0.5, 0.3, 0.2],  # Weighted distribution
            k=1
        )[0]
        return random.choice(category)

    @classmethod
    def generate_batch(cls, size: int) -> List[str]:
        """Generate a batch of text samples"""
        return [cls.generate_text() for _ in range(size)]


class LoadTestClient:
    """Async HTTP client for load testing"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def predict_single(self, text: str) -> RequestResult:
        """Send single prediction request"""
        start_time = time.perf_counter()

        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/predict",
                json={"text": text}
            ) as response:
                await response.read()
                latency_ms = (time.perf_counter() - start_time) * 1000

                return RequestResult(
                    success=response.status == 200,
                    latency_ms=latency_ms,
                    status_code=response.status,
                    timestamp=time.time()
                )
        except asyncio.TimeoutError:
            return RequestResult(
                success=False,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                status_code=0,
                timestamp=time.time(),
                error="timeout"
            )
        except Exception as e:
            return RequestResult(
                success=False,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                status_code=0,
                timestamp=time.time(),
                error=str(e)
            )

    async def predict_batch(self, texts: List[str]) -> RequestResult:
        """Send batch prediction request"""
        start_time = time.perf_counter()

        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/batch/predict",
                json={"texts": texts}
            ) as response:
                data = await response.json()
                latency_ms = (time.perf_counter() - start_time) * 1000

                # For batch, might need to poll for results
                if response.status == 202:  # Accepted, async processing
                    job_id = data.get('job_id')
                    if job_id:
                        # Poll for completion
                        await self._poll_batch_completion(job_id, start_time)

                return RequestResult(
                    success=response.status in [200, 202],
                    latency_ms=latency_ms,
                    status_code=response.status,
                    timestamp=time.time()
                )
        except Exception as e:
            return RequestResult(
                success=False,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                status_code=0,
                timestamp=time.time(),
                error=str(e)
            )

    async def _poll_batch_completion(self, job_id: str, start_time: float, max_wait: int = 30):
        """Poll batch job for completion"""
        timeout = start_time + max_wait

        while time.perf_counter() < timeout:
            try:
                async with self.session.get(
                    f"{self.base_url}/api/v1/batch/status/{job_id}"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'completed':
                            return
            except:
                pass

            await asyncio.sleep(0.5)

    async def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except:
            return False


class TrafficPattern:
    """Generate traffic patterns for realistic load testing"""

    @staticmethod
    def constant(target_rps: int, duration: int) -> List[float]:
        """Constant RPS throughout test"""
        interval = 1.0 / target_rps if target_rps > 0 else 1.0
        return [i * interval for i in range(int(target_rps * duration))]

    @staticmethod
    def ramp(start_rps: int, end_rps: int, duration: int) -> List[float]:
        """Gradually increase RPS over time"""
        timestamps = []
        current_time = 0.0

        for second in range(duration):
            # Calculate RPS for this second
            progress = second / duration
            current_rps = start_rps + (end_rps - start_rps) * progress
            interval = 1.0 / current_rps if current_rps > 0 else 1.0

            # Generate requests for this second
            for _ in range(int(current_rps)):
                timestamps.append(current_time)
                current_time += interval

        return timestamps

    @staticmethod
    def spike(base_rps: int, spike_rps: int, duration: int, spike_interval: int = 60) -> List[float]:
        """Periodic traffic spikes"""
        timestamps = []
        current_time = 0.0

        for second in range(duration):
            # Determine if we're in a spike
            in_spike = (second % spike_interval) < 10  # 10 second spikes
            current_rps = spike_rps if in_spike else base_rps
            interval = 1.0 / current_rps if current_rps > 0 else 1.0

            for _ in range(int(current_rps)):
                timestamps.append(current_time)
                current_time += interval

        return timestamps

    @staticmethod
    def wave(min_rps: int, max_rps: int, duration: int, period: int = 120) -> List[float]:
        """Sinusoidal wave pattern"""
        import math
        timestamps = []
        current_time = 0.0

        for second in range(duration):
            # Calculate RPS using sine wave
            progress = (second % period) / period
            wave_value = math.sin(2 * math.pi * progress)
            current_rps = min_rps + (max_rps - min_rps) * (wave_value + 1) / 2
            interval = 1.0 / current_rps if current_rps > 0 else 1.0

            for _ in range(int(current_rps)):
                timestamps.append(current_time)
                current_time += interval

        return timestamps


class LoadTester:
    """Main load testing orchestrator"""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results: List[RequestResult] = []
        self.start_time = None

    async def run(self) -> Dict:
        """Execute load test"""
        logger.info(f"Starting load test: {self.config.traffic_pattern} pattern, "
                   f"{self.config.rps_target} RPS target, {self.config.duration_seconds}s duration")

        # Generate traffic pattern
        timestamps = self._generate_pattern()
        logger.info(f"Generated {len(timestamps)} requests")

        # Pre-flight health check
        async with LoadTestClient(self.config.base_url, self.config.timeout) as client:
            if not await client.health_check():
                logger.error("Service health check failed. Aborting test.")
                return {"error": "Service not healthy"}

        # Execute test
        self.start_time = time.time()

        async with LoadTestClient(self.config.base_url, self.config.timeout) as client:
            tasks = []

            for timestamp in timestamps:
                # Schedule task at specified timestamp
                task = asyncio.create_task(
                    self._send_request_at(client, timestamp)
                )
                tasks.append(task)

            # Wait for all requests to complete
            self.results = await asyncio.gather(*tasks)

        # Analyze results
        return self._analyze_results()

    def _generate_pattern(self) -> List[float]:
        """Generate request timestamps based on traffic pattern"""
        pattern_map = {
            'constant': lambda: TrafficPattern.constant(
                self.config.rps_target,
                self.config.duration_seconds
            ),
            'ramp': lambda: TrafficPattern.ramp(
                self.config.rps_target // 10,
                self.config.rps_target,
                self.config.duration_seconds
            ),
            'spike': lambda: TrafficPattern.spike(
                self.config.rps_target // 2,
                self.config.rps_target * 2,
                self.config.duration_seconds
            ),
            'wave': lambda: TrafficPattern.wave(
                self.config.rps_target // 2,
                self.config.rps_target * 2,
                self.config.duration_seconds
            ),
        }

        return pattern_map.get(self.config.traffic_pattern, pattern_map['constant'])()

    async def _send_request_at(self, client: LoadTestClient, scheduled_time: float) -> RequestResult:
        """Send request at scheduled time"""
        # Wait until scheduled time
        delay = scheduled_time - (time.time() - self.start_time)
        if delay > 0:
            await asyncio.sleep(delay)

        # Generate realistic data
        text = RealisticDataGenerator.generate_text()

        # Send request
        return await client.predict_single(text)

    def _analyze_results(self) -> Dict:
        """Analyze test results"""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        latencies = [r.latency_ms for r in successful]

        total_duration = time.time() - self.start_time
        actual_rps = len(self.results) / total_duration if total_duration > 0 else 0

        analysis = {
            "summary": {
                "total_requests": len(self.results),
                "successful_requests": len(successful),
                "failed_requests": len(failed),
                "success_rate": len(successful) / len(self.results) * 100 if self.results else 0,
                "test_duration_seconds": total_duration,
                "target_rps": self.config.rps_target,
                "actual_rps": actual_rps,
            },
            "latency": {
                "min_ms": min(latencies) if latencies else 0,
                "max_ms": max(latencies) if latencies else 0,
                "mean_ms": statistics.mean(latencies) if latencies else 0,
                "median_ms": statistics.median(latencies) if latencies else 0,
                "p95_ms": self._percentile(latencies, 95) if latencies else 0,
                "p99_ms": self._percentile(latencies, 99) if latencies else 0,
                "stddev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            },
            "errors": self._analyze_errors(failed),
        }

        return analysis

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    @staticmethod
    def _analyze_errors(failed: List[RequestResult]) -> Dict:
        """Analyze error types"""
        error_counts = {}
        status_counts = {}

        for result in failed:
            # Count errors
            error_type = result.error or "unknown"
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

            # Count status codes
            status_counts[result.status_code] = status_counts.get(result.status_code, 0) + 1

        return {
            "error_types": error_counts,
            "status_codes": status_counts,
        }


async def main():
    parser = argparse.ArgumentParser(description='Load test KubeSentiment service')
    parser.add_argument('--url', default='http://localhost:8000',
                       help='Base URL of the service')
    parser.add_argument('--duration', type=int, default=60,
                       help='Test duration in seconds')
    parser.add_argument('--rps', type=int, default=100,
                       help='Target requests per second')
    parser.add_argument('--pattern', choices=['constant', 'ramp', 'spike', 'wave'],
                       default='constant', help='Traffic pattern')
    parser.add_argument('--workers', type=int, default=10,
                       help='Number of concurrent workers')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds')
    parser.add_argument('--output', help='Output file for results (JSON)')

    args = parser.parse_args()

    config = LoadTestConfig(
        base_url=args.url,
        duration_seconds=args.duration,
        rps_target=args.rps,
        traffic_pattern=args.pattern,
        num_workers=args.workers,
        timeout=args.timeout,
    )

    # Run load test
    tester = LoadTester(config)
    results = await tester.run()

    # Print results
    print("\n" + "="*80)
    print("LOAD TEST RESULTS")
    print("="*80)
    print(json.dumps(results, indent=2))

    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                "config": {
                    "url": config.base_url,
                    "duration": config.duration_seconds,
                    "rps_target": config.rps_target,
                    "pattern": config.traffic_pattern,
                },
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }, f, indent=2)
        logger.info(f"Results saved to {args.output}")

    # Return exit code based on success
    if results.get("summary", {}).get("success_rate", 0) < 95:
        logger.warning("Success rate below 95%")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
