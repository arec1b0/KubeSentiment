"""
Configuration profiles for different deployment environments.

This module provides environment-specific configuration profiles that set
appropriate defaults for development, staging, and production environments,
reducing the need for extensive environment variable configuration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ConfigProfile(ABC):
    """Base class for configuration profiles.

    Each profile defines environment-specific defaults that override
    the base configuration values. This reduces environment variable
    sprawl by providing sensible defaults for each environment.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Profile name (dev, staging, production)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Profile description."""
        pass

    @abstractmethod
    def get_overrides(self) -> Dict[str, Any]:
        """Get environment-specific configuration overrides.

        Returns:
            Dictionary of configuration overrides keyed by setting name.
        """
        pass

    def apply_to_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply profile overrides to a configuration dictionary.

        Args:
            config_dict: Base configuration dictionary.

        Returns:
            Updated configuration dictionary with profile overrides applied.
        """
        overrides = self.get_overrides()
        config_dict.update(overrides)
        return config_dict


class DevelopmentProfile(ConfigProfile):
    """Development environment profile.

    Optimized for:
    - Local development
    - Debugging
    - Fast iteration
    - Verbose logging
    """

    @property
    def name(self) -> str:
        return "development"

    @property
    def description(self) -> str:
        return "Development environment with debug features enabled"

    def get_overrides(self) -> Dict[str, Any]:
        """Development-specific configuration overrides."""
        return {
            # Server configuration
            "MLOPS_DEBUG": "true",
            "MLOPS_WORKERS": "1",
            "MLOPS_ENVIRONMENT": "development",
            # Logging and monitoring
            "MLOPS_LOG_LEVEL": "DEBUG",
            "MLOPS_ENABLE_METRICS": "true",
            "MLOPS_ENABLE_TRACING": "false",
            # External services (disabled by default in dev)
            "MLOPS_REDIS_ENABLED": "false",
            "MLOPS_KAFKA_ENABLED": "false",
            "MLOPS_VAULT_ENABLED": "false",
            "MLOPS_DATA_LAKE_ENABLED": "false",
            # MLOps features (disabled for faster startup)
            "MLOPS_MLFLOW_ENABLED": "false",
            "MLOPS_DRIFT_DETECTION_ENABLED": "false",
            "MLOPS_EXPLAINABILITY_ENABLED": "false",
            # Performance features (simplified for dev)
            "MLOPS_ASYNC_BATCH_ENABLED": "false",
            "MLOPS_ANOMALY_BUFFER_ENABLED": "false",
            # Security (relaxed for development)
            "MLOPS_API_KEY": "",
            "MLOPS_ALLOWED_ORIGINS": "*",
            "MLOPS_CORS_ORIGINS": "*",
            # Model configuration (smaller cache for dev)
            "MLOPS_PREDICTION_CACHE_MAX_SIZE": "100",
            "MLOPS_MAX_TEXT_LENGTH": "512",
        }


