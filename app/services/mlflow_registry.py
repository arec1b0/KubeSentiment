"""
MLflow Model Registry integration for KubeSentiment.

This module provides integration with MLflow Model Registry for:
- Model versioning and lifecycle management
- Model metadata tracking
- A/B testing support
- Canary deployments
- Model performance tracking
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    from mlflow.exceptions import MlflowException
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

logger = logging.getLogger(__name__)


class ModelStage(str, Enum):
    """MLflow model stages."""
    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


class ModelRegistry:
    """
    MLflow Model Registry client for managing sentiment analysis models.

    Features:
    - Register and version models
    - Promote models through stages (None -> Staging -> Production)
    - Track model metadata and performance metrics
    - Support A/B testing with multiple production models
    - Enable canary deployments

    Example:
        >>> registry = ModelRegistry(tracking_uri="http://mlflow:5000")
        >>> model_info = registry.get_production_model("sentiment-model")
        >>> registry.log_prediction_metrics("sentiment-model", version=3, metrics={...})
    """

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        registry_uri: Optional[str] = None,
        experiment_name: str = "sentiment-analysis",
        enabled: bool = True
    ):
        """
        Initialize MLflow Model Registry client.

        Args:
            tracking_uri: MLflow tracking server URI (e.g., "http://mlflow:5000")
            registry_uri: MLflow registry URI (defaults to tracking_uri)
            experiment_name: Name of the MLflow experiment
            enabled: Whether MLflow integration is enabled
        """
        self.enabled = enabled and MLFLOW_AVAILABLE

        if not self.enabled:
            if not MLFLOW_AVAILABLE:
                logger.warning("MLflow not available. Model registry features disabled.")
            else:
                logger.info("MLflow integration disabled by configuration.")
            return

        self.tracking_uri = tracking_uri or "http://localhost:5000"
        self.registry_uri = registry_uri or self.tracking_uri
        self.experiment_name = experiment_name

        # Set MLflow tracking URI
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_registry_uri(self.registry_uri)

        # Initialize client
        self.client = MlflowClient(tracking_uri=self.tracking_uri, registry_uri=self.registry_uri)

        # Create or get experiment
        try:
            self.experiment = mlflow.get_experiment_by_name(experiment_name)
            if self.experiment is None:
                self.experiment_id = mlflow.create_experiment(experiment_name)
            else:
                self.experiment_id = self.experiment.experiment_id
            logger.info(f"MLflow initialized: tracking_uri={self.tracking_uri}, experiment={experiment_name}")
        except Exception as e:
            logger.error(f"Failed to initialize MLflow: {e}")
            self.enabled = False

    def register_model(
        self,
        model_name: str,
        model_uri: str,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Register a new model version in MLflow.

        Args:
            model_name: Name of the model (e.g., "sentiment-distilbert")
            model_uri: URI to the model artifacts
            tags: Optional tags for the model version
            description: Optional description

        Returns:
            Model version info or None if registration failed
        """
        if not self.enabled:
            return None

        try:
            # Register model
            model_version = mlflow.register_model(model_uri, model_name)

            # Add tags if provided
            if tags:
                for key, value in tags.items():
                    self.client.set_model_version_tag(
                        model_name, model_version.version, key, value
                    )

            # Update description
            if description:
                self.client.update_model_version(
                    model_name, model_version.version, description=description
                )

            logger.info(f"Registered model {model_name} version {model_version.version}")

            return {
                "name": model_version.name,
                "version": model_version.version,
                "stage": model_version.current_stage,
                "creation_timestamp": model_version.creation_timestamp
            }
        except MlflowException as e:
            logger.error(f"Failed to register model {model_name}: {e}")
            return None

    def get_model_version(
        self,
        model_name: str,
        version: Optional[int] = None,
        stage: Optional[ModelStage] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific model version or the latest in a stage.

        Args:
            model_name: Name of the model
            version: Specific version number (if None, uses stage)
            stage: Model stage to retrieve (Production, Staging, etc.)

        Returns:
            Model version info or None if not found
        """
        if not self.enabled:
            return None

        try:
            if version is not None:
                # Get specific version
                model_version = self.client.get_model_version(model_name, version)
            elif stage is not None:
                # Get latest version in stage
                versions = self.client.get_latest_versions(model_name, stages=[stage.value])
                if not versions:
                    logger.warning(f"No model found in stage {stage} for {model_name}")
                    return None
                model_version = versions[0]
            else:
                # Get latest version overall
                versions = self.client.search_model_versions(f"name='{model_name}'")
                if not versions:
                    logger.warning(f"No versions found for model {model_name}")
                    return None
                model_version = max(versions, key=lambda v: v.version)

            return {
                "name": model_version.name,
                "version": model_version.version,
                "stage": model_version.current_stage,
                "source": model_version.source,
                "run_id": model_version.run_id,
                "status": model_version.status,
                "creation_timestamp": model_version.creation_timestamp,
                "tags": model_version.tags
            }
        except MlflowException as e:
            logger.error(f"Failed to get model version for {model_name}: {e}")
            return None

    def get_production_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the production model version.

        Args:
            model_name: Name of the model

        Returns:
            Production model info or None if not found
        """
        return self.get_model_version(model_name, stage=ModelStage.PRODUCTION)

    def get_all_production_models(self, model_name: str) -> List[Dict[str, Any]]:
        """
        Get all production model versions (for A/B testing).

        Args:
            model_name: Name of the model

        Returns:
            List of production model versions
        """
        if not self.enabled:
            return []

        try:
            versions = self.client.get_latest_versions(model_name, stages=[ModelStage.PRODUCTION.value])
            return [{
                "name": v.name,
                "version": v.version,
                "stage": v.current_stage,
                "source": v.source,
                "run_id": v.run_id,
                "tags": v.tags
            } for v in versions]
        except MlflowException as e:
            logger.error(f"Failed to get production models for {model_name}: {e}")
            return []

    def transition_model_stage(
        self,
        model_name: str,
        version: int,
        stage: ModelStage,
        archive_existing: bool = False
    ) -> bool:
        """
        Transition a model version to a new stage.

        Args:
            model_name: Name of the model
            version: Version number to transition
            stage: Target stage
            archive_existing: Whether to archive existing models in target stage

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage.value,
                archive_existing_versions=archive_existing
            )
            logger.info(f"Transitioned {model_name} v{version} to {stage.value}")
            return True
        except MlflowException as e:
            logger.error(f"Failed to transition model stage: {e}")
            return False

    def promote_to_production(
        self,
        model_name: str,
        version: int,
        archive_existing: bool = True
    ) -> bool:
        """
        Promote a model version to production.

        Args:
            model_name: Name of the model
            version: Version number to promote
            archive_existing: Whether to archive current production models

        Returns:
            True if successful, False otherwise
        """
        return self.transition_model_stage(
            model_name, version, ModelStage.PRODUCTION, archive_existing
        )

    def log_prediction_metrics(
        self,
        model_name: str,
        version: int,
        metrics: Dict[str, float],
        tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Log prediction metrics for a model version.

        Args:
            model_name: Name of the model
            version: Model version
            metrics: Dictionary of metric names and values
            tags: Optional tags

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Get model version to find run_id
            model_version = self.client.get_model_version(model_name, version)
            run_id = model_version.run_id

            # Log metrics
            with mlflow.start_run(run_id=run_id):
                for metric_name, value in metrics.items():
                    mlflow.log_metric(metric_name, value)

                if tags:
                    mlflow.set_tags(tags)

            logger.debug(f"Logged metrics for {model_name} v{version}: {metrics}")
            return True
        except MlflowException as e:
            logger.error(f"Failed to log metrics: {e}")
            return False

    def delete_model_version(self, model_name: str, version: int) -> bool:
        """
        Delete a specific model version.

        Args:
            model_name: Name of the model
            version: Version number to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            self.client.delete_model_version(model_name, version)
            logger.info(f"Deleted {model_name} version {version}")
            return True
        except MlflowException as e:
            logger.error(f"Failed to delete model version: {e}")
            return False

    def search_models(
        self,
        filter_string: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for registered models.

        Args:
            filter_string: Optional filter (e.g., "name LIKE 'sentiment%'")
            max_results: Maximum number of results

        Returns:
            List of registered models
        """
        if not self.enabled:
            return []

        try:
            models = self.client.search_registered_models(
                filter_string=filter_string,
                max_results=max_results
            )
            return [{
                "name": m.name,
                "creation_timestamp": m.creation_timestamp,
                "last_updated_timestamp": m.last_updated_timestamp,
                "description": m.description,
                "latest_versions": [{
                    "version": v.version,
                    "stage": v.current_stage
                } for v in m.latest_versions]
            } for m in models]
        except MlflowException as e:
            logger.error(f"Failed to search models: {e}")
            return []


# Global registry instance (initialized by settings)
_registry_instance: Optional[ModelRegistry] = None


def get_model_registry() -> Optional[ModelRegistry]:
    """Get the global model registry instance."""
    return _registry_instance


def initialize_model_registry(
    tracking_uri: Optional[str] = None,
    enabled: bool = True
) -> ModelRegistry:
    """Initialize the global model registry instance."""
    global _registry_instance
    _registry_instance = ModelRegistry(tracking_uri=tracking_uri, enabled=enabled)
    return _registry_instance
