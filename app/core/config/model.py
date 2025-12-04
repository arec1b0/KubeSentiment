"""ML model configuration settings."""

import os
import re
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from app.utils.exceptions import ModelConfigError


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
        onnx_intra_op_num_threads: Threads for parallelism within ONNX ops.
        onnx_inter_op_num_threads: Threads for parallelism between ONNX ops.
        onnx_execution_mode: ONNX execution mode ('sequential' or 'parallel').
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
    prediction_cache_enabled: bool = Field(
        default=True,
        description="Enable LRU cache for predictions (disable if hit rate <5%)",
    )
    enable_feature_engineering: bool = Field(
        default=False,
        description="Enable advanced feature engineering",
    )

    # ONNX Runtime threading configuration
    # For microservices, single-threaded inference (1) lets Uvicorn workers
    # handle parallelism, typically yielding 2-3x higher total throughput
    onnx_intra_op_num_threads: int = Field(
        default=1,
        description="Threads for parallelism within ops (1 recommended for microservices, 0=auto)",
        ge=0,
    )
    onnx_inter_op_num_threads: int = Field(
        default=1,
        description="Threads for parallelism between ops (1 recommended for microservices, 0=auto)",
        ge=0,
    )
    onnx_execution_mode: str = Field(
        default="sequential",
        description="ONNX execution mode: 'sequential' or 'parallel'",
    )

    @field_validator("onnx_execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        """Validates that execution mode is valid.

        Args:
            v: The execution mode string.

        Returns:
            The validated execution mode (lowercase).

        Raises:
            ValueError: If the execution mode is not valid.
        """
        v = v.lower()
        if v not in ("sequential", "parallel"):
            raise ValueError("onnx_execution_mode must be 'sequential' or 'parallel'")
        return v

    @field_validator("allowed_models")
    @classmethod
    def validate_model_names(cls, v: List[str]) -> List[str]:
        """Validates the format of each model name in the allowed list.

        Args:
            v: The list of allowed model names.

        Returns:
            The validated list of model names.

        Raises:
            ModelConfigError: If a model name has an invalid format or is too long.
        """
        for model_name in v:
            if not re.match(r"^[a-zA-Z0-9/_-]+$", model_name):
                raise ModelConfigError(f"Invalid model name format: {model_name}")
            if len(model_name) > 200:
                raise ModelConfigError(f"Model name too long: {model_name}")
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
            ModelConfigError: If the path is not absolute or the parent directory does not exist.
        """
        if v is not None:
            if not os.path.isabs(v):
                raise ModelConfigError("Cache directory must be an absolute path")
            parent_dir = os.path.dirname(v)
            if not os.path.exists(parent_dir):
                raise ModelConfigError(f"Parent directory does not exist: {parent_dir}")
        return v

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
