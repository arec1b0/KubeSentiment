"""
Unit tests for load balancing and circuit breaker functionality.

Tests cover InstanceLoad health score calculation, CircuitBreaker state
transitions, and LoadBalancingMetrics collection.
"""

import pytest


import time
from unittest.mock import patch

import pytest

from app.services.load_balancer import (
    CircuitBreaker,
    CircuitState,
    InstanceLoad,
    LoadBalancingMetrics,
    get_load_metrics,
)


@pytest.mark.unit
class TestInstanceLoad:
    """Test InstanceLoad functionality."""

    def test_instance_load_creation(self):
        """Test InstanceLoad creation with default values."""
        load = InstanceLoad(instance_id="test_instance")
        assert load.instance_id == "test_instance"
        assert load.active_requests == 0
        assert load.queue_size == 0
        assert load.cpu_utilization == 0.0
        assert load.memory_utilization == 0.0
        assert load.response_time_ms == 0.0
        assert load.error_rate == 0.0

    def test_health_score_calculation_healthy(self):
        """Test health score calculation for healthy instance."""
        load = InstanceLoad(
            instance_id="test",
            active_requests=10,
            queue_size=5,
            cpu_utilization=30.0,
            memory_utilization=40.0,
            response_time_ms=100.0,
            error_rate=0.01,
        )
        score = load.calculate_health_score()
        assert 70.0 <= score <= 100.0  # Should be relatively healthy

    def test_health_score_calculation_unhealthy(self):
        """Test health score calculation for unhealthy instance."""
        load = InstanceLoad(
            instance_id="test",
            active_requests=150,
            queue_size=100,
            cpu_utilization=95.0,
            memory_utilization=98.0,
            response_time_ms=2000.0,
            error_rate=0.5,
        )
        score = load.calculate_health_score()
        assert 0.0 <= score < 30.0  # Should be unhealthy

    def test_health_score_boundaries(self):
        """Test health score stays within 0-100 range."""
        # Perfect health
        load = InstanceLoad(instance_id="test")
        score = load.calculate_health_score()
        assert score == 100.0

        # Maximum load
        load = InstanceLoad(
            instance_id="test",
            active_requests=1000,
            queue_size=1000,
            cpu_utilization=100.0,
            memory_utilization=100.0,
            response_time_ms=10000.0,
            error_rate=1.0,
        )
        score = load.calculate_health_score()
        assert 0.0 <= score <= 100.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        load = InstanceLoad(
            instance_id="test_instance",
            active_requests=5,
            cpu_utilization=50.0,
        )
        result = load.to_dict()
        assert isinstance(result, dict)
        assert result["instance_id"] == "test_instance"
        assert result["active_requests"] == 5
        assert result["cpu_utilization"] == 50.0
        assert "health_score" in result
        assert "timestamp" in result


