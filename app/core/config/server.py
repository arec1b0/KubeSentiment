"""Server and application configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings


class ServerConfig(BaseSettings):
    """Server and application-level configuration.

    Attributes:
        app_name: The name of the application.
        app_version: The version of the application.
        debug: A flag to enable or disable debug mode.
        host: The host on which the server will run.
        port: The port on which the server will listen.
        workers: The number of worker processes for the server.
        environment: Deployment environment (dev/staging/prod).
    """

    # Application metadata
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
    environment: str = Field(
        default="production",
        description="Deployment environment (dev/staging/prod)",
    )

    # Server configuration
    host: str = Field(
        default="0.0.0.0",
        description="Server host",
        pattern=r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|localhost|0\.0\.0\.0)$",
    )
    port: int = Field(
        default=8000,
        description="Server port",
        ge=1024,
        le=65535,
    )
    workers: int = Field(
        default=1,
        description="Number of worker processes",
        ge=1,
        le=16,
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
