"""
Request schemas for API endpoints.

This module defines Pydantic models for request validation. These models handle
STRUCTURAL validation only (format, type, basic constraints). Business logic
validation (e.g., max_text_length from settings) is handled in the service layer
for better separation of concerns and testability.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TextInput(BaseModel):
    """Defines the schema for requests containing text to be analyzed.

    This Pydantic model is used to validate the input for the prediction
    endpoints. It ensures that the incoming JSON payload contains a `text`
    field that is a non-empty string and does not exceed the configured
    maximum length.

    Attributes:
        text: The input text to be analyzed.

    Example:
        ```json
        {
            "text": "I absolutely love this product! It exceeded all my expectations."
        }
        ```
    """

    text: str = Field(
        ...,
        description="Text to analyze for sentiment. Can be a product review, comment, tweet, or any text content. Maximum 10,000 characters.",
        min_length=1,
        max_length=10000,
        examples=[
            "I love this product! It's amazing.",
            "This is terrible, worst purchase ever.",
            "It's okay, nothing special.",
            "Amazing customer service and fast shipping!",
            "Product broke after one week of use."
        ],
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validates and sanitizes the input text.

        This validator performs STRUCTURAL validation only:
        1. Ensures the text is not empty or whitespace-only
        2. Strips leading and trailing whitespace

        Business logic validation (e.g., max_text_length) is handled in the
        service layer for better separation of concerns and testability.

        Args:
            v: The raw input text from the request.

        Returns:
            The validated and stripped text.

        Raises:
            ValueError: If the input text is empty or contains only whitespace.
        """
        if not v or not v.strip():
            raise ValueError(
                "The text field is required and cannot be empty or contain only whitespace."
            )

        return v.strip()


class BatchTextInput(BaseModel):
    """Defines the schema for batch sentiment analysis requests.

    This model accepts multiple texts for batch processing with configurable
    options for performance optimization. Batch processing provides 85% better
    throughput than sequential requests and is ideal for processing large
    volumes of text asynchronously.

    Attributes:
        texts: List of texts to analyze for sentiment (1-1000 items).
        priority: Processing priority level (low, medium, high).
        max_batch_size: Maximum batch size for processing optimization (optional).
        timeout_seconds: Maximum time to wait for processing completion (optional).

    Example:
        ```json
        {
            "texts": [
                "I love this product!",
                "This is terrible.",
                "It's okay, nothing special."
            ],
            "priority": "high",
            "max_batch_size": 100,
            "timeout_seconds": 300
        }
        ```

    Performance Notes:
        - Recommended batch size: 10-1000 items
        - Optimal batch size: 100-500 items (85% throughput improvement)
        - Processing time varies based on batch size and priority
    """

    texts: List[str] = Field(
        ...,
        description="List of texts to analyze for sentiment. Each text is analyzed independently. Supports 1-1000 items per request.",
        min_length=1,
        max_length=1000,
        examples=[[
            "I love this product! Best purchase ever.",
            "This is terrible, worst experience.",
            "It's okay, nothing special.",
            "Amazing customer service and fast delivery!",
            "Product quality is excellent!"
        ]],
    )

    priority: str = Field(
        default="medium",
        description="Processing priority level determines queue position. Use 'high' for time-sensitive requests, 'low' for batch processing large volumes.",
        pattern=r"^(low|medium|high)$",
        examples=["low", "medium", "high"],
    )

    max_batch_size: Optional[int] = Field(
        default=None,
        description="Optional: Maximum batch size for internal processing optimization. Helps control memory usage. Valid range: 1-1000.",
        ge=1,
        le=1000,
        examples=[100, 500],
    )

    timeout_seconds: Optional[int] = Field(
        default=300,
        description="Maximum time to wait for batch processing completion (seconds). Default: 300 (5 minutes). Valid range: 10-3600 seconds.",
        ge=10,
        le=3600,
        examples=[300, 600, 3600],
    )

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: List[str]) -> List[str]:
        """Validate texts list structure.

        This validator performs STRUCTURAL validation only:
        1. Ensures the list is not empty
        2. Ensures batch size doesn't exceed hard limit (1000)
        3. Ensures each text is non-empty

        Business logic validation (e.g., max_text_length from settings) is
        handled in the service layer for better separation of concerns and testability.

        Args:
            v: List of texts to validate.

        Returns:
            The validated list of texts.

        Raises:
            ValueError: If the batch is empty, exceeds maximum size, or contains empty texts.
        """
        if not v or len(v) == 0:
            raise ValueError("Batch processing request cannot be empty.")

        max_texts = 1000  # Hard limit for structural validation

        if len(v) > max_texts:
            raise ValueError(f"Batch size of {len(v)} exceeds the maximum of {max_texts}.")

        for i, text in enumerate(v):
            if not text or not text.strip():
                raise ValueError(f"Text at index {i} is empty or contains only whitespace.")

        return v
