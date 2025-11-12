"""ML model configuration settings."""

import os
import re
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ModelConfig(BaseSettings):
    """Machine learning model configuration.

    Attributes:
        model_name: The identifier of the Hugging Face model to be used.
        allowed_models: A list of model names that are permitted for use.
        model_cache_dir: The directory to cache downloaded models.
        onnx_model_path: The path to the ONNX model for optimized inference.
        onnx_model_path_default: The default path for the ONNX model.
        max_text_length: The maximum length of input text.
        prediction_cache_max_size: The maximum number of predictions to cache.
        enable_feature_engineering: Enable advanced feature engineering.
    """

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
        default=None,
        description="Directory to cache downloaded models",
    )
    onnx_model_path: Optional[str] = Field(
        default=None,
        description="Path to ONNX model directory for optimized inference",
    )
    onnx_model_path_default: str = Field(
        default="./onnx_models/distilbert-base-uncased-finetuned-sst-2-english",
        description="Default ONNX model path when onnx_model_path is not set",
    )
    max_text_length: int = Field(
        default=512,
        description="Maximum input text length",
        ge=1,
        le=10000,
    )
    prediction_cache_max_size: int = Field(
        default=1000,
        description="Maximum number of cached predictions",
        ge=10,
        le=100000,
    )
    enable_feature_engineering: bool = Field(
        default=False,
        description="Enable advanced feature engineering",
    )

    @field_validator("allowed_models")
    @classmethod
    def validate_model_names(cls, v: List[str]) -> List[str]:
        """Validates the format of each model name in the allowed list.

        Args:
            v: The list of allowed model names.

        Returns:
            The validated list of model names.

        Raises:
            ValueError: If a model name has an invalid format or is too long.
        """
        for model_name in v:
            if not re.match(r"^[a-zA-Z0-9/_-]+$", model_name):
                raise ValueError(f"Invalid model name format: {model_name}")
            if len(model_name) > 200:
                raise ValueError(f"Model name too long: {model_name}")
        return v

    @field_validator("model_cache_dir")
    @classmethod
    def validate_cache_dir(cls, v: Optional[str]) -> Optional[str]:
        """Validates that the cache directory is an absolute path and its parent exists.

        Args:
            v: The path to the model cache directory.

        Returns:
            The validated cache directory path.

        Raises:
            ValueError: If the path is not absolute or the parent directory does not exist.
        """
        if v is not None:
            if not os.path.isabs(v):
                raise ValueError("Cache directory must be an absolute path")
            parent_dir = os.path.dirname(v)
            if not os.path.exists(parent_dir):
                raise ValueError(f"Parent directory does not exist: {parent_dir}")
        return v

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
