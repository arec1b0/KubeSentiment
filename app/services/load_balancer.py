"""
Load Balancing and Horizontal Scaling Support

This module provides utilities for horizontal scaling and load balancing
in distributed environments, including health reporting for autoscaling decisions.

Features:
- Health score calculation for load balancing
- Custom metrics for Horizontal Pod Autoscaler (HPA)
- Instance capacity tracking
- Load distribution recommendations
- Circuit breaker pattern for overload protection
"""

import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class InstanceLoad:
    """Represents the current load on a service instance."""

    instance_id: str
    pod_name: str
    timestamp: float = field(default_factory=time.time)
    active_requests: int = 0
    queue_size: int = 0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    error_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    health_score: float = 100.0

    def calculate_health_score(self) -> float:
        """
        Calculate overall health score (0-100).

        Lower score indicates higher load/worse health.
        This score can be used for load balancing decisions.
        """
        score = 100.0

        # Deduct based on active requests (assuming max capacity of 100 concurrent)
        max_concurrent = 100
        if self.active_requests > 0:
            score -= min(50, (self.active_requests / max_concurrent) * 50)

        # Deduct based on queue size (assuming max queue of 1000)
        max_queue = 1000
        if self.queue_size > 0:
            score -= min(20, (self.queue_size / max_queue) * 20)

        # Deduct based on CPU usage
        score -= min(15, (self.cpu_percent / 100) * 15)

        # Deduct based on memory usage
        score -= min(10, (self.memory_percent / 100) * 10)

        # Deduct based on error rate
        score -= min(25, self.error_rate * 25)

        # Deduct based on response time (assuming max acceptable is 1000ms)
        if self.avg_response_time_ms > 100:
            score -= min(10, ((self.avg_response_time_ms - 100) / 900) * 10)

        self.health_score = max(0.0, score)
        return self.health_score

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "instance_id": self.instance_id,
            "pod_name": self.pod_name,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "active_requests": self.active_requests,
            "queue_size": self.queue_size,
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_percent": round(self.memory_percent, 2),
            "error_rate": round(self.error_rate, 4),
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
            "health_score": round(self.health_score, 2),
        }


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for overload protection.

    States:
    - CLOSED: Normal operation, requests allowed
    - OPEN: Too many failures, requests blocked
    - HALF_OPEN: Testing if system recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to count as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"
        self._lock = threading.Lock()

        logger.info(
            "Circuit breaker initialized",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        return self._state

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        with self._lock:
            if self._state == "OPEN":
                # Check if we should try recovery
                if (
                    self._last_failure_time
                    and time.time() - self._last_failure_time > self.recovery_timeout
                ):
                    self._state = "HALF_OPEN"
                    logger.info("Circuit breaker entering HALF_OPEN state")
                else:
                    raise Exception("Circuit breaker is OPEN - rejecting request")

        try:
            result = func(*args, **kwargs)

            # Success - reset if in HALF_OPEN
            with self._lock:
                if self._state == "HALF_OPEN":
                    self._state = "CLOSED"
                    self._failure_count = 0
                    logger.info("Circuit breaker recovered - entering CLOSED state")

            return result

        except self.expected_exception as e:
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()

                if self._failure_count >= self.failure_threshold:
                    self._state = "OPEN"
                    logger.warning(
                        "Circuit breaker opened due to failures",
                        failure_count=self._failure_count,
                        threshold=self.failure_threshold,
                    )

            raise e

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = "CLOSED"
            self._failure_count = 0
            self._last_failure_time = None
            logger.info("Circuit breaker manually reset")

    def get_stats(self) -> Dict:
        """Get circuit breaker statistics."""
        return {
            "state": self._state,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
            "last_failure_datetime": (
                datetime.fromtimestamp(self._last_failure_time).isoformat()
                if self._last_failure_time
                else None
            ),
        }


class LoadBalancingMetrics:
    """
    Collects and provides metrics for load balancing and autoscaling decisions.

    This class tracks instance-level metrics that can be used by:
    - Kubernetes HPA for scaling decisions
    - Load balancers for traffic distribution
    - Monitoring systems for alerting
    """

    def __init__(self):
        """Initialize load balancing metrics."""
        self.settings = get_settings()
        self.logger = get_logger(__name__)

        # Instance identification
        self.pod_name = os.getenv("HOSTNAME", "unknown")
        self.instance_id = f"{self.pod_name}-{int(time.time())}"

        # Metrics tracking
        self._active_requests = 0
        self._queue_size = 0
        self._total_requests = 0
        self._total_errors = 0
        self._response_times: List[float] = []
        self._max_response_times = 1000  # Keep last 1000 response times

        # Thread safety
        self._lock = threading.Lock()

        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=10,
            recovery_timeout=30,
        )

        self.logger.info(
            "Load balancing metrics initialized",
            instance_id=self.instance_id,
            pod_name=self.pod_name,
        )

    def increment_active_requests(self) -> None:
        """Increment active request counter."""
        with self._lock:
            self._active_requests += 1
            self._total_requests += 1

    def decrement_active_requests(self) -> None:
        """Decrement active request counter."""
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)

    def set_queue_size(self, size: int) -> None:
        """Set current queue size."""
        with self._lock:
            self._queue_size = size

    def record_error(self) -> None:
        """Record an error occurrence."""
        with self._lock:
            self._total_errors += 1

    def record_response_time(self, time_ms: float) -> None:
        """
        Record a response time.

        Args:
            time_ms: Response time in milliseconds
        """
        with self._lock:
            self._response_times.append(time_ms)

            # Keep only recent response times
            if len(self._response_times) > self._max_response_times:
                self._response_times = self._response_times[-self._max_response_times :]

    def get_instance_load(self) -> InstanceLoad:
        """
        Get current instance load metrics.

        Returns:
            InstanceLoad object with current metrics
        """
        with self._lock:
            # Calculate error rate
            error_rate = (
                self._total_errors / self._total_requests
                if self._total_requests > 0
                else 0.0
            )

            # Calculate average response time
            avg_response_time = (
                sum(self._response_times) / len(self._response_times)
                if self._response_times
                else 0.0
            )

            # Get CPU and memory (would use psutil in production)
            cpu_percent = 0.0
            memory_percent = 0.0

            try:
                import psutil

                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
            except ImportError:
                # psutil not available - estimates based on other metrics
                # High load = high CPU/memory estimate
                if self._active_requests > 50:
                    cpu_percent = 70.0
                    memory_percent = 60.0
                elif self._active_requests > 20:
                    cpu_percent = 40.0
                    memory_percent = 35.0

            load = InstanceLoad(
                instance_id=self.instance_id,
                pod_name=self.pod_name,
                active_requests=self._active_requests,
                queue_size=self._queue_size,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                error_rate=error_rate,
                avg_response_time_ms=avg_response_time,
            )

            # Calculate health score
            load.calculate_health_score()

            return load

    def get_hpa_metrics(self) -> Dict:
        """
        Get metrics formatted for Kubernetes HPA.

        Returns:
            Dictionary with HPA-compatible metrics
        """
        load = self.get_instance_load()

        return {
            # Standard HPA metrics
            "cpu_utilization": load.cpu_percent,
            "memory_utilization": load.memory_percent,
            # Custom metrics for HPA
            "active_requests": load.active_requests,
            "queue_size": load.queue_size,
            "avg_response_time_ms": load.avg_response_time_ms,
            "error_rate": load.error_rate,
            "health_score": load.health_score,
            # Recommended scaling action
            "should_scale_up": load.health_score < 30,
            "should_scale_down": load.health_score > 90 and load.active_requests < 5,
        }

    def should_accept_request(self) -> Tuple[bool, str]:
        """
        Determine if instance should accept new requests.

        Returns:
            Tuple of (should_accept, reason)
        """
        load = self.get_instance_load()

        # Check circuit breaker
        if self.circuit_breaker.state == "OPEN":
            return False, "Circuit breaker is open"

        # Check if overloaded
        if load.active_requests > 100:
            return False, "Too many active requests"

        if load.queue_size > 1000:
            return False, "Queue is full"

        if load.health_score < 20:
            return False, "Instance health score too low"

        return True, "OK"

    def get_stats(self) -> Dict:
        """Get comprehensive statistics."""
        load = self.get_instance_load()

        return {
            "instance": load.to_dict(),
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "totals": {
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
            },
        }


# Global load balancing metrics instance
_load_metrics: Optional[LoadBalancingMetrics] = None


def get_load_metrics() -> LoadBalancingMetrics:
    """
    Get the global load balancing metrics instance.

    Returns:
        The global LoadBalancingMetrics instance
    """
    global _load_metrics
    if _load_metrics is None:
        _load_metrics = LoadBalancingMetrics()
    return _load_metrics


def reset_load_metrics() -> None:
    """Reset the global load balancing metrics instance."""
    global _load_metrics
    _load_metrics = None
