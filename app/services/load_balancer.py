"""
Load Balancing and Horizontal Scaling Support for Distributed Environments.

This module provides utilities for managing load and health in a distributed
system. It includes a `CircuitBreaker` for overload protection and a
`LoadBalancingMetrics` class for calculating instance health scores, which can
be used for autoscaling and intelligent load balancing decisions.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class InstanceLoad:
    """Represents the current load on a single service instance.

    This dataclass holds various metrics that describe the current load and
    health of a service instance, such as active requests, queue size, and
    CPU utilization. It also includes a method to calculate a unified health
    score.
    """

    instance_id: str
    active_requests: int = 0
    queue_size: int = 0
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    response_time_ms: float = 0.0
    error_rate: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def calculate_health_score(self) -> float:
        """Calculates an overall health score (0-100).

        A lower score indicates a higher load or poorer health. This score can
        be used by a load balancer to distribute traffic intelligently.

        Returns:
            Health score from 0 (unhealthy) to 100 (healthy).
        """
        # Weighted factors (lower is worse)
        # CPU utilization: 0-100%, weight 0.25
        cpu_penalty = self.cpu_utilization * 0.25

        # Memory utilization: 0-100%, weight 0.25
        memory_penalty = self.memory_utilization * 0.25

        # Active requests penalty: normalized to 0-25, weight 0.20
        # Assuming max 100 concurrent requests as baseline
        requests_penalty = min((self.active_requests / 100.0) * 25.0, 25.0) * 0.20

        # Queue size penalty: normalized to 0-15, weight 0.15
        # Assuming max 50 queue items as baseline
        queue_penalty = min((self.queue_size / 50.0) * 15.0, 15.0) * 0.15

        # Response time penalty: normalized to 0-10, weight 0.10
        # Assuming 1000ms as threshold
        response_penalty = min((self.response_time_ms / 1000.0) * 10.0, 10.0) * 0.10

        # Error rate penalty: 0-5, weight 0.05
        error_penalty = min(self.error_rate * 5.0, 5.0) * 0.05

        # Calculate total penalty
        total_penalty = (
            cpu_penalty
            + memory_penalty
            + requests_penalty
            + queue_penalty
            + response_penalty
            + error_penalty
        )

        # Health score is 100 minus penalty
        health_score = max(0.0, 100.0 - total_penalty)
        return round(health_score, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the instance load to a dictionary.

        Returns:
            Dictionary representation of instance load metrics.
        """
        return {
            "instance_id": self.instance_id,
            "active_requests": self.active_requests,
            "queue_size": self.queue_size,
            "cpu_utilization": self.cpu_utilization,
            "memory_utilization": self.memory_utilization,
            "response_time_ms": self.response_time_ms,
            "error_rate": self.error_rate,
            "health_score": self.calculate_health_score(),
            "timestamp": self.timestamp,
        }


class CircuitBreaker:
    """An implementation of the circuit breaker pattern for overload protection.

    This class provides a simple and effective way to prevent a service from
    being overwhelmed by repeated failures. It monitors for failures and, once
    a threshold is reached, "opens" the circuit to block further requests for a
    period of time, allowing the system to recover.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """Initializes the circuit breaker.

        Args:
            failure_threshold: The number of failures before opening the circuit.
            recovery_timeout: The time in seconds to wait before attempting recovery.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.success_count = 0  # For half-open state

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Executes a function with circuit breaker protection.

        Args:
            func: The function to execute.
            *args, **kwargs: Arguments for the function.

        Returns:
            The result of the function if successful.

        Raises:
            RuntimeError: If the circuit is open.
            Exception: If the function fails.
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time >= self.recovery_timeout
            ):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise RuntimeError(
                    f"Circuit breaker is OPEN. "
                    f"Last failure: {self.last_failure_time}. "
                    f"Recovery timeout: {self.recovery_timeout}s"
                )

        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handles successful function execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            # If we get a few successes, close the circuit
            if self.success_count >= 2:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker CLOSED after successful recovery")
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handles failed function execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failed in half-open, go back to open
            self.state = CircuitState.OPEN
            self.success_count = 0
            logger.warning("Circuit breaker OPENED after failure in HALF_OPEN state")
        elif (
            self.state == CircuitState.CLOSED
            and self.failure_count >= self.failure_threshold
        ):
            # Too many failures, open the circuit
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPENED after {self.failure_count} failures"
            )


