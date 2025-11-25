"""
Result Cache Manager - Handles result caching and cleanup.

This module provides a focused class for managing cached batch job results,
including caching, retrieval, expiration, and size management.
"""

import asyncio
import time
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ResultCacheManager:
    """Manages caching of batch job results.

    Responsibilities:
    - Caching job results
    - Retrieving cached results
    - Expired cache cleanup
    - Cache size management
    """

    def __init__(self, settings: Settings):
        """Initialize the result cache manager.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self._result_cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl = (
            self.settings.performance.async_batch_cache_ttl_seconds
        )
        self._max_cache_size = (
            self.settings.performance.async_batch_result_cache_max_size
        )
        self._lock: asyncio.Lock | None = None

    def _ensure_lock(self) -> asyncio.Lock:
        """Ensure the lock is initialized.

        Returns:
            The initialized lock.

        Raises:
            RuntimeError: If no event loop is available.
        """
        if self._lock is None:
            try:
                self._lock = asyncio.Lock()
            except RuntimeError:
                raise RuntimeError(
                    "ResultCacheManager requires an active event loop. "
                    "Ensure you're in an async context."
                )
        return self._lock

    async def cache_result(
        self,
        job_id: str,
        job_info: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> None:
        """Cache job results.

        Args:
            job_id: The job identifier.
            job_info: Job metadata dictionary.
            results: List of prediction results.
        """
        current_time = time.time()

        async with self._ensure_lock():
            # Cleanup expired cache entries
            await self._cleanup_expired_cache(current_time)

            # Enforce cache size limit
            await self._enforce_cache_size_limit()

            # Cache the result
            self._result_cache[job_id] = {
                "job_info": job_info,
                "results": results,
                "cached_at": current_time,
            }

        logger.debug(f"Cached results for job {job_id}", cache_size=len(self._result_cache))

    async def get_cached_result(
        self, job_id: str, current_time: float | None = None
    ) -> list[dict[str, Any]] | None:
        """Retrieve cached results for a job.

        Args:
            job_id: The job identifier.
            current_time: Current timestamp (for testing). If None, uses time.time().

        Returns:
            Cached results if available and not expired, None otherwise.
        """
        if current_time is None:
            current_time = time.time()

        async with self._ensure_lock():
            if job_id not in self._result_cache:
                return None

            cache_entry = self._result_cache[job_id]

            # Check if cache entry has expired
            if current_time - cache_entry["cached_at"] >= self._cache_ttl:
                # Remove expired entry
                del self._result_cache[job_id]
                logger.debug(f"Cache entry expired for job {job_id}")
                return None

            # Return cached results (copy reference while holding lock)
            return cache_entry["results"]

    async def _cleanup_expired_cache(self, current_time: float) -> None:
        """Remove expired cache entries.

        Args:
            current_time: Current timestamp.
        """
        expired_keys = [
            k
            for k, v in self._result_cache.items()
            if current_time - v["cached_at"] >= self._cache_ttl
        ]

        for key in expired_keys:
            del self._result_cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    async def _enforce_cache_size_limit(self) -> None:
        """Enforce cache size limit by removing oldest entries."""
        if len(self._result_cache) < self._max_cache_size:
            return

        # Remove oldest entries
        sorted_cache = sorted(
            self._result_cache.items(), key=lambda x: x[1]["cached_at"]
        )
        num_to_remove = len(self._result_cache) - self._max_cache_size + 1

        for key, _ in sorted_cache[:num_to_remove]:
            del self._result_cache[key]

        logger.debug(
            f"Enforced cache size limit, removed {num_to_remove} oldest entries"
        )

    def get_cache_size(self) -> int:
        """Get current cache size.

        Returns:
            Number of cached entries.
        """
        return len(self._result_cache)

    async def clear_cache(self) -> None:
        """Clear all cached results."""
        async with self._ensure_lock():
            self._result_cache.clear()
        logger.info("Cache cleared")

