"""Redis caching configuration settings."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class RedisConfig(BaseSettings):
    """Redis distributed caching configuration.

    Attributes:
        redis_enabled: Enable Redis distributed caching.
        redis_host: Redis server host.
        redis_port: Redis server port.
        redis_db: Redis database number.
        redis_password: Redis password for authentication.
        redis_max_connections: Maximum number of Redis connections in pool.
        redis_socket_timeout: Redis socket timeout in seconds.
        redis_socket_connect_timeout: Redis socket connection timeout in seconds.
        redis_namespace: Redis key namespace prefix.
        redis_prediction_cache_ttl: TTL for prediction cache entries in seconds.
        redis_feature_cache_ttl: TTL for feature cache entries in seconds.
    """

    redis_enabled: bool = Field(
        default=False,
        description="Enable Redis distributed caching",
    )
    redis_host: str = Field(
        default="localhost",
        description="Redis server host",
        min_length=1,
    )
    redis_port: int = Field(
        default=6379,
        description="Redis server port",
        ge=1,
        le=65535,
    )
    redis_db: int = Field(
        default=0,
        description="Redis database number",
        ge=0,
        le=15,
    )
    redis_password: Optional[str] = Field(
        default=None,
        description="Redis password for authentication",
        exclude=True,  # Don't include in API responses
    )
    redis_max_connections: int = Field(
        default=50,
        description="Maximum number of Redis connections in pool",
        ge=10,
        le=1000,
    )
    redis_socket_timeout: int = Field(
        default=5,
        description="Redis socket timeout in seconds",
        ge=1,
        le=60,
    )
    redis_socket_connect_timeout: int = Field(
        default=5,
        description="Redis socket connection timeout in seconds",
        ge=1,
        le=60,
    )
    redis_namespace: str = Field(
        default="kubesentiment",
        description="Redis key namespace prefix",
        min_length=1,
        max_length=50,
    )
    redis_prediction_cache_ttl: int = Field(
        default=3600,
        description="TTL for prediction cache entries in seconds",
        ge=60,
        le=86400,
    )
    redis_feature_cache_ttl: int = Field(
        default=1800,
        description="TTL for feature cache entries in seconds",
        ge=60,
        le=86400,
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