class StagingProfile(ConfigProfile):
    """Staging environment profile.

    Optimized for:
    - Pre-production testing
    - Integration testing
    - Performance validation
    - User acceptance testing
    """

    @property
    def name(self) -> str:
        return "staging"

    @property
    def description(self) -> str:
        return "Staging environment for pre-production testing"

    def get_overrides(self) -> Dict[str, Any]:
        """Staging-specific configuration overrides."""
        return {
            # Server configuration
            "MLOPS_DEBUG": "false",
            "MLOPS_WORKERS": "2",
            "MLOPS_ENVIRONMENT": "staging",
            # Logging and monitoring
            "MLOPS_LOG_LEVEL": "INFO",
            "MLOPS_ENABLE_METRICS": "true",
            "MLOPS_ENABLE_TRACING": "true",
            "MLOPS_TRACING_BACKEND": "jaeger",
            # External services (enabled for realistic testing)
            "MLOPS_REDIS_ENABLED": "true",
            "MLOPS_KAFKA_ENABLED": "false",  # Optional in staging
            "MLOPS_VAULT_ENABLED": "true",
            "MLOPS_DATA_LAKE_ENABLED": "false",
            # MLOps features (enabled for testing)
            "MLOPS_MLFLOW_ENABLED": "true",
            "MLOPS_DRIFT_DETECTION_ENABLED": "true",
            "MLOPS_EXPLAINABILITY_ENABLED": "true",
            # Performance features
            "MLOPS_ASYNC_BATCH_ENABLED": "true",
            "MLOPS_ANOMALY_BUFFER_ENABLED": "true",
            "MLOPS_ASYNC_BATCH_SIZE": "50",
            "MLOPS_ASYNC_BATCH_TIMEOUT": "5.0",
            # Security (enforced but with staging credentials)
            "MLOPS_ALLOWED_ORIGINS": "https://staging.example.com,https://staging-app.example.com",
            "MLOPS_CORS_ORIGINS": "https://staging.example.com",
            "MLOPS_MAX_REQUEST_TIMEOUT": "60",
            # Model configuration (moderate caching)
            "MLOPS_PREDICTION_CACHE_MAX_SIZE": "1000",
            "MLOPS_MAX_TEXT_LENGTH": "512",
            # Redis configuration
            "MLOPS_REDIS_MAX_CONNECTIONS": "50",
            "MLOPS_REDIS_PREDICTION_CACHE_TTL": "3600",
            "MLOPS_REDIS_FEATURE_CACHE_TTL": "1800",
        }


class ProductionProfile(ConfigProfile):
    """Production environment profile.

    Optimized for:
    - Maximum reliability
    - Optimal performance
    - Security hardening
    - Comprehensive monitoring
    """

    @property
    def name(self) -> str:
        return "production"

    @property
    def description(self) -> str:
        return "Production environment with maximum reliability and performance"

    def get_overrides(self) -> Dict[str, Any]:
        """Production-specific configuration overrides."""
        return {
            # Server configuration
            "MLOPS_DEBUG": "false",
            "MLOPS_WORKERS": "4",
            "MLOPS_ENVIRONMENT": "production",
            # Logging and monitoring (less verbose, more efficient)
            "MLOPS_LOG_LEVEL": "WARNING",
            "MLOPS_ENABLE_METRICS": "true",
            "MLOPS_ENABLE_TRACING": "true",
            "MLOPS_TRACING_BACKEND": "otlp",
            "MLOPS_METRICS_CACHE_TTL": "300",
            # External services (all enabled for production)
            "MLOPS_REDIS_ENABLED": "true",
            "MLOPS_KAFKA_ENABLED": "true",
            "MLOPS_VAULT_ENABLED": "true",
            "MLOPS_DATA_LAKE_ENABLED": "true",
            # MLOps features (fully enabled)
            "MLOPS_MLFLOW_ENABLED": "true",
            "MLOPS_DRIFT_DETECTION_ENABLED": "true",
            "MLOPS_EXPLAINABILITY_ENABLED": "true",
            "MLOPS_DRIFT_CHECK_INTERVAL": "3600",
            # Performance features (optimized for production load)
            "MLOPS_ASYNC_BATCH_ENABLED": "true",
            "MLOPS_ANOMALY_BUFFER_ENABLED": "true",
            "MLOPS_ASYNC_BATCH_SIZE": "100",
            "MLOPS_ASYNC_BATCH_TIMEOUT": "2.0",
            "MLOPS_ASYNC_MAX_WORKERS": "10",
            # Security (strict)
            "MLOPS_MAX_REQUEST_TIMEOUT": "30",
            # Model configuration (large cache for performance)
            "MLOPS_PREDICTION_CACHE_MAX_SIZE": "10000",
            "MLOPS_MAX_TEXT_LENGTH": "512",
            "MLOPS_ENABLE_FEATURE_ENGINEERING": "true",
            # Redis configuration (production-optimized)
            "MLOPS_REDIS_MAX_CONNECTIONS": "100",
            "MLOPS_REDIS_PREDICTION_CACHE_TTL": "7200",
            "MLOPS_REDIS_FEATURE_CACHE_TTL": "3600",
            # Kafka configuration
            "MLOPS_KAFKA_CONSUMER_THREADS": "8",
            "MLOPS_KAFKA_BATCH_SIZE": "200",
            "MLOPS_KAFKA_MAX_POLL_RECORDS": "1000",
            # Data Lake configuration
            "MLOPS_DATA_LAKE_BATCH_SIZE": "1000",
            "MLOPS_DATA_LAKE_FLUSH_INTERVAL": "300",
        }