@pytest.mark.unit
class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 10
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED
        assert cb.success_count == 0

    def test_circuit_breaker_closed_state_success(self):
        """Test circuit breaker in closed state with successful calls."""
        cb = CircuitBreaker(failure_threshold=3)

        def success_func():
            return "success"

        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_closed_state_failures(self):
        """Test circuit breaker opening after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)

        def failing_func():
            raise ValueError("Test error")

        # Fail multiple times
        for _ in range(3):
            try:
                cb.call(failing_func)
            except ValueError:
                pass

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    def test_circuit_breaker_open_state_blocks(self):
        """Test circuit breaker blocks calls when open."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        cb.state = CircuitState.OPEN
        cb.last_failure_time = time.time()

        def any_func():
            return "should not execute"

        with pytest.raises(RuntimeError, match="Circuit breaker is OPEN"):
            cb.call(any_func)

    def test_circuit_breaker_recovery_timeout(self):
        """Test circuit breaker recovery after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        cb.state = CircuitState.OPEN
        cb.last_failure_time = time.time() - 2  # 2 seconds ago

        def success_func():
            return "recovered"

        # Should transition to HALF_OPEN
        result = cb.call(success_func)
        assert result == "recovered"
        assert cb.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_half_open_success(self):
        """Test circuit breaker closing after successful recovery."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        cb.state = CircuitState.HALF_OPEN

        def success_func():
            return "success"

        # Need 2 successes to close
        cb.call(success_func)
        assert cb.state == CircuitState.HALF_OPEN
        cb.call(success_func)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_half_open_failure(self):
        """Test circuit breaker reopening after failure in half-open state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        cb.state = CircuitState.HALF_OPEN

        def failing_func():
            raise ValueError("Test error")

        try:
            cb.call(failing_func)
        except ValueError:
            pass

        assert cb.state == CircuitState.OPEN


@pytest.mark.unit
class TestLoadBalancingMetrics:
    """Test LoadBalancingMetrics functionality."""

    def test_load_balancing_metrics_initialization(self):
        """Test LoadBalancingMetrics initialization."""
        metrics = LoadBalancingMetrics()
        assert metrics.active_requests == 0
        assert metrics.queue_size == 0
        assert metrics.total_requests == 0
        assert metrics.failed_requests == 0
        assert len(metrics.response_times) == 0

    def test_get_instance_load(self):
        """Test getting instance load metrics."""
        metrics = LoadBalancingMetrics()
        metrics.active_requests = 10
        metrics.queue_size = 5
        metrics.total_requests = 100
        metrics.failed_requests = 5

        instance_load = metrics.get_instance_load()
        assert isinstance(instance_load, InstanceLoad)
        assert instance_load.active_requests == 10
        assert instance_load.queue_size == 5
        assert instance_load.error_rate == 0.05  # 5/100

    @patch("app.services.load_balancer.PSUTIL_AVAILABLE", True)
    @patch("app.services.load_balancer.psutil")
    def test_get_instance_load_with_psutil(self, mock_psutil):
        """Test getting instance load with psutil available."""
        mock_psutil.cpu_percent.return_value = 75.0
        mock_memory = type("obj", (object,), {"percent": 80.0})()
        mock_psutil.virtual_memory.return_value = mock_memory

        metrics = LoadBalancingMetrics()
        instance_load = metrics.get_instance_load()

        assert instance_load.cpu_utilization == 75.0
        assert instance_load.memory_utilization == 80.0

    def test_get_hpa_metrics(self):
        """Test getting HPA-formatted metrics."""
        metrics = LoadBalancingMetrics()
        metrics.active_requests = 20
        metrics.queue_size = 10

        hpa_metrics = metrics.get_hpa_metrics()
        assert isinstance(hpa_metrics, dict)
        assert "cpu_utilization" in hpa_metrics
        assert "memory_utilization" in hpa_metrics
        assert "request_rate" in hpa_metrics
        assert "active_requests" in hpa_metrics
        assert "queue_size" in hpa_metrics
        assert hpa_metrics["active_requests"] == 20.0
        assert hpa_metrics["queue_size"] == 10.0

    def test_should_accept_request_healthy(self):
        """Test request acceptance for healthy instance."""
        metrics = LoadBalancingMetrics()
        metrics.active_requests = 10
        metrics.queue_size = 5

        should_accept, reason = metrics.should_accept_request()
        assert should_accept is True
        assert "healthy" in reason.lower()

    def test_should_accept_request_unhealthy(self):
        """Test request rejection for unhealthy instance."""
        metrics = LoadBalancingMetrics()
        metrics.active_requests = 150  # Over limit
        metrics.queue_size = 5

        should_accept, reason = metrics.should_accept_request()
        assert should_accept is False
        assert "active requests" in reason.lower()

    def test_should_accept_request_high_cpu(self):
        """Test request rejection due to high CPU."""
        metrics = LoadBalancingMetrics()
        metrics.active_requests = 10

        # Mock high CPU utilization
        with patch.object(metrics, "get_instance_load") as mock_load:
            mock_load.return_value = InstanceLoad(
                instance_id="test",
                cpu_utilization=95.0,
                memory_utilization=50.0,
            )
            should_accept, reason = metrics.should_accept_request()
            assert should_accept is False
            assert "cpu" in reason.lower()

    def test_should_accept_request_high_memory(self):
        """Test request rejection due to high memory."""
        metrics = LoadBalancingMetrics()
        metrics.active_requests = 10

        # Mock high memory utilization
        with patch.object(metrics, "get_instance_load") as mock_load:
            mock_load.return_value = InstanceLoad(
                instance_id="test",
                cpu_utilization=50.0,
                memory_utilization=95.0,
            )
            should_accept, reason = metrics.should_accept_request()
            assert should_accept is False
            assert "memory" in reason.lower()

    def test_should_accept_request_low_health_score(self):
        """Test request rejection due to low health score."""
        metrics = LoadBalancingMetrics()

        # Mock low health score
        with patch.object(metrics, "get_instance_load") as mock_load:
            mock_load.return_value = InstanceLoad(
                instance_id="test",
                active_requests=200,
                queue_size=100,
                cpu_utilization=95.0,
                memory_utilization=95.0,
                response_time_ms=2000.0,
                error_rate=0.5,
            )
            should_accept, reason = metrics.should_accept_request()
            assert should_accept is False
            assert "health score" in reason.lower()

    def test_record_request_start(self):
        """Test recording request start."""
        metrics = LoadBalancingMetrics()
        assert metrics.active_requests == 0
        assert metrics.total_requests == 0

        metrics.record_request_start()
        assert metrics.active_requests == 1
        assert metrics.total_requests == 1

        metrics.record_request_start()
        assert metrics.active_requests == 2
        assert metrics.total_requests == 2

    def test_record_request_end_success(self):
        """Test recording successful request end."""
        metrics = LoadBalancingMetrics()
        metrics.active_requests = 5
        metrics.total_requests = 10
        metrics.failed_requests = 2

        metrics.record_request_end(success=True, response_time_ms=100.0)
        assert metrics.active_requests == 4
        assert metrics.total_requests == 10  # Unchanged
        assert metrics.failed_requests == 2  # Unchanged
        assert len(metrics.response_times) == 1
        assert metrics.response_times[0] == 100.0

    def test_record_request_end_failure(self):
        """Test recording failed request end."""
        metrics = LoadBalancingMetrics()
        metrics.active_requests = 5
        metrics.total_requests = 10
        metrics.failed_requests = 2

        metrics.record_request_end(success=False, response_time_ms=200.0)
        assert metrics.active_requests == 4
        assert metrics.failed_requests == 3
        assert len(metrics.response_times) == 1

    def test_record_request_end_response_time_limit(self):
        """Test response time list size limit."""
        metrics = LoadBalancingMetrics()
        metrics.max_response_times = 5

        # Add more than max
        for i in range(10):
            metrics.record_request_end(success=True, response_time_ms=float(i))

        assert len(metrics.response_times) == 5
        assert metrics.response_times[0] == 5.0  # Oldest removed

    def test_set_queue_size(self):
        """Test setting queue size."""
        metrics = LoadBalancingMetrics()
        assert metrics.queue_size == 0

        metrics.set_queue_size(10)
        assert metrics.queue_size == 10

        metrics.set_queue_size(-5)  # Should be clamped to 0
        assert metrics.queue_size == 0


@pytest.mark.unit
class TestSingleton:
    """Test singleton pattern for LoadBalancingMetrics."""

    def test_get_load_metrics_singleton(self):
        """Test that get_load_metrics returns singleton."""
        metrics1 = get_load_metrics()
        metrics2 = get_load_metrics()
        assert metrics1 is metrics2
