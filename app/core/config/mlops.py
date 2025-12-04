"""MLOps configuration for model lifecycle management."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class MLOpsConfig(BaseSettings):
    """MLOps configuration for model registry, drift detection, and explainability.

    Attributes:
        mlflow_enabled: Enable MLflow model registry integration.
        mlflow_tracking_uri: MLflow tracking server URI.
        mlflow_registry_uri: MLflow registry URI (defaults to tracking URI).
        mlflow_experiment_name: MLflow experiment name.
        mlflow_model_name: Registered model name in MLflow.
        drift_detection_enabled: Enable model drift detection.
        drift_window_size: Number of samples in drift detection window.
        drift_psi_threshold: PSI threshold for drift detection.
        drift_ks_threshold: KS test p-value threshold for drift detection.
        drift_min_samples: Minimum samples before checking drift.
        explainability_enabled: Enable model explainability features.
        explainability_use_attention: Use attention weights for explanations.
        explainability_use_gradients: Use gradient-based explanations (slower).
    """

    # MLflow Model Registry
    mlflow_enabled: bool = Field(
        default=False,
        description="Enable MLflow model registry integration",
    )
    mlflow_tracking_uri: Optional[str] = Field(
        default=None,
        description="MLflow tracking server URI (e.g., http://mlflow:5000)",
    )
    mlflow_registry_uri: Optional[str] = Field(
        default=None,
        description="MLflow registry URI (defaults to tracking URI)",
    )
    mlflow_experiment_name: str = Field(
        default="sentiment-analysis",
        description="MLflow experiment name",
    )
    mlflow_model_name: str = Field(
        default="sentiment-model",
        description="Registered model name in MLflow",
    )

    # Drift Detection
    drift_detection_enabled: bool = Field(
        default=True,
        description="Enable model drift detection",
    )
    drift_window_size: int = Field(
        default=1000,
        description="Number of samples in drift detection window",
        ge=100,
        le=10000,
    )
    drift_psi_threshold: float = Field(
        default=0.1,
        description="PSI threshold for drift detection (0.1=minor, 0.25=major)",
        ge=0.0,
        le=1.0,
    )
    drift_ks_threshold: float = Field(
        default=0.05,
        description="KS test p-value threshold for drift detection",
        ge=0.0,
        le=1.0,
    )
    drift_min_samples: int = Field(
        default=100,
        description="Minimum samples before checking drift",
        ge=10,
        le=1000,
    )

    # Explainability
    explainability_enabled: bool = Field(
        default=True,
        description="Enable model explainability features",
    )
    explainability_use_attention: bool = Field(
        default=True,
        description="Use attention weights for explanations",
    )
    explainability_use_gradients: bool = Field(
        default=False,
        description="Use gradient-based explanations (slower)",
    )

    # Shadow Mode (Dark Launch)
    shadow_mode_enabled: bool = Field(
        default=False,
        description="Enable shadow mode to run a candidate model alongside production",
    )
    shadow_model_name: Optional[str] = Field(
        default=None,
        description="Model name/path for the shadow (candidate) model",
    )
    shadow_model_backend: str = Field(
        default="pytorch",
        description="Backend for the shadow model (pytorch or onnx)",
    )
    shadow_traffic_percentage: float = Field(
        default=10.0,
        description="Percentage of traffic to sample for shadow predictions (0-100)",
        ge=0.0,
        le=100.0,
    )
    shadow_async_dispatch: bool = Field(
        default=True,
        description="Dispatch shadow predictions asynchronously (fire-and-forget)",
    )
    shadow_log_comparisons: bool = Field(
        default=True,
        description="Log comparison results between primary and shadow predictions",
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
