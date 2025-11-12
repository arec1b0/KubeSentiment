"""Performance and async processing configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings


class PerformanceConfig(BaseSettings):
    """Performance tuning and async processing configuration.

    Attributes:
        async_batch_enabled: Enable async batch processing.
        async_batch_max_jobs: Maximum number of concurrent batch jobs.
        async_batch_max_batch_size: Maximum batch size for async processing.
        async_batch_default_timeout_seconds: Default timeout for batch jobs.
        async_batch_priority_high_limit: Maximum high priority jobs in queue.
        async_batch_priority_medium_limit: Maximum medium priority jobs in queue.
        async_batch_priority_low_limit: Maximum low priority jobs in queue.
        async_batch_cleanup_interval_seconds: Interval for cleaning up expired jobs.
        async_batch_cache_ttl_seconds: Time-to-live for cached batch results.
        async_batch_result_cache_max_size: Maximum number of cached batch results.
        anomaly_buffer_enabled: Enable anomaly detection buffer.
        anomaly_buffer_max_size: Maximum number of anomalies to store in buffer.
        anomaly_buffer_default_ttl: Default TTL for anomaly entries in seconds.
        anomaly_buffer_cleanup_interval: Interval for cleaning up expired anomalies.
    """

    # Async batch processing
    async_batch_enabled: bool = Field(
        default=True,
        description="Enable async batch processing",
    )
    async_batch_max_jobs: int = Field(
        default=1000,
        description="Maximum number of concurrent batch jobs",
        ge=10,
        le=10000,
    )
    async_batch_max_batch_size: int = Field(
        default=1000,
        description="Maximum batch size for async processing",
        ge=10,
        le=10000,
    )
    async_batch_default_timeout_seconds: int = Field(
        default=300,
        description="Default timeout for batch jobs in seconds",
        ge=30,
        le=3600,
    )
    async_batch_priority_high_limit: int = Field(
        default=100,
        description="Maximum high priority jobs in queue",
        ge=10,
        le=1000,
    )
    async_batch_priority_medium_limit: int = Field(
        default=500,
        description="Maximum medium priority jobs in queue",
        ge=100,
        le=5000,
    )
    async_batch_priority_low_limit: int = Field(
        default=1000,
        description="Maximum low priority jobs in queue",
        ge=200,
        le=10000,
    )
    async_batch_cleanup_interval_seconds: int = Field(
        default=60,
        description="Interval for cleaning up expired jobs",
        ge=10,
        le=3600,
    )
    async_batch_cache_ttl_seconds: int = Field(
        default=3600,
        description="Time-to-live for cached batch results",
        ge=300,
        le=86400,
    )
    async_batch_result_cache_max_size: int = Field(
        default=1000,
        description="Maximum number of cached batch results",
        ge=100,
        le=10000,
    )

    # Anomaly buffer
    anomaly_buffer_enabled: bool = Field(
        default=True,
        description="Enable anomaly detection buffer",
    )
    anomaly_buffer_max_size: int = Field(
        default=10000,
        description="Maximum number of anomalies to store in buffer",
        ge=100,
        le=100000,
    )
    anomaly_buffer_default_ttl: int = Field(
        default=3600,
        description="Default TTL for anomaly entries in seconds",
        ge=300,
        le=86400,
    )
    anomaly_buffer_cleanup_interval: int = Field(
        default=300,
        description="Interval for cleaning up expired anomalies in seconds",
        ge=60,
        le=3600,
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
