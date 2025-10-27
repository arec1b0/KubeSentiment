"""
Load Balancing and Horizontal Scaling Support for Distributed Environments.

This module provides utilities for managing load and health in a distributed
system. It includes a `CircuitBreaker` for overload protection and a
`LoadBalancingMetrics` class for calculating instance health scores, which can
be used for autoscaling and intelligent load balancing decisions.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger(__name__)


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
    ...

    def calculate_health_score(self) -> float:
        """Calculates an overall health score (0-100).

        A lower score indicates a higher load or poorer health. This score can
        be used by a load balancer to distribute traffic intelligently.
        """
        ...

    def to_dict(self) -> Dict:
        """Converts the instance load to a dictionary."""
        ...


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
        ...

    def call(self, func, *args, **kwargs):
        """Executes a function with circuit breaker protection.

        Args:
            func: The function to execute.
            *args, **kwargs: Arguments for the function.

        Returns:
            The result of the function if successful.

        Raises:
            Exception: If the circuit is open or if the function fails.
        """
        ...


class LoadBalancingMetrics:
    """Collects and provides metrics for load balancing and autoscaling.

    This class tracks instance-level metrics that can be used by a Kubernetes
    Horizontal Pod Autoscaler (HPA) or an external load balancer to make
    intelligent scaling and traffic distribution decisions.
    """

    def __init__(self):
        """Initializes the load balancing metrics collector."""
        ...

    def get_instance_load(self) -> InstanceLoad:
        """Returns the current load metrics for the instance.

        Returns:
            An `InstanceLoad` object with the current metrics.
        """
        ...

    def get_hpa_metrics(self) -> Dict:
        """Returns metrics formatted for use by a Kubernetes HPA.

        Returns:
            A dictionary of HPA-compatible metrics.
        """
        ...

    def should_accept_request(self) -> Tuple[bool, str]:
        """Determines if the instance should accept new requests.

        This can be used for load shedding or to signal to a load balancer that
        the instance is overloaded.

        Returns:
            A tuple containing a boolean and a reason string.
        """
        ...


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
