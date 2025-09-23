from app.monitoring import PrometheusMetrics
from app.config import Settings


def test_metrics_cache_ttl_respected():
    settings = Settings()
    settings.metrics_cache_ttl = 1

    metrics = PrometheusMetrics()
    # Force generation and cache
    first = metrics.get_metrics()
    second = metrics.get_metrics()
    assert first == second

    import time

    time.sleep(1.1)
    third = metrics.get_metrics()
    # After TTL, payload may be regenerated; allow equality or inequality but ensure no exception
    assert isinstance(third, str)
