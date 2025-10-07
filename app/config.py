"""
Configuration management for the MLOps sentiment analysis service.

This module handles all configuration settings, environment variables,
and application parameters in a centralized manner with comprehensive validation.
"""

from typing import Optional, List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import re
import os


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden via environment variables with the prefix 'MLOPS_'.
    For example: MLOPS_MODEL_NAME="custom-model"
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
    workers: int = Field(
        default=1, description="Number of worker processes", ge=1, le=16
    )

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

    @field_validator("allowed_models")
    @classmethod
    def validate_model_names(cls, v):
        """Validate each model name format."""
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
        """Validate cache directory path."""
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
        """Get CORS origins for middleware configuration."""
        return self.allowed_origins

    @field_validator("allowed_origins")
    @classmethod
    def validate_cors_origins(cls, v):
        """Validate CORS origin URLs."""
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
        """Validate API key strength."""
        if v is not None:
            if len(v) < 8:
                raise ValueError("API key must be at least 8 characters")
            # Check for basic complexity
            if not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v):
                raise ValueError("API key must contain both letters and numbers")
        return v

    def _validate_model_in_allowed_list(self) -> None:
        """Ensure model_name is in allowed_models list."""
        if (
            self.model_name
            and self.allowed_models
            and self.model_name not in self.allowed_models
        ):
            raise ValueError(
                f"Model '{self.model_name}' must be in allowed_models list: {self.allowed_models}"
            )

    def _validate_worker_count_consistency(self) -> None:
        """Validate worker count based on debug mode."""
        if self.debug and self.workers > 1:
            raise ValueError("Cannot use multiple workers in debug mode")

    def _validate_cache_memory_usage(self) -> None:
        """Validate cache settings to prevent excessive memory usage."""
        # Rough estimate: each cache entry might be ~1KB per 100 chars
        estimated_memory_mb = (
            self.prediction_cache_max_size * self.max_text_length
        ) / 100000
        if estimated_memory_mb > 1000:  # 1GB limit
            raise ValueError(
                f"Cache configuration may use too much memory (~{estimated_memory_mb:.0f}MB). "
                "Reduce cache_size or max_text_length."
            )

    @model_validator(mode="after")
    def validate_configuration_consistency(self):
        """Validate cross-field configuration consistency."""
        self._validate_model_in_allowed_list()
        self._validate_worker_count_consistency()
        self._validate_cache_memory_usage()
        return self

    class Config:
        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Dependency function to get application settings.

    Returns:
        Settings: The application settings instance
    """
    return settings
