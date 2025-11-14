"""
Interface for Model Registry

Defines the contract for MLflow model registry services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class IModelRegistry(ABC):
    """
    Interface for model registry services.

    Provides model versioning, lifecycle management, and deployment tracking.
    """

    @abstractmethod
    def register_model(
        self,
        model_name: str,
        model_uri: str,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register a new model version.

        Args:
            model_name: Name of the model
            model_uri: URI to model artifacts
            tags: Optional tags for the model version
            description: Optional model description

        Returns:
            Dictionary with model version information

        Raises:
            ValueError: If model_name or model_uri is invalid
            RuntimeError: If registration fails
        """
        pass

    @abstractmethod
    def get_model_version(
        self,
        model_name: str,
        version: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve model version information.

        Args:
            model_name: Name of the model
            version: Specific version number (None for latest)
            stage: Model stage filter (None, Staging, Production, Archived)

        Returns:
            Dictionary with model version details

        Raises:
            KeyError: If model or version not found
        """
        pass

    @abstractmethod
    def get_production_model(self, model_name: str) -> Dict[str, Any]:
        """
        Get the current production model version.

        Args:
            model_name: Name of the model

        Returns:
            Production model version information

        Raises:
            KeyError: If no production version exists
        """
        pass

    @abstractmethod
    def transition_model_stage(
        self,
        model_name: str,
        version: str,
        stage: str,
        archive_existing: bool = True,
    ) -> Dict[str, Any]:
        """
        Transition a model version to a new stage.

        Args:
            model_name: Name of the model
            version: Version to transition
            stage: Target stage (None, Staging, Production, Archived)
            archive_existing: Whether to archive existing versions in target stage

        Returns:
            Updated model version information

        Raises:
            ValueError: If stage is invalid
            KeyError: If model or version not found
        """
        pass

    @abstractmethod
    def promote_to_production(
        self, model_name: str, version: str, archive_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Fast-track promotion to production stage.

        Args:
            model_name: Name of the model
            version: Version to promote
            archive_existing: Whether to archive current production version

        Returns:
            Updated model version information

        Raises:
            KeyError: If model or version not found
        """
        pass

    @abstractmethod
    def log_prediction_metrics(
        self,
        model_name: str,
        version: str,
        metrics: Dict[str, float],
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Log prediction metrics for a model version.

        Args:
            model_name: Name of the model
            version: Model version
            metrics: Metrics to log
            tags: Optional tags for the metrics

        Raises:
            KeyError: If model or version not found
        """
        pass

    @abstractmethod
    def delete_model_version(self, model_name: str, version: str) -> None:
        """
        Delete a model version.

        Args:
            model_name: Name of the model
            version: Version to delete

        Raises:
            KeyError: If model or version not found
            ValueError: If trying to delete production version
        """
        pass

    @abstractmethod
    def search_models(
        self, filter_string: Optional[str] = None, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for models matching criteria.

        Args:
            filter_string: MLflow filter string
            max_results: Maximum number of results

        Returns:
            List of model information dictionaries
        """
        pass
