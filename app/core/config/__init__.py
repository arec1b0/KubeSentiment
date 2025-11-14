"""
Configuration management package for KubeSentiment.

This package provides domain-specific configuration classes that are composed
into a root Settings class, replacing the previous monolithic configuration.

Configuration profiles provide environment-specific defaults for development,
staging, and production environments, reducing environment variable sprawl.
"""

from app.core.config.data_lake import DataLakeConfig
from app.core.config.kafka import KafkaConfig
from app.core.config.mlops import MLOpsConfig
from app.core.config.model import ModelConfig
from app.core.config.monitoring import MonitoringConfig
from app.core.config.performance import PerformanceConfig
from app.core.config.profiles import (
    ConfigProfile,
    DevelopmentProfile,
    StagingProfile,
    ProductionProfile,
    LocalProfile,
    ProfileRegistry,
    load_profile,
    get_profile_info,
)
from app.core.config.redis import RedisConfig
from app.core.config.security import SecurityConfig
from app.core.config.server import ServerConfig
from app.core.config.settings import Settings, get_settings
from app.core.config.vault import VaultConfig

__all__ = [
    "Settings",
    "get_settings",
    "ServerConfig",
    "ModelConfig",
    "SecurityConfig",
    "PerformanceConfig",
    "KafkaConfig",
    "RedisConfig",
    "VaultConfig",
    "DataLakeConfig",
    "MonitoringConfig",
    "MLOpsConfig",
    # Profile management
    "ConfigProfile",
    "DevelopmentProfile",
    "StagingProfile",
    "ProductionProfile",
    "LocalProfile",
    "ProfileRegistry",
    "load_profile",
    "get_profile_info",
]
