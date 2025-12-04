"""Security configuration settings."""

import os
import re
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from app.utils.exceptions import SecurityConfigError


class SecurityConfig(BaseSettings):
    """Security and authentication configuration.

    Attributes:
        api_key: The API key for securing application endpoints.
        allowed_origins: A list of allowed origins for CORS.
        max_request_timeout: The maximum request timeout in seconds.
    """

    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication",
        min_length=8 if os.getenv("MLOPS_API_KEY") else None,
    )
    allowed_origins: List[str] = Field(
        default_factory=lambda: [
            "https://example.com",
            "https://another-example.com",
        ],
        description="List of allowed origins for CORS",
    )
    max_request_timeout: int = Field(
        default=30,
        description="Maximum request timeout in seconds",
        ge=1,
        le=300,
    )

    @property
    def cors_origins(self) -> List[str]:
        """Provides the list of CORS origins for middleware configuration.

        Returns:
            A list of strings representing the allowed origins for CORS.
        """
        return self.allowed_origins

    @field_validator("allowed_origins")
    @classmethod
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        """Validates the format of CORS origin URLs and disallows wildcards.

        Args:
            v: The list of CORS origins.

        Returns:
            The validated list of CORS origins.

        Raises:
            SecurityConfigError: If a wildcard origin is used or a URL is invalid.
        """
        for origin in v:
            if origin == "*":
                raise SecurityConfigError(
                    "Wildcard CORS origin '*' is not allowed. "
                    "Specify explicit origins for security."
                )
            url_pattern = re.compile(r"^https?://[a-zA-Z0-9.-]+(?:\:[0-9]+)?(?:/.*)?$")
            if not url_pattern.match(origin):
                raise SecurityConfigError(f"Invalid CORS origin URL: {origin}")
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Validates the strength of the API key.

        Args:
            v: The API key.

        Returns:
            The validated API key.

        Raises:
            SecurityConfigError: If the API key is not strong enough.
        """
        if v is not None:
            if len(v) < 8:
                raise SecurityConfigError("API key must be at least 8 characters")
            if not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v):
                raise SecurityConfigError("API key must contain both letters and numbers")
        return v

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
