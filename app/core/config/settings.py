"""
Root Settings class composing all domain-specific configurations.

This module provides the main Settings class that brings together all
domain-specific configuration classes into a single, cohesive settings object.
"""

import os
from functools import cached_property
from typing import Any, List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings

from app.core.config.data_lake import DataLakeConfig
from app.core.config.kafka import KafkaConfig
from app.core.config.mlops import MLOpsConfig
from app.core.config.model import ModelConfig
from app.core.config.monitoring import MonitoringConfig
from app.core.config.performance import PerformanceConfig
from app.core.config.profiles import load_profile, get_profile_info
from app.core.config.redis import RedisConfig
from app.core.config.security import SecurityConfig
from app.core.config.server import ServerConfig
from app.core.config.vault import VaultConfig


class Settings(BaseSettings):
    """Main settings class composing all domain-specific configurations.

    This class brings together all configuration domains (server, model, kafka,
    etc.) into a single settings object while maintaining clean separation of
    concerns. Each domain is represented by a nested configuration object.

    For backward compatibility, all settings are also accessible as direct
    attributes on the Settings instance (e.g., settings.model_name is equivalent
    to settings.model.model_name).

    Attributes:
        server: Server and application configuration.
        model: ML model configuration.
        security: Security and authentication configuration.
        performance: Performance and async processing configuration.
        kafka: Kafka streaming configuration.
        redis: Redis caching configuration.
        vault: HashiCorp Vault secrets management configuration.
        data_lake: Data lake integration configuration.
        monitoring: Monitoring, logging, and tracing configuration.
        mlops: MLOps configuration (MLflow, drift detection, explainability).
    """

    # Domain-specific configuration objects
    server: ServerConfig = ServerConfig()
    model: ModelConfig = ModelConfig()
    security: SecurityConfig = SecurityConfig()
    performance: PerformanceConfig = PerformanceConfig()
    kafka: KafkaConfig = KafkaConfig()
    redis: RedisConfig = RedisConfig()
    vault: VaultConfig = VaultConfig()
    data_lake: DataLakeConfig = DataLakeConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    mlops: MLOpsConfig = MLOpsConfig()

    # Backward compatibility: expose commonly used settings as direct attributes
    @property
    def app_name(self) -> str:
        """Application name (backward compatibility)."""
        return self.server.app_name

    @property
    def app_version(self) -> str:
        """Application version (backward compatibility)."""
        return self.server.app_version

    @property
    def debug(self) -> bool:
        """Debug mode (backward compatibility)."""
        return self.server.debug

    @property
    def host(self) -> str:
        """Server host (backward compatibility)."""
        return self.server.host

    @property
    def port(self) -> int:
        """Server port (backward compatibility)."""
        return self.server.port

    @property
    def workers(self) -> int:
        """Number of worker processes (backward compatibility)."""
        return self.server.workers

    @property
    def environment(self) -> str:
        """Deployment environment (backward compatibility)."""
        return self.server.environment

    @property
    def model_name(self) -> str:
        """Model name (backward compatibility)."""
        return self.model.model_name

    @property
    def allowed_models(self) -> List[str]:
        """Allowed models (backward compatibility)."""
        return self.model.allowed_models

    @property
    def model_cache_dir(self) -> Optional[str]:
        """Model cache directory (backward compatibility)."""
        return self.model.model_cache_dir

    @property
    def onnx_model_path(self) -> Optional[str]:
        """ONNX model path (backward compatibility)."""
        return self.model.onnx_model_path

    @property
    def onnx_model_path_default(self) -> str:
        """Default ONNX model path (backward compatibility)."""
        return self.model.onnx_model_path_default

    @property
    def max_text_length(self) -> int:
        """Maximum text length (backward compatibility)."""
        return self.model.max_text_length

    @property
    def prediction_cache_max_size(self) -> int:
        """Prediction cache max size (backward compatibility)."""
        return self.model.prediction_cache_max_size

    @property
    def enable_feature_engineering(self) -> bool:
        """Enable feature engineering (backward compatibility)."""
        return self.model.enable_feature_engineering

    @property
    def api_key(self) -> Optional[str]:
        """API key (backward compatibility)."""
        return self.security.api_key

    @property
    def allowed_origins(self) -> List[str]:
        """Allowed CORS origins (backward compatibility)."""
        return self.security.allowed_origins

    @property
    def cors_origins(self) -> List[str]:
        """CORS origins (backward compatibility)."""
        return self.security.cors_origins

    @property
    def max_request_timeout(self) -> int:
        """Max request timeout (backward compatibility)."""
        return self.security.max_request_timeout

    @property
    def enable_metrics(self) -> bool:
        """Enable metrics (backward compatibility)."""
        return self.monitoring.enable_metrics

    @property
    def log_level(self) -> str:
        """Log level (backward compatibility)."""
        return self.monitoring.log_level

    @property
    def metrics_cache_ttl(self) -> int:
        """Metrics cache TTL (backward compatibility)."""
        return self.monitoring.metrics_cache_ttl

    @property
    def service_name(self) -> str:
        """Service name for tracing (backward compatibility)."""
        return self.monitoring.service_name

    @property
    def enable_tracing(self) -> bool:
        """Enable distributed tracing (backward compatibility)."""
        return self.monitoring.enable_tracing

    @property
    def tracing_backend(self) -> str:
        """Tracing backend (backward compatibility)."""
        return self.monitoring.tracing_backend

    @property
    def jaeger_agent_host(self) -> str:
        """Jaeger agent host (backward compatibility)."""
        return self.monitoring.jaeger_agent_host

    @property
    def jaeger_agent_port(self) -> int:
        """Jaeger agent port (backward compatibility)."""
        return self.monitoring.jaeger_agent_port

    @property
    def zipkin_endpoint(self) -> str:
        """Zipkin endpoint (backward compatibility)."""
        return self.monitoring.zipkin_endpoint

    @property
    def otlp_endpoint(self) -> str:
        """OTLP endpoint (backward compatibility)."""
        return self.monitoring.otlp_endpoint

    @property
    def tracing_excluded_urls(self) -> str:
        """Tracing excluded URLs (backward compatibility)."""
        return self.monitoring.tracing_excluded_urls

    # Expose remaining commonly accessed properties
    @property
    def kafka_enabled(self) -> bool:
        """Kafka enabled (backward compatibility)."""
        return self.kafka.kafka_enabled

    @property
    def redis_enabled(self) -> bool:
        """Redis enabled (backward compatibility)."""
        return self.redis.redis_enabled

    @property
    def vault_enabled(self) -> bool:
        """Vault enabled (backward compatibility)."""
        return self.vault.vault_enabled

    @property
    def vault_addr(self) -> Optional[str]:
        """Vault address (backward compatibility)."""
        return self.vault.vault_addr

    @property
    def vault_namespace(self) -> Optional[str]:
        """Vault namespace (backward compatibility)."""
        return self.vault.vault_namespace

    @property
    def vault_role(self) -> Optional[str]:
        """Vault role (backward compatibility)."""
        return self.vault.vault_role

    @property
    def vault_mount_point(self) -> str:
        """Vault mount point (backward compatibility)."""
        return self.vault.vault_mount_point

    @property
    def vault_secrets_path(self) -> str:
        """Vault secrets path (backward compatibility)."""
        return self.vault.vault_secrets_path

    @property
    def data_lake_enabled(self) -> bool:
        """Data lake enabled (backward compatibility)."""
        return self.data_lake.data_lake_enabled

    @property
    def mlflow_enabled(self) -> bool:
        """MLflow enabled (backward compatibility)."""
        return self.mlops.mlflow_enabled

    @property
    def drift_detection_enabled(self) -> bool:
        """Drift detection enabled (backward compatibility)."""
        return self.mlops.drift_detection_enabled

    @property
    def explainability_enabled(self) -> bool:
        """Explainability enabled (backward compatibility)."""
        return self.mlops.explainability_enabled

    @property
    def async_batch_enabled(self) -> bool:
        """Async batch enabled (backward compatibility)."""
        return self.performance.async_batch_enabled

    @property
    def anomaly_buffer_enabled(self) -> bool:
        """Anomaly buffer enabled (backward compatibility)."""
        return self.performance.anomaly_buffer_enabled

    # Additional frequently accessed Kafka properties
    @property
    def kafka_bootstrap_servers(self) -> List[str]:
        """Kafka bootstrap servers (backward compatibility)."""
        return self.kafka.kafka_bootstrap_servers

    @property
    def kafka_consumer_group(self) -> str:
        """Kafka consumer group (backward compatibility)."""
        return self.kafka.kafka_consumer_group

    @property
    def kafka_topic(self) -> str:
        """Kafka topic (backward compatibility)."""
        return self.kafka.kafka_topic

    def _validate_model_in_allowed_list(self) -> None:
        """Ensures the selected model_name is in the allowed_models list.

        Raises:
            ValueError: If model_name is not in allowed_models.
        """
        if self.model.model_name and self.model.allowed_models:
            if self.model.model_name not in self.model.allowed_models:
                raise ValueError(
                    f"Model '{self.model.model_name}' must be in allowed_models list: "
                    f"{self.model.allowed_models}"
                )

    def _validate_worker_count_consistency(self) -> None:
        """Validates that multiple workers are not used in debug mode.

        Raises:
            ValueError: If debug is True and workers is greater than 1.
        """
        if self.server.debug and self.server.workers > 1:
            raise ValueError("Cannot use multiple workers in debug mode")

    def _validate_cache_memory_usage(self) -> None:
        """Estimates cache memory usage to prevent excessive allocation.

        Raises:
            ValueError: If the estimated memory usage exceeds a predefined limit.
        """
        estimated_memory_mb = (
            self.model.prediction_cache_max_size * self.model.max_text_length
        ) / 100000
        if estimated_memory_mb > 1000:  # 1GB limit
            raise ValueError(
                f"Cache configuration may use too much memory (~{estimated_memory_mb:.0f}MB). "
                "Reduce cache_size or max_text_length."
            )

    @model_validator(mode="after")
    def validate_configuration_consistency(self):
        """Performs cross-field validation to ensure configuration consistency.

        Returns:
            The validated Settings instance.
        """
        self._validate_model_in_allowed_list()
        self._validate_worker_count_consistency()
        self._validate_cache_memory_usage()
        return self

    @cached_property
    def secret_manager(self) -> Any:
        """Initializes and retrieves the appropriate secret manager.

        This property lazily initializes the secret manager, choosing between
        HashiCorp Vault and environment variables based on the configuration.

        Returns:
            An instance of a SecretManager implementation.
        """
        from app.core.secrets import get_secret_manager

        return get_secret_manager(
            vault_enabled=self.vault.vault_enabled,
            vault_addr=self.vault.vault_addr,
            vault_namespace=self.vault.vault_namespace,
            vault_role=self.vault.vault_role,
            vault_mount_point=self.vault.vault_mount_point,
            vault_secrets_path=self.vault.vault_secrets_path,
            env_prefix="MLOPS_",
        )

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a secret from the configured secret manager.

        Args:
            key: The key of the secret to retrieve.
            default: The default value to return if the secret is not found.

        Returns:
            The value of the secret, or the default value if not found.
        """
        return self.secret_manager.get_secret(key, default)

    @classmethod
    def load_from_profile(cls, profile_name: Optional[str] = None) -> "Settings":
        """Load settings with profile-based defaults.

        This method creates a Settings instance with environment-specific defaults
        from the specified profile. Environment variables can still override these
        defaults.

        Args:
            profile_name: Name of the profile to load (local, development, staging,
                         production). If None, uses MLOPS_PROFILE or defaults to
                         'development'.

        Returns:
            Settings instance with profile defaults applied.

        Example:
            # Load development profile
            settings = Settings.load_from_profile('development')

            # Load from environment variable MLOPS_PROFILE
            settings = Settings.load_from_profile()
        """
        # Determine profile name
        if profile_name is None:
            profile_name = os.getenv("MLOPS_PROFILE", "development")

        # Load profile overrides
        profile_overrides = load_profile(profile_name)

        # Apply overrides to environment (only if not already set)
        for key, value in profile_overrides.items():
            if key not in os.environ:
                os.environ[key] = str(value)

        # Create settings instance (will read from environment)
        return cls()

    @staticmethod
    def get_available_profiles() -> dict:
        """Get information about available configuration profiles.

        Returns:
            Dictionary with profile information.
        """
        return get_profile_info()

    def get_active_profile(self) -> str:
        """Get the name of the currently active profile.

        Returns:
            Profile name based on the environment setting.
        """
        env = self.server.environment.lower()
        # Map environment names to profile names
        profile_map = {
            "local": "local",
            "development": "development",
            "dev": "development",
            "staging": "staging",
            "production": "production",
            "prod": "production",
        }
        return profile_map.get(env, env)

    class Config:
        """Pydantic configuration options for the Settings class.

        Attributes:
            env_prefix: The prefix for environment variables (e.g., MLOPS_APP_NAME).
            env_file: The name of the environment file to load (e.g., .env).
            case_sensitive: Whether environment variables are case-sensitive.
            extra: Setting to ignore extra fields provided.
        """

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Load settings with profile support
# Use MLOPS_PROFILE environment variable or default to 'development'
_profile_name = os.getenv("MLOPS_PROFILE")
if _profile_name:
    settings = Settings.load_from_profile(_profile_name)
else:
    # Fallback to standard loading for backward compatibility
    settings = Settings()


def get_settings() -> Settings:
    """Provides a dependency-injected instance of the application settings.

    This function is used by FastAPI's dependency injection system to make the
    global Settings object available to route handlers and other dependencies.

    Returns:
        The singleton instance of the application settings.
    """
    return settings
