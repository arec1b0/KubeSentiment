"""
Interface for Drift Detector

Defines the contract for model drift detection services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DriftMetrics:
    """Drift detection metrics"""
    psi_score: float
    ks_statistic: Optional[float]
    chi_squared: Optional[float]
    drift_detected: bool
    confidence_drift: bool
    prediction_drift: bool


class IDriftDetector(ABC):
    """
    Interface for model drift detection services.

    Provides statistical tests to detect data and concept drift.
    """

    @abstractmethod
    def add_prediction(
        self,
        text: str,
        confidence: float,
        prediction: str,
        is_reference: bool = False,
    ) -> None:
        """
        Record a prediction for drift analysis.

        Args:
            text: Input text
            confidence: Prediction confidence score
            prediction: Predicted label
            is_reference: Whether this is reference/baseline data

        Raises:
            ValueError: If inputs are invalid
        """
        pass

    @abstractmethod
    def check_drift(self) -> DriftMetrics:
        """
        Perform drift detection tests.

        Compares current window against baseline using statistical tests.

        Returns:
            DriftMetrics containing test results and drift status

        Raises:
            RuntimeError: If insufficient data for testing
        """
        pass

    @abstractmethod
    def reset_current_window(self) -> None:
        """Reset the current monitoring window."""
        pass

    @abstractmethod
    def update_baseline(self) -> None:
        """Update baseline statistics from current window data."""
        pass

    @abstractmethod
    def get_drift_summary(self) -> Dict[str, Any]:
        """
        Get drift detection summary statistics.

        Returns:
            Dictionary with summary metrics and status
        """
        pass

    @abstractmethod
    def export_drift_report(self, output_path: str) -> str:
        """
        Generate and export drift analysis report.

        Args:
            output_path: Path to save the report

        Returns:
            Path to the generated report file

        Raises:
            RuntimeError: If report generation fails
        """
        pass