class LocalProfile(ConfigProfile):
    """Local development profile.

    Similar to development but optimized for running locally
    without any external dependencies.
    """

    @property
    def name(self) -> str:
        return "local"

    @property
    def description(self) -> str:
        return "Local development without external dependencies"

    def get_overrides(self) -> Dict[str, Any]:
        """Local-specific configuration overrides."""
        # Start with development defaults
        dev_profile = DevelopmentProfile()
        overrides = dev_profile.get_overrides().copy()

        # Override with local-specific settings
        overrides.update(
            {
                "MLOPS_ENVIRONMENT": "local",
                "MLOPS_HOST": "127.0.0.1",  # Localhost only
                "MLOPS_WORKERS": "1",
                # Ensure all external services are disabled
                "MLOPS_REDIS_ENABLED": "false",
                "MLOPS_KAFKA_ENABLED": "false",
                "MLOPS_VAULT_ENABLED": "false",
                "MLOPS_DATA_LAKE_ENABLED": "false",
                "MLOPS_MLFLOW_ENABLED": "false",
                # Minimal logging for cleaner output
                "MLOPS_LOG_LEVEL": "INFO",
            }
        )

        return overrides


class ProfileRegistry:
    """Registry for managing configuration profiles."""

    _profiles: Dict[str, ConfigProfile] = {
        "local": LocalProfile(),
        "development": DevelopmentProfile(),
        "dev": DevelopmentProfile(),  # Alias
        "staging": StagingProfile(),
        "production": ProductionProfile(),
        "prod": ProductionProfile(),  # Alias
    }

    @classmethod
    def get_profile(cls, profile_name: str) -> Optional[ConfigProfile]:
        """Get a configuration profile by name.

        Args:
            profile_name: Name of the profile (case-insensitive).

        Returns:
            ConfigProfile instance or None if not found.
        """
        return cls._profiles.get(profile_name.lower())

    @classmethod
    def get_available_profiles(cls) -> Dict[str, str]:
        """Get all available profiles with their descriptions.

        Returns:
            Dictionary mapping profile names to descriptions.
        """
        # Get unique profiles (excluding aliases)
        unique_profiles = {}
        seen = set()

        for name, profile in cls._profiles.items():
            if profile.name not in seen:
                unique_profiles[profile.name] = profile.description
                seen.add(profile.name)

        return unique_profiles

    @classmethod
    def register_profile(cls, profile: ConfigProfile) -> None:
        """Register a custom configuration profile.

        Args:
            profile: ConfigProfile instance to register.
        """
        cls._profiles[profile.name.lower()] = profile


def load_profile(profile_name: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration overrides for a specific profile.

    Args:
        profile_name: Name of the profile to load. If None, defaults to 'development'.

    Returns:
        Dictionary of configuration overrides.

    Raises:
        ValueError: If the profile name is not recognized.
    """
    if profile_name is None:
        profile_name = "development"

    profile = ProfileRegistry.get_profile(profile_name)

    if profile is None:
        available = ", ".join(ProfileRegistry.get_available_profiles().keys())
        raise ValueError(f"Unknown profile '{profile_name}'. " f"Available profiles: {available}")

    return profile.get_overrides()


def get_profile_info() -> Dict[str, Dict[str, str]]:
    """Get information about all available profiles.

    Returns:
        Dictionary with profile information including name and description.
    """
    profiles = ProfileRegistry.get_available_profiles()
    return {name: {"name": name, "description": desc} for name, desc in profiles.items()}
