"""
Interface for Cache Client

Defines the contract for distributed caching services.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from enum import Enum


class CacheType(Enum):
    """Cache types for namespacing"""

    PREDICTION = "prediction"
    FEATURE = "feature"
    MODEL = "model"
    METADATA = "metadata"


class ICacheClient(ABC):
    """
    Interface for distributed caching services.

    Provides key-value storage with TTL support and namespacing.
    """

    @abstractmethod
    def get(self, key: str, cache_type: CacheType = CacheType.PREDICTION) -> Optional[Any]:
        """
        Retrieve a cached value.

        Args:
            key: Cache key
            cache_type: Type of cache for namespacing

        Returns:
            Cached value if found, None otherwise

        Raises:
            RuntimeError: If cache operation fails
        """
        pass

    @abstractmethod
    def set(
        self,
        key: str,
        value: Any,
        cache_type: CacheType = CacheType.PREDICTION,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store a value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (must be serializable)
            cache_type: Type of cache for namespacing
            ttl: Time-to-live in seconds (None for default)

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If value cannot be serialized
            RuntimeError: If cache operation fails
        """
        pass

    @abstractmethod
    def delete(self, key: str, cache_type: CacheType = CacheType.PREDICTION) -> bool:
        """
        Remove a value from cache.

        Args:
            key: Cache key
            cache_type: Type of cache for namespacing

        Returns:
            True if key was deleted, False if key didn't exist

        Raises:
            RuntimeError: If cache operation fails
        """
        pass
