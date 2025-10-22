"""
Request schemas for API endpoints.
"""

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.utils.exceptions import TextEmptyError, TextTooLongError


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
            TextEmptyError: If the input text is empty.
            TextTooLongError: If the input text exceeds the maximum allowed length.
        """
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
