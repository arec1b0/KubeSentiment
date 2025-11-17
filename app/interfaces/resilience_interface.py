"""
Interface for Resilience Services

Defines contracts for circuit breaker and load balancing services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, TypeVar
from dataclasses import dataclass
from enum import Enum

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class InstanceLoad:
    """Instance load metrics"""

    cpu_percent: float
    memory_percent: float
    active_requests: int
    queue_size: int
    avg_response_time_ms: float
    error_rate: float

    def calculate_health_score(self) -> float:
        """Calculate weighted health score (0-100)

        Returns:
            Health score from 0-100, where 100 is optimal health
        """
        # Weighted scoring: lower is better for most metrics
        cpu_score = max(0, 100 - self.cpu_percent)
        memory_score = max(0, 100 - self.memory_percent)
        error_score = max(0, 100 - (self.error_rate * 100))
        response_time_score = max(0, 100 - min(self.avg_response_time_ms / 10, 100))

        # Weighted average
        return cpu_score * 0.3 + memory_score * 0.2 + error_score * 0.3 + response_time_score * 0.2


class ICircuitBreaker(ABC):
    """
    Interface for circuit breaker pattern implementation.

    Provides automatic failure detection and recovery.
    """

    @abstractmethod
    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            RuntimeError: If circuit is OPEN
            Exception: Any exception from func if circuit is CLOSED/HALF_OPEN
        """
        pass

    @abstractmethod
    def get_state(self) -> CircuitState:
        """
        Get current circuit state.

        Returns:
            Current circuit state (CLOSED, OPEN, or HALF_OPEN)
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Manually reset the circuit to CLOSED state.
        """
        pass


class ILoadMetrics(ABC):
    """
    Interface for load balancing and metrics tracking.

    Provides instance health monitoring and load shedding decisions.
    """

    @abstractmethod
    def get_instance_load(self) -> InstanceLoad:
        """
        Get current instance load metrics.

        Returns:
            InstanceLoad with current metrics
        """
        pass

    @abstractmethod
    def get_hpa_metrics(self) -> Dict[str, Any]:
        """
        Get Kubernetes HPA-compatible metrics.

        Returns:
            Dictionary with metrics for horizontal pod autoscaling
        """
        pass

    @abstractmethod
    def should_accept_request(self) -> bool:
        """
        Determine if instance should accept new requests (load shedding).

        Returns:
            True if request should be accepted, False to shed load
        """
        pass

    @abstractmethod
    def record_request_start(self) -> None:
        """
        Record the start of a request (increment active count).
        """
        pass

    @abstractmethod
    def record_request_end(self, success: bool, response_time_ms: float) -> None:
        """
        Record the completion of a request.

        Args:
            success: Whether request succeeded
            response_time_ms: Request duration in milliseconds
        """
        pass

    @abstractmethod
    def set_queue_size(self, size: int) -> None:
        """
        Update current queue size.

        Args:
            size: Current queue size
        """
        pass
