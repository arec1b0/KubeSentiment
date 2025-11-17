"""Unit tests for the Prometheus metrics caching functionality.

This module contains test cases to verify that the caching mechanism for
Prometheus metrics respects the configured Time-To-Live (TTL).
"""

import pytest

from app.core.config import Settings
from app.monitoring.prometheus import PrometheusMetrics


@pytest.mark.unit
def test_metrics_cache_ttl_respected():
    """Tests that the Prometheus metrics cache expires after the configured TTL.

    This test verifies that:
    1.  The first two calls within the TTL return the exact same cached response.
    2.  A third call after the TTL has expired returns a new response,
        confirming that the cache was invalidated and the metrics were regenerated.
    """
    settings = Settings()
    settings.metrics_cache_ttl = 1  # Set a short TTL of 1 second for the test

    metrics = PrometheusMetrics(settings=settings)
    # Force generation and cache the first response
    first_response = metrics.get_metrics()
    # This should hit the cache
    second_response = metrics.get_metrics()

    # The first and second responses should be the exact same object from the cache
    assert first_response is second_response

    import time

    # Wait for the TTL to expire
    time.sleep(1.1)
    # This should generate a new response as the cache is now stale
    third_response = metrics.get_metrics()

    # After the TTL, the new response should be different from the first one
    assert third_response is not first_response
    assert isinstance(third_response, str)