class LoadBalancingMetrics:
    """Collects and provides metrics for load balancing and autoscaling.

    This class tracks instance-level metrics that can be used by a Kubernetes
    Horizontal Pod Autoscaler (HPA) or an external load balancer to make
    intelligent scaling and traffic distribution decisions.
    """

    def __init__(self):
        """Initializes the load balancing metrics collector."""
        self.instance_id = f"instance_{int(time.time())}"
        self.active_requests = 0
        self.queue_size = 0
        self.total_requests = 0
        self.failed_requests = 0
        self.response_times: list[float] = []
        self.max_response_times = 1000  # Keep last 1000 response times
        self._lock = False  # Simple lock flag for thread safety

    def get_instance_load(self) -> InstanceLoad:
        """Returns the current load metrics for the instance.

        Returns:
            An `InstanceLoad` object with the current metrics.
        """
        # Get CPU and memory utilization
        cpu_utilization = 0.0
        memory_utilization = 0.0

        if PSUTIL_AVAILABLE:
            try:
                cpu_utilization = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                memory_utilization = memory.percent
            except Exception as e:
                logger.warning(f"Failed to get system metrics: {e}")

        # Calculate average response time
        avg_response_time = 0.0
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)

        # Calculate error rate
        error_rate = 0.0
        if self.total_requests > 0:
            error_rate = self.failed_requests / self.total_requests

        return InstanceLoad(
            instance_id=self.instance_id,
            active_requests=self.active_requests,
            queue_size=self.queue_size,
            cpu_utilization=cpu_utilization,
            memory_utilization=memory_utilization,
            response_time_ms=avg_response_time,
            error_rate=error_rate,
        )

    def get_hpa_metrics(self) -> Dict[str, float]:
        """Returns metrics formatted for use by a Kubernetes HPA.

        Returns:
            A dictionary of HPA-compatible metrics.
        """
        instance_load = self.get_instance_load()

        # Calculate request rate (requests per second)
        # This is a simplified calculation - in production, you'd track this over time
        request_rate = max(0.0, self.active_requests / 10.0)  # Simplified metric

        return {
            "cpu_utilization": instance_load.cpu_utilization,
            "memory_utilization": instance_load.memory_utilization,
            "request_rate": request_rate,
            "active_requests": float(self.active_requests),
            "queue_size": float(self.queue_size),
        }

    def should_accept_request(self) -> Tuple[bool, str]:
        """Determines if the instance should accept new requests.

        This can be used for load shedding or to signal to a load balancer that
        the instance is overloaded.

        Returns:
            A tuple containing a boolean and a reason string.
        """
        instance_load = self.get_instance_load()
        health_score = instance_load.calculate_health_score()

        # Reject if health score is too low
        if health_score < 20.0:
            return False, f"Health score too low: {health_score:.2f}"

        # Reject if CPU is too high
        if instance_load.cpu_utilization > 90.0:
            return False, f"CPU utilization too high: {instance_load.cpu_utilization:.2f}%"

        # Reject if memory is too high
        if instance_load.memory_utilization > 90.0:
            return False, f"Memory utilization too high: {instance_load.memory_utilization:.2f}%"

        # Reject if too many active requests
        if self.active_requests > 100:
            return False, f"Too many active requests: {self.active_requests}"

        # Reject if queue is too large
        if self.queue_size > 50:
            return False, f"Queue size too large: {self.queue_size}"

        return True, "Instance is healthy and can accept requests"

    def record_request_start(self) -> None:
        """Records the start of a request."""
        self.active_requests += 1
        self.total_requests += 1

    def record_request_end(self, success: bool = True, response_time_ms: float = 0.0) -> None:
        """Records the end of a request.

        Args:
            success: Whether the request was successful.
            response_time_ms: Response time in milliseconds.
        """
        self.active_requests = max(0, self.active_requests - 1)
        if not success:
            self.failed_requests += 1

        if response_time_ms > 0:
            self.response_times.append(response_time_ms)
            # Keep only last N response times
            if len(self.response_times) > self.max_response_times:
                self.response_times.pop(0)

    def set_queue_size(self, size: int) -> None:
        """Sets the current queue size.

        Args:
            size: Current queue size.
        """
        self.queue_size = max(0, size)


_load_metrics: Optional[LoadBalancingMetrics] = None


def get_load_metrics() -> LoadBalancingMetrics:
    """Provides a singleton instance of the `LoadBalancingMetrics` class.

    Returns:
        The singleton `LoadBalancingMetrics` instance.
    """
    global _load_metrics
    if _load_metrics is None:
        _load_metrics = LoadBalancingMetrics()
    return _load_metrics
