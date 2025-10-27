"""
Configuration management for the MLOps sentiment analysis service.

This module handles all configuration settings, environment variables,
and application parameters in a centralized manner with comprehensive validation.
"""

import os
import re
from functools import cached_property
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Manages application settings, environment variables, and secrets.

    This class centralizes all configuration parameters for the application.
    Settings are loaded from environment variables with the prefix 'MLOPS_'.
    It supports HashiCorp Vault for secure secret management, falling back to
    environment variables if Vault is not enabled.

    Attributes:
        app_name: The name of the application.
        app_version: The version of the application.
        debug: A flag to enable or disable debug mode.
        host: The host on which the server will run.
        port: The port on which the server will listen.
        workers: The number of worker processes for the server.
        model_name: The identifier of the Hugging Face model to be used.
        allowed_models: A list of model names that are permitted for use.
        model_cache_dir: The directory to cache downloaded models.
        onnx_model_path: The path to the ONNX model for optimized inference.
        onnx_model_path_default: The default path for the ONNX model.
        max_request_timeout: The maximum request timeout in seconds.
        max_text_length: The maximum length of input text.
        prediction_cache_max_size: The maximum number of predictions to cache.
        enable_metrics: A flag to enable or disable metrics collection.
        log_level: The logging level for the application.
        metrics_cache_ttl: The time-to-live for cached Prometheus metrics.
        api_key: The API key for securing application endpoints.
        allowed_origins: A list of allowed origins for CORS.
        vault_enabled: A flag to enable Vault for secrets management.
        vault_addr: The address of the Vault server.
        vault_namespace: The Vault namespace for multi-tenancy.
        vault_role: The Kubernetes service account role for Vault authentication.
        vault_mount_point: The mount point for the KV v2 secrets engine.
        vault_secrets_path: The base path for secrets in Vault.
        vault_token: The Vault token for direct authentication (not for production).
    """

    # Application settings
    app_name: str = Field(
        default="ML Model Serving API",
        description="Application name",
        min_length=1,
        max_length=100,
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version",
        pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$",
    )
    debug: bool = Field(default=False, description="Debug mode")

    # Server settings
    host: str = Field(
        default="0.0.0.0",
        description="Server host",
        pattern=r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|localhost|0\.0\.0\.0)$",
    )
    port: int = Field(default=8000, description="Server port", ge=1024, le=65535)
    workers: int = Field(default=1, description="Number of worker processes", ge=1, le=16)

    # Model settings
    model_name: str = Field(
        default="distilbert-base-uncased-finetuned-sst-2-english",
        description="Hugging Face model identifier",
        min_length=1,
        max_length=200,
    )
    allowed_models: List[str] = Field(
        default_factory=lambda: [
            "distilbert-base-uncased-finetuned-sst-2-english",
            "cardiffnlp/twitter-roberta-base-sentiment-latest",
            "nlptown/bert-base-multilingual-uncased-sentiment",
            "j-hartmann/emotion-english-distilroberta-base",
        ],
        description="List of allowed model names for security",
        min_length=1,
    )
    model_cache_dir: Optional[str] = Field(
        default=None, description="Directory to cache downloaded models"
    )
    onnx_model_path: Optional[str] = Field(
        default=None, description="Path to ONNX model directory for optimized inference"
    )
    onnx_model_path_default: str = Field(
        default="./onnx_models/distilbert-base-uncased-finetuned-sst-2-english",
        description="Default ONNX model path when onnx_model_path is not set",
    )

    # Performance settings
    max_request_timeout: int = Field(
        default=30, description="Maximum request timeout in seconds", ge=1, le=300
    )
    max_text_length: int = Field(
        default=512, description="Maximum input text length", ge=1, le=10000
    )

    # Feature Engineering settings
    enable_feature_engineering: bool = Field(
        default=False, description="Enable advanced feature engineering"
    )

    # Cache settings
    prediction_cache_max_size: int = Field(
        default=1000,
        description="Maximum number of cached predictions",
        ge=10,
        le=100000,
    )

    # Monitoring settings
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )
    metrics_cache_ttl: int = Field(
        default=5,
        description="Seconds to cache generated Prometheus metrics",
        ge=1,
        le=300,
    )

    # Security settings
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication",
        min_length=8 if os.getenv("MLOPS_API_KEY") else None,
    )

    # Explicit CORS origins configuration
    allowed_origins: List[str] = Field(
        default_factory=lambda: [
            "https://example.com",
            "https://another-example.com",
        ],
        description="List of allowed origins for CORS",
    )

    # Vault integration settings
    vault_enabled: bool = Field(
        default=False, description="Enable HashiCorp Vault for secrets management"
    )
    vault_addr: Optional[str] = Field(
        default=None, description="Vault server address (e.g., http://vault:8200)"
    )
    vault_namespace: Optional[str] = Field(
        default="mlops", description="Vault namespace for multi-tenancy (Enterprise feature)"
    )
    vault_role: Optional[str] = Field(
        default=None, description="Kubernetes service account role for Vault authentication"
    )
    vault_mount_point: str = Field(
        default="mlops-sentiment", description="KV v2 secrets engine mount point in Vault"
    )
    vault_secrets_path: str = Field(
        default="mlops-sentiment", description="Base path for secrets in Vault"
    )
    vault_token: Optional[str] = Field(
        default=None,
        description="Vault token for direct authentication (not recommended for production)",
        exclude=True,  # Don't include in API responses
    )

    # Kafka streaming settings
    kafka_enabled: bool = Field(default=False, description="Enable Kafka streaming")
    kafka_bootstrap_servers: List[str] = Field(
        default_factory=lambda: ["localhost:9092"],
        description="Kafka bootstrap servers",
        min_length=1,
    )
    kafka_consumer_group: str = Field(
        default="kubesentiment_consumer",
        description="Kafka consumer group ID",
        min_length=1,
    )
    kafka_topic: str = Field(
        default="sentiment_requests",
        description="Kafka topic to consume from",
        min_length=1,
    )
    kafka_auto_offset_reset: str = Field(
        default="latest",
        description="Auto offset reset strategy",
        pattern=r"^(earliest|latest|none)$",
    )
    kafka_max_poll_records: int = Field(
        default=500,
        description="Maximum records to poll per request",
        ge=1,
        le=10000,
    )
    kafka_session_timeout_ms: int = Field(
        default=30000,
        description="Session timeout in milliseconds",
        ge=1000,
        le=300000,
    )
    kafka_heartbeat_interval_ms: int = Field(
        default=3000,
        description="Heartbeat interval in milliseconds",
        ge=1000,
        le=30000,
    )
    kafka_max_poll_interval_ms: int = Field(
        default=300000,
        description="Maximum poll interval in milliseconds",
        ge=10000,
        le=2147483647,
    )
    kafka_enable_auto_commit: bool = Field(
        default=False,
        description="Enable automatic offset commits",
    )
    kafka_auto_commit_interval_ms: int = Field(
        default=5000,
        description="Auto commit interval in milliseconds",
        ge=1000,
        le=60000,
    )

    # High-throughput consumer settings
    kafka_consumer_threads: int = Field(
        default=4,
        description="Number of consumer threads for parallel processing",
        ge=1,
        le=32,
    )
    kafka_batch_size: int = Field(
        default=100,
        description="Batch size for processing messages",
        ge=1,
        le=1000,
    )
    kafka_processing_timeout_ms: int = Field(
        default=30000,
        description="Processing timeout per batch in milliseconds",
        ge=1000,
        le=300000,
    )
    kafka_buffer_size: int = Field(
        default=10000,
        description="Internal buffer size for message queuing",
        ge=1000,
        le=100000,
    )

    # Dead letter queue settings
    kafka_dlq_topic: str = Field(
        default="sentiment_requests_dlq",
        description="Dead letter queue topic for failed messages",
    )
    kafka_dlq_enabled: bool = Field(
        default=True,
        description="Enable dead letter queue for failed messages",
    )
    kafka_max_retries: int = Field(
        default=3,
        description="Maximum number of retries before sending to DLQ",
        ge=1,
        le=10,
    )

    # Producer settings for DLQ
    kafka_producer_bootstrap_servers: List[str] = Field(
        default_factory=lambda: ["localhost:9092"],
        description="Kafka bootstrap servers for producer (DLQ)",
        min_length=1,
    )
    kafka_producer_acks: str = Field(
        default="all",
        description="Producer acknowledgment level",
        pattern=r"^(0|1|all)$",
    )
    kafka_producer_retries: int = Field(
        default=3,
        description="Number of producer retries",
        ge=0,
        le=10,
    )
    kafka_producer_batch_size: int = Field(
        default=16384,
        description="Producer batch size in bytes",
        ge=0,
        le=1048576,
    )
    kafka_producer_linger_ms: int = Field(
        default=5,
        description="Producer linger time in milliseconds",
        ge=0,
        le=100,
    )
    kafka_producer_compression_type: str = Field(
        default="lz4",
        description="Producer compression type",
        pattern=r"^(none|gzip|snappy|lz4|zstd)$",
    )

    # Async batch processing settings
    async_batch_enabled: bool = Field(default=True, description="Enable async batch processing")
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
        le=86400,  # Max 24 hours
    )
    async_batch_result_cache_max_size: int = Field(
        default=1000,
        description="Maximum number of cached batch results",
        ge=100,
        le=10000,
    )

    # Redis cache settings
    redis_enabled: bool = Field(default=False, description="Enable Redis distributed caching")
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
        le=86400,  # Max 24 hours
    )
    redis_feature_cache_ttl: int = Field(
        default=1800,
        description="TTL for feature cache entries in seconds",
        ge=60,
        le=86400,
    )

    # Anomaly buffer settings
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

    # Distributed Kafka consumer settings
    kafka_partition_assignment_strategy: str = Field(
        default="roundrobin",
        description="Partition assignment strategy for consumer group",
        pattern=r"^(range|roundrobin|sticky)$",
    )

    @field_validator("allowed_models")
    @classmethod
    def validate_model_names(cls, v):
        """Validates the format of each model name in the allowed list.

        Args:
            v: The list of allowed model names.

        Returns:
            The validated list of model names.

        Raises:
            ValueError: If a model name has an invalid format or is too long.
        """
        for model_name in v:
            # Basic validation for Hugging Face model names
            if not re.match(r"^[a-zA-Z0-9/_-]+$", model_name):
                raise ValueError(f"Invalid model name format: {model_name}")
            if len(model_name) > 200:
                raise ValueError(f"Model name too long: {model_name}")
        return v

    @field_validator("model_cache_dir")
    @classmethod
    def validate_cache_dir(cls, v):
        """Validates that the cache directory is an absolute path and its parent exists.

        Args:
            v: The path to the model cache directory.

        Returns:
            The validated cache directory path.

        Raises:
            ValueError: If the path is not absolute or the parent directory does not exist.
        """
        if v is not None:
            # Check if path is absolute and valid
            if not os.path.isabs(v):
                raise ValueError("Cache directory must be an absolute path")
            # Check if parent directory exists (don't create automatically)
            parent_dir = os.path.dirname(v)
            if not os.path.exists(parent_dir):
                raise ValueError(f"Parent directory does not exist: {parent_dir}")
        return v

    @property
    def cors_origins(self) -> List[str]:
        """Provides the list of CORS origins for middleware configuration.

        Returns:
            A list of strings representing the allowed origins for CORS.
        """
        return self.allowed_origins

    @field_validator("allowed_origins")
    @classmethod
    def validate_cors_origins(cls, v):
        """Validates the format of CORS origin URLs and disallows wildcards.

        Args:
            v: The list of CORS origins.

        Returns:
            The validated list of CORS origins.

        Raises:
            ValueError: If a wildcard origin is used or a URL is invalid.
        """
        for origin in v:
            # Wildcard CORS is a security risk - require explicit origins
            if origin == "*":
                raise ValueError(
                    "Wildcard CORS origin '*' is not allowed. "
                    "Specify explicit origins for security."
                )

            # Validate URL format
            url_pattern = re.compile(r"^https?://[a-zA-Z0-9.-]+(?:\:[0-9]+)?(?:/.*)?$")
            if not url_pattern.match(origin):
                raise ValueError(f"Invalid CORS origin URL: {origin}")
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v):
        """Validates the strength of the API key.

        The key must be at least 8 characters long and contain both letters and numbers.

        Args:
            v: The API key.

        Returns:
            The validated API key.

        Raises:
            ValueError: If the API key is not strong enough.
        """
        if v is not None:
            if len(v) < 8:
                raise ValueError("API key must be at least 8 characters")
            # Check for basic complexity
            if not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v):
                raise ValueError("API key must contain both letters and numbers")
        return v

    def _validate_model_in_allowed_list(self) -> None:
        """Ensures the selected model_name is in the allowed_models list.

        Raises:
            ValueError: If `model_name` is not in `allowed_models`.
        """
        if self.model_name and self.allowed_models and self.model_name not in self.allowed_models:
            raise ValueError(
                f"Model '{self.model_name}' must be in allowed_models list: {self.allowed_models}"
            )

    def _validate_worker_count_consistency(self) -> None:
        """Validates that multiple workers are not used in debug mode.

        Raises:
            ValueError: If `debug` is True and `workers` is greater than 1.
        """
        if self.debug and self.workers > 1:
            raise ValueError("Cannot use multiple workers in debug mode")

    def _validate_cache_memory_usage(self) -> None:
        """Estimates cache memory usage to prevent excessive allocation.

        Raises:
            ValueError: If the estimated memory usage exceeds a predefined limit.
        """
        # Rough estimate: each cache entry might be ~1KB per 100 chars
        estimated_memory_mb = (self.prediction_cache_max_size * self.max_text_length) / 100000
        if estimated_memory_mb > 1000:  # 1GB limit
            raise ValueError(
                f"Cache configuration may use too much memory (~{estimated_memory_mb:.0f}MB). "
                "Reduce cache_size or max_text_length."
            )

    @model_validator(mode="after")
    def validate_configuration_consistency(self):
        """Performs cross-field validation to ensure configuration consistency.

        This validator runs after individual field validators and checks relationships
        between different configuration settings.

        Returns:
            The validated Settings instance.
        """
        self._validate_model_in_allowed_list()
        self._validate_worker_count_consistency()
        self._validate_cache_memory_usage()
        return self

    @cached_property
    def secret_manager(self):
        """Initializes and retrieves the appropriate secret manager.

        This property lazily initializes the secret manager based on whether Vault
        is enabled. It returns either a `VaultSecretManager` or an
        `EnvironmentSecretManager` instance.

        Returns:
            An instance of a secret manager.
        """
        from app.core.secrets import get_secret_manager

        return get_secret_manager(
            vault_enabled=self.vault_enabled,
            vault_addr=self.vault_addr,
            vault_namespace=self.vault_namespace,
            vault_role=self.vault_role,
            vault_mount_point=self.vault_mount_point,
            vault_secrets_path=self.vault_secrets_path,
            env_prefix="MLOPS_",
        )

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a secret from the configured secret manager.

        This method abstracts the secret retrieval process, allowing other parts
        of the application to fetch secrets without needing to know the
        underlying secret management system.

        Args:
            key: The key of the secret to retrieve.
            default: The default value to return if the secret is not found.

        Returns:
            The value of the secret, or the default value if not found.
        """
        return self.secret_manager.get_secret(key, default)

    class Config:
        """Pydantic configuration options for the Settings class.

        Attributes:
            env_prefix: The prefix for environment variables (e.g., `MLOPS_APP_NAME`).
            env_file: The name of the environment file to load (e.g., `.env`).
            case_sensitive: A flag indicating whether environment variables are case-sensitive.
            extra: A setting to ignore extra fields provided.
        """

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency function to get the application settings instance.

    This function is used by FastAPI's dependency injection system to provide
    the global `Settings` object to route handlers and other dependencies.

    Returns:
        The singleton instance of the application settings.
    """
    return settings
