"""
Request schemas for API endpoints.
"""

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.utils.exceptions import TextEmptyError, TextTooLongError


class TextInput(BaseModel):
    """Input schema for text analysis requests."""

    text: str = Field(
        ...,
        description="Text to analyze for sentiment",
        min_length=1,
        max_length=10000,
        examples=["I love this product! It's amazing."],
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate and clean input text."""
        if not v or not v.strip():
            raise TextEmptyError(context={"text_length": len(v) if v else 0})

        # Check for maximum length
        settings = get_settings()
        max_len = settings.max_text_length

        if len(v.strip()) > max_len:
            raise TextTooLongError(
                text_length=len(v.strip()),
                max_length=max_len,
                context={"raw_length": len(v)},
            )

        return v.strip()

