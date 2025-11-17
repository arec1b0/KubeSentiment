"""
Request schemas for API endpoints.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings


class TextInput(BaseModel):
    """Defines the schema for requests containing text to be analyzed.

    This Pydantic model is used to validate the input for the prediction
    endpoints. It ensures that the incoming JSON payload contains a `text`
    field that is a non-empty string and does not exceed the configured
    maximum length.

    Attributes:
        text: The input text to be analyzed.
    """

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
        """Validates and sanitizes the input text.

        This validator checks two main conditions:
        1. The text must not be empty or contain only whitespace.
        2. The text's length must not exceed the `max_text_length` setting.

        It also strips leading and trailing whitespace from the text.

        Args:
            v: The raw input text from the request.

        Returns:
            The validated and stripped text.

        Raises:
            ValueError: If the input text is empty or exceeds the maximum allowed length.
        """
        if not v or not v.strip():
            raise ValueError(
                "The text field is required and cannot be empty or contain only whitespace."
            )

        # Check for maximum length
        settings = get_settings()
        max_len = settings.max_text_length

        if len(v.strip()) > max_len:
            raise ValueError(
                f"Text length {len(v.strip())} exceeds the maximum allowed length of {max_len}."
            )

        return v.strip()


class BatchTextInput(BaseModel):
    """Defines the schema for batch sentiment analysis requests.

    This model accepts multiple texts for batch processing with configurable
    options for performance optimization.

    Attributes:
        texts: List of texts to analyze for sentiment.
        priority: Processing priority (low, medium, high).
        max_batch_size: Maximum batch size for processing (optional).
        timeout_seconds: Maximum time to wait for processing (optional).
    """

    texts: List[str] = Field(
        ...,
        description="List of texts to analyze for sentiment",
        min_length=1,
        max_length=1000,  # Reasonable limit for batch processing
        examples=[["I love this product!", "This is terrible.", "It's okay."]],
    )

    priority: str = Field(
        default="medium",
        description="Processing priority level",
        pattern=r"^(low|medium|high)$",
    )

    max_batch_size: Optional[int] = Field(
        default=None,
        description="Maximum batch size for processing optimization",
        ge=1,
        le=1000,
    )

    timeout_seconds: Optional[int] = Field(
        default=300,  # 5 minutes default
        description="Maximum time to wait for processing completion",
        ge=10,
        le=3600,  # Max 1 hour
    )

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: List[str]) -> List[str]:
        """Validate that all texts are non-empty and within length limits.

        Raises:
            ValueError: If the batch is empty, exceeds maximum size, or contains invalid texts.
        """
        if not v or len(v) == 0:
            raise ValueError("Batch processing request cannot be empty.")

        settings = get_settings()
        max_texts = 1000  # Reasonable batch limit

        if len(v) > max_texts:
            raise ValueError(
                f"Batch size of {len(v)} exceeds the maximum of {max_texts}."
            )

        for i, text in enumerate(v):
            if not text or not text.strip():
                raise ValueError(
                    f"Text at index {i} is empty or contains only whitespace."
                )
            if len(text) > settings.max_text_length:
                raise ValueError(
                    f"Text at index {i} with length {len(text)} exceeds the maximum allowed length of {settings.max_text_length}."
                )

        return v
