"""
Model Drift Detection for KubeSentiment.

This module provides comprehensive drift detection capabilities:
- Data drift detection (input distribution changes)
- Prediction drift detection (output distribution changes)
- Statistical tests (KS test, Chi-squared, PSI)
- Real-time monitoring with alerts
- Integration with Prometheus metrics
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
import threading

from app.core.logging import get_logger
from app.interfaces.drift_interface import IDriftDetector

try:
    from scipy import stats
    from evidently.metric_preset import DataDriftPreset, DataQualityPreset
    from evidently.report import Report
    from evidently.test_suite import TestSuite
    from evidently.tests import TestNumberOfDriftedColumns
    import pandas as pd

    DRIFT_DETECTION_AVAILABLE = True
except ImportError:
    DRIFT_DETECTION_AVAILABLE = False
    pd = None

logger = get_logger(__name__)


@dataclass
class DriftMetrics:
    """Container for drift detection metrics."""

    timestamp: datetime
    data_drift_detected: bool
    prediction_drift_detected: bool
    drift_score: float
    statistical_tests: Dict[str, Any] = field(default_factory=dict)
    feature_drifts: Dict[str, float] = field(default_factory=dict)


class DriftDetector(IDriftDetector):
    """
    Comprehensive drift detection for sentiment analysis models.

    Features:
    - Population Stability Index (PSI) for drift detection
    - Kolmogorov-Smirnov (KS) test for continuous distributions
    - Chi-squared test for categorical distributions
    - Rolling window for baseline comparison
    - Configurable thresholds and alerting
    - Integration with Prometheus

    Example:
        >>> detector = DriftDetector(window_size=1000, psi_threshold=0.1)
        >>> detector.add_prediction("This is great!", 0.95, "POSITIVE")
        >>> drift_metrics = detector.check_drift()
        >>> if drift_metrics.data_drift_detected:
        ...     logger.warning("Data drift detected!")
    """

    def __init__(
        self,
        window_size: int = 1000,
        psi_threshold: float = 0.1,
        ks_threshold: float = 0.05,
        enabled: bool = True,
        min_samples: int = 100,
    ):
        """
        Initialize drift detector.

        Args:
            window_size: Number of samples to keep in rolling window
            psi_threshold: PSI threshold for drift detection (0.1 = minor, 0.25 = major)
            ks_threshold: KS test p-value threshold
            enabled: Whether drift detection is enabled
            min_samples: Minimum samples before checking drift
        """
        self.enabled = enabled and DRIFT_DETECTION_AVAILABLE

        if not self.enabled:
            if not DRIFT_DETECTION_AVAILABLE:
                logger.warning("Drift detection dependencies not available")
            return

        self.window_size = window_size
        self.psi_threshold = psi_threshold
        self.ks_threshold = ks_threshold
        self.min_samples = min_samples

        # Reference data (baseline)
        self.reference_predictions: deque = deque(maxlen=window_size)
        self.reference_confidences: deque = deque(maxlen=window_size)
        self.reference_text_lengths: deque = deque(maxlen=window_size)

        # Current window
        self.current_predictions: deque = deque(maxlen=window_size)
        self.current_confidences: deque = deque(maxlen=window_size)
        self.current_text_lengths: deque = deque(maxlen=window_size)

        # Drift history
        self.drift_history: List[DriftMetrics] = []
        self.last_drift_check: Optional[datetime] = None

        # Thread safety
        self._lock = threading.Lock()

        # Baseline established flag
        self.baseline_established = False

        logger.info(
            "Drift detector initialized", window_size=window_size, psi_threshold=psi_threshold
        )

    def add_prediction(
        self, text: str, confidence: float, prediction: str, is_reference: bool = False
    ) -> None:
        """
        Add a prediction to the drift detector.

        Args:
            text: Input text
            confidence: Prediction confidence score
            prediction: Predicted label
            is_reference: Whether this is reference (baseline) data
        """
        if not self.enabled:
            return

        with self._lock:
            text_length = len(text)

            if is_reference or not self.baseline_established:
                # Add to reference data
                self.reference_predictions.append(prediction)
                self.reference_confidences.append(confidence)
                self.reference_text_lengths.append(text_length)

                # Check if baseline is established
                if len(self.reference_predictions) >= self.min_samples:
                    self.baseline_established = True
                    logger.info("Drift detection baseline established")
            else:
                # Add to current window
                self.current_predictions.append(prediction)
                self.current_confidences.append(confidence)
                self.current_text_lengths.append(text_length)

    def calculate_psi(self, reference: List[float], current: List[float], bins: int = 10) -> float:
        """
        Calculate Population Stability Index (PSI).

        PSI measures the change between two distributions:
        - PSI < 0.1: No significant change
        - 0.1 <= PSI < 0.25: Minor change
        - PSI >= 0.25: Major change (drift detected)

        Args:
            reference: Reference distribution
            current: Current distribution
            bins: Number of bins for discretization

        Returns:
            PSI score
        """
        if not reference or not current:
            return 0.0

        # Create bins based on reference data
        ref_array = np.array(reference)
        cur_array = np.array(current)

        # Calculate bin edges
        bin_edges = np.percentile(ref_array, np.linspace(0, 100, bins + 1))
        bin_edges = np.unique(bin_edges)  # Remove duplicates

        if len(bin_edges) < 2:
            return 0.0

        # Calculate frequencies
        ref_freq, _ = np.histogram(ref_array, bins=bin_edges)
        cur_freq, _ = np.histogram(cur_array, bins=bin_edges)

        # Convert to percentages
        ref_pct = ref_freq / len(ref_array)
        cur_pct = cur_freq / len(cur_array)

        # Avoid division by zero
        ref_pct = np.where(ref_pct == 0, 0.0001, ref_pct)
        cur_pct = np.where(cur_pct == 0, 0.0001, cur_pct)

        # Calculate PSI
        psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))

        return float(psi)

    def ks_test(self, reference: List[float], current: List[float]) -> Tuple[float, float]:
        """
        Perform Kolmogorov-Smirnov test.

        Args:
            reference: Reference distribution
            current: Current distribution

        Returns:
            Tuple of (statistic, p_value)
        """
        if not reference or not current or not DRIFT_DETECTION_AVAILABLE:
            return 0.0, 1.0

        statistic, p_value = stats.ks_2samp(reference, current)
        return float(statistic), float(p_value)

    def chi_squared_test(self, reference: List[str], current: List[str]) -> Tuple[float, float]:
        """
        Perform Chi-squared test for categorical data.

        Args:
            reference: Reference categories
            current: Current categories

        Returns:
            Tuple of (statistic, p_value)
        """
        if not reference or not current or not DRIFT_DETECTION_AVAILABLE:
            return 0.0, 1.0

        # Get all unique categories
        all_categories = sorted(set(reference + current))

        # Count occurrences
        ref_counts = [reference.count(cat) for cat in all_categories]
        cur_counts = [current.count(cat) for cat in all_categories]

        # Chi-squared test
        try:
            statistic, p_value = stats.chisquare(cur_counts, ref_counts)
            return float(statistic), float(p_value)
        except Exception as e:
            logger.error("Chi-squared test failed", error=str(e), exc_info=True)
            return 0.0, 1.0

    def check_drift(self) -> Optional[DriftMetrics]:
        """
        Check for drift in current window vs reference.

        Returns:
            DriftMetrics object or None if not enough data
        """
        if not self.enabled or not self.baseline_established:
            return None

        with self._lock:
            # Check if we have enough current data
            if len(self.current_predictions) < self.min_samples:
                return None

            # Perform drift tests
            drift_metrics = DriftMetrics(
                timestamp=datetime.utcnow(),
                data_drift_detected=False,
                prediction_drift_detected=False,
                drift_score=0.0,
            )

            # 1. Test confidence score drift (PSI and KS test)
            confidence_psi = self.calculate_psi(
                list(self.reference_confidences), list(self.current_confidences)
            )
            confidence_ks_stat, confidence_ks_p = self.ks_test(
                list(self.reference_confidences), list(self.current_confidences)
            )

            # 2. Test text length drift (PSI and KS test)
            length_psi = self.calculate_psi(
                list(self.reference_text_lengths), list(self.current_text_lengths)
            )
            length_ks_stat, length_ks_p = self.ks_test(
                list(self.reference_text_lengths), list(self.current_text_lengths)
            )

            # 3. Test prediction distribution drift (Chi-squared)
            pred_chi2, pred_chi2_p = self.chi_squared_test(
                list(self.reference_predictions), list(self.current_predictions)
            )

            # Store test results
            drift_metrics.statistical_tests = {
                "confidence_psi": confidence_psi,
                "confidence_ks_statistic": confidence_ks_stat,
                "confidence_ks_pvalue": confidence_ks_p,
                "text_length_psi": length_psi,
                "text_length_ks_statistic": length_ks_stat,
                "text_length_ks_pvalue": length_ks_p,
                "prediction_chi2_statistic": pred_chi2,
                "prediction_chi2_pvalue": pred_chi2_p,
            }

            # Feature-level drift scores
            drift_metrics.feature_drifts = {
                "confidence": confidence_psi,
                "text_length": length_psi,
                "prediction_distribution": pred_chi2_p,
            }

            # Overall drift score (average PSI)
            drift_metrics.drift_score = (confidence_psi + length_psi) / 2

            # Determine if drift detected
            # Data drift: PSI > threshold OR KS test significant
            drift_metrics.data_drift_detected = (
                confidence_psi > self.psi_threshold
                or length_psi > self.psi_threshold
                or confidence_ks_p < self.ks_threshold
                or length_ks_p < self.ks_threshold
            )

            # Prediction drift: Chi-squared test significant
            drift_metrics.prediction_drift_detected = pred_chi2_p < self.ks_threshold

            # Update history
            self.drift_history.append(drift_metrics)
            self.last_drift_check = datetime.utcnow()

            # Log drift detection
            if drift_metrics.data_drift_detected or drift_metrics.prediction_drift_detected:
                logger.warning(
                    "Drift detected",
                    data_drift_detected=drift_metrics.data_drift_detected,
                    prediction_drift_detected=drift_metrics.prediction_drift_detected,
                    drift_score=drift_metrics.drift_score,
                )
            else:
                logger.debug("No drift detected", drift_score=drift_metrics.drift_score)

            return drift_metrics

    def reset_current_window(self) -> None:
        """Reset the current window (e.g., after deploying a new model)."""
        if not self.enabled:
            return

        with self._lock:
            self.current_predictions.clear()
            self.current_confidences.clear()
            self.current_text_lengths.clear()
            logger.info("Current drift window reset")

    def update_baseline(self) -> None:
        """Update baseline with current window data."""
        if not self.enabled:
            return

        with self._lock:
            # Move current data to reference
            self.reference_predictions = self.current_predictions.copy()
            self.reference_confidences = self.current_confidences.copy()
            self.reference_text_lengths = self.current_text_lengths.copy()

            # Clear current window
            self.reset_current_window()

            logger.info("Drift detection baseline updated")

    def get_drift_summary(self) -> Dict[str, Any]:
        """
        Get drift detection summary.

        Returns:
            Dictionary with drift statistics
        """
        if not self.enabled:
            return {"enabled": False}

        with self._lock:
            recent_drifts = [
                d
                for d in self.drift_history
                if d.timestamp > datetime.utcnow() - timedelta(hours=24)
            ]

            return {
                "enabled": True,
                "baseline_established": self.baseline_established,
                "baseline_size": len(self.reference_predictions),
                "current_window_size": len(self.current_predictions),
                "last_check": self.last_drift_check.isoformat() if self.last_drift_check else None,
                "total_drift_checks": len(self.drift_history),
                "drifts_last_24h": len(
                    [
                        d
                        for d in recent_drifts
                        if d.data_drift_detected or d.prediction_drift_detected
                    ]
                ),
                "latest_drift_score": (
                    self.drift_history[-1].drift_score if self.drift_history else 0.0
                ),
                "thresholds": {"psi": self.psi_threshold, "ks_pvalue": self.ks_threshold},
            }

    def export_drift_report(self) -> Optional[str]:
        """
        Export detailed drift report using Evidently.

        Returns:
            HTML report or None if not enough data
        """
        if not self.enabled or not self.baseline_established:
            return None

        if len(self.current_predictions) < self.min_samples:
            return None

        try:
            # Create DataFrames
            reference_df = pd.DataFrame(
                {
                    "confidence": list(self.reference_confidences),
                    "text_length": list(self.reference_text_lengths),
                    "prediction": list(self.reference_predictions),
                }
            )

            current_df = pd.DataFrame(
                {
                    "confidence": list(self.current_confidences),
                    "text_length": list(self.current_text_lengths),
                    "prediction": list(self.current_predictions),
                }
            )

            # Create drift report
            report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])

            report.run(reference_data=reference_df, current_data=current_df)

            # Return HTML
            return report.get_html()
        except Exception as e:
            logger.error("Failed to generate drift report", error=str(e), exc_info=True)
            return None


# Global drift detector instance
_drift_detector_instance: Optional[DriftDetector] = None


def get_drift_detector() -> Optional[DriftDetector]:
    """Get the global drift detector instance."""
    return _drift_detector_instance


def initialize_drift_detector(
    window_size: int = 1000, psi_threshold: float = 0.1, enabled: bool = True
) -> DriftDetector:
    """Initialize the global drift detector instance."""
    global _drift_detector_instance
    _drift_detector_instance = DriftDetector(
        window_size=window_size, psi_threshold=psi_threshold, enabled=enabled
    )
    return _drift_detector_instance
