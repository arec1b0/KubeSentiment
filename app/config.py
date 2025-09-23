"""
Configuration management for the MLOps sentiment analysis service.

This module handles all configuration settings, environment variables,
and application parameters in a centralized manner.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden via environment variables with the prefix 'MLOPS_'.
    For example: MLOPS_MODEL_NAME="custom-model"
    """

    # Application settings
    app_name: str = Field(
        default="ML Model Serving API", description="Application name"
    )
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")

    # Model settings
    model_name: str = Field(
        default="distilbert-base-uncased-finetuned-sst-2-english",
        description="Hugging Face model identifier",
    )
    allowed_models: list[str] = Field(
        default_factory=lambda: [
            "distilbert-base-uncased-finetuned-sst-2-english",
            "cardiffnlp/twitter-roberta-base-sentiment-latest",
            "nlptown/bert-base-multilingual-uncased-sentiment",
            "j-hartmann/emotion-english-distilroberta-base",
        ],
        description="List of allowed model names for security",
    )
    model_cache_dir: Optional[str] = Field(
        default=None, description="Directory to cache downloaded models"
    )

    # Performance settings
    max_request_timeout: int = Field(
        default=30, description="Maximum request timeout in seconds"
    )
    max_text_length: int = Field(default=512, description="Maximum input text length")

    # Monitoring settings
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    log_level: str = Field(default="INFO", description="Logging level")
    metrics_cache_ttl: int = Field(
        default=5, description="Seconds to cache generated Prometheus metrics"
    )

    # Security settings
    api_key: Optional[str] = Field(
        default=None, description="API key for authentication"
    )

    # Explicit CORS origins configuration
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "https://example.com",
            "https://another-example.com",
        ],
        description="List of allowed origins for CORS",
    )

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
