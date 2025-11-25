"""
Redis-based Distributed Caching System for the MLOps sentiment analysis service.

This module provides a high-performance, distributed caching layer using Redis.
It is designed to cache various types of data, such as prediction results and
feature vectors, to improve performance and reduce latency across multiple
service instances.
"""

import pickle
import time
from contextlib import contextmanager
from typing import Any, Optional

import redis
from redis.connection import ConnectionPool
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.interfaces.cache_interface import ICacheClient
from app.monitoring.prometheus import (
    record_redis_cache_error,
    record_redis_cache_hit,
    record_redis_cache_miss,
    record_redis_operation_duration,
)

logger = get_logger(__name__)


class RedisCacheClient(ICacheClient):
    """A high-performance Redis cache client with connection pooling and retries.

    This client provides a robust interface for interacting with a Redis
    server. It includes features like connection pooling for efficient
    resource management, automatic retries for transient network errors, and
    comprehensive monitoring of cache performance.
    """

    def __init__(self, **kwargs):
        """Initializes the Redis cache client.

        Args:
            **kwargs: Configuration options for the Redis connection pool.
        """
        self.pool = ConnectionPool(**kwargs)
        self.client = redis.Redis(connection_pool=self.pool)
        self.namespace = kwargs.get("namespace", "kubesentiment")
        self._test_connection()

    def _test_connection(self):
        """Tests the connection to the Redis server on initialization."""
        try:
            self.client.ping()
            logger.info("Redis connection successful")
        except RedisError as e:
            logger.error("Redis connection failed", error=str(e))
            raise

    def _make_key(self, key: str, cache_type: str) -> str:
        """Creates a namespaced cache key.

        Args:
            key: The original key.
            cache_type: The type of cache (e.g., 'prediction').

        Returns:
            The namespaced key.
        """
        return f"{self.namespace}:{cache_type}:{key}"

    @contextmanager
    def _measure_operation(self, operation: str):
        """A context manager to measure the duration of a Redis operation."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            record_redis_operation_duration(operation, duration)

    def get(self, key: str, cache_type: str = "prediction") -> Optional[Any]:
        """Retrieves a value from the cache.

        Args:
            key: The cache key.
            cache_type: The type of cache.

        Returns:
            The cached value if found, `None` otherwise.
        """
        namespaced_key = self._make_key(key, cache_type)
        try:
            with self._measure_operation("get"):
                value = self.client.get(namespaced_key)
            if value:
                record_redis_cache_hit(cache_type)
                return pickle.loads(value)
            record_redis_cache_miss(cache_type)
            return None
        except RedisError as e:
            record_redis_cache_error("get", type(e).__name__)
            logger.error("Redis GET failed", key=key, error=str(e))
            return None

    def set(
        self, key: str, value: Any, cache_type: str = "prediction", ttl: Optional[int] = None
    ) -> bool:
        """Sets a value in the cache with an optional TTL.

        Args:
            key: The cache key.
            value: The value to cache.
            cache_type: The type of cache.
            ttl: The time-to-live in seconds.

        Returns:
            `True` if the value was set successfully, `False` otherwise.
        """
        namespaced_key = self._make_key(key, cache_type)
        try:
            serialized_value = pickle.dumps(value)
            with self._measure_operation("set"):
                self.client.set(namespaced_key, serialized_value, ex=ttl)
            return True
        except RedisError as e:
            record_redis_cache_error("set", type(e).__name__)
            logger.error("Redis SET failed", key=key, error=str(e))
            return False

    def delete(self, key: str, cache_type: str = "prediction") -> bool:
        """Deletes a value from the cache.

        Args:
            key: The cache key.
            cache_type: The type of cache.

        Returns:
            `True` if the key was deleted, `False` otherwise.
        """
        namespaced_key = self._make_key(key, cache_type)
        try:
            with self._measure_operation("delete"):
                return self.client.delete(namespaced_key) > 0
        except RedisError as e:
            record_redis_cache_error("delete", type(e).__name__)
            logger.error("Redis DELETE failed", key=key, error=str(e))
            return False


_cache_instance: Optional[RedisCacheClient] = None


def get_redis_cache() -> RedisCacheClient:
    """Provides a singleton instance of the `RedisCacheClient`.

    Returns:
        The singleton `RedisCacheClient` instance.
    """
    global _cache_instance
    if _cache_instance is None:
        settings = get_settings()
        _cache_instance = RedisCacheClient(
            host=settings.redis.redis_host,
            port=settings.redis.redis_port,
            db=settings.redis.redis_db,
            password=settings.redis.redis_password,
            namespace=settings.redis.redis_namespace,
        )
    return _cache_instance
