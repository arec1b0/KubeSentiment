"""
Online Normalization for Streaming Data.

This module implements online standardization using Welford's algorithm for numerically
stable computation of running mean and variance. It supports state persistence to maintain
statistics across application restarts, making it suitable for production streaming ML pipelines.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


class OnlineStandardScaler:
    """
    Performs online standardization of features using Welford's algorithm.

    This class maintains running statistics (mean and variance) that can be updated
    incrementally with new batches of data. It uses numerically stable algorithms
    to avoid precision issues with large datasets or streaming scenarios.

    The scaler supports state persistence, allowing it to maintain statistics across
    application restarts. This is crucial for production streaming ML pipelines.

    Attributes:
        mean_: np.ndarray or None
            Running mean of each feature. None until first batch is processed.
        var_: np.ndarray or None
            Running variance of each feature. None until first batch is processed.
        n_samples_seen_: int
            Number of samples seen so far across all batches.
        n_features_: int or None
            Number of features. Determined from first batch.
    """

    def __init__(self):
        """Initialize the online standard scaler."""
        self.mean_: Optional[np.ndarray] = None
        self.var_: Optional[np.ndarray] = None
        self.n_samples_seen_: int = 0
        self.n_features_: Optional[int] = None

    def partial_fit(self, X: np.ndarray) -> "OnlineStandardScaler":
        """
        Update running mean and variance with a new batch of data.

        Uses Welford's algorithm for numerically stable online computation of
        mean and variance. This method can be called repeatedly with new batches
        of data to update the running statistics.

        Args:
            X: Input array of shape (n_samples, n_features).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If input array has inconsistent number of features.
        """
        X = np.asarray(X)

        if X.ndim == 1:
            X = X.reshape(-1, 1)
        elif X.ndim != 2:
            raise ValueError(f"Input must be 1D or 2D array, got {X.ndim}D")

        n_samples, n_features = X.shape

        if n_samples == 0:
            return self

        # Initialize on first batch
        if self.mean_ is None:
            self.mean_ = np.zeros(n_features, dtype=np.float64)
            self.var_ = np.zeros(n_features, dtype=np.float64)
            self.n_features_ = n_features
        elif n_features != self.n_features_:
            raise ValueError(
                f"Number of features {n_features} does not match "
                f"previous batches ({self.n_features_})"
            )

        # Welford's algorithm for online mean and variance
        for i in range(n_samples):
            self.n_samples_seen_ += 1

            # Update mean
            delta = X[i] - self.mean_
            self.mean_ += delta / self.n_samples_seen_

            # Update variance
            delta2 = X[i] - self.mean_
            self.var_ += delta * delta2

        logger.debug(
            "Updated scaler statistics",
            n_samples_processed=n_samples,
            total_samples_seen=self.n_samples_seen_,
            n_features=n_features,
        )

        return self

    def transform(self, X: np.ndarray):
        """
        Standardize features using current running statistics.

        Args:
            X: Input array of shape (n_samples, n_features).

        Returns:
            Standardized array of same shape as input.

        Raises:
            ValueError: If scaler has not been fitted or input shape is invalid.
        """
        if self.mean_ is None or self.var_ is None:
            raise ValueError("Scaler must be fitted before transform")

        X = np.asarray(X)

        if X.ndim == 1:
            X = X.reshape(-1, 1)
        elif X.ndim != 2:
            raise ValueError(f"Input must be 1D or 2D array, got {X.ndim}D")

        n_samples, n_features = X.shape

        if n_features != self.n_features_:
            raise ValueError(
                f"Number of features {n_features} does not match "
                f"fitted features ({self.n_features_})"
            )

        # Avoid division by zero for features with zero variance
        std = np.sqrt(self.var_ / max(1, self.n_samples_seen_ - 1))
        std = np.where(std == 0, 1.0, std)  # Replace zero std with 1 to avoid NaN

        # Standardize: (X - mean) / std
        X_scaled = (X - self.mean_) / std

        logger.debug(
            "Transformed features",
            input_shape=X.shape,
            output_shape=X_scaled.shape,
            mean_range=(float(self.mean_.min()), float(self.mean_.max())),
            std_range=(float(std.min()), float(std.max())),
        )

        return X_scaled

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """
        Fit the scaler and transform the data in one step.

        Args:
            X: Input array of shape (n_samples, n_features).

        Returns:
            Standardized array of same shape as input.
        """
        return self.partial_fit(X).transform(X)

    def save_state(self, path: str) -> None:
        """
        Save scaler state to a JSON file for persistence.

        Args:
            path: File path where state will be saved.

        Raises:
            IOError: If file cannot be written.
        """
        state = {
            "mean": self.mean_.tolist() if self.mean_ is not None else None,
            "var": self.var_.tolist() if self.var_ is not None else None,
            "n_samples_seen": self.n_samples_seen_,
            "n_features": self.n_features_,
            "version": "1.0",
        }

        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "w") as f:
                json.dump(state, f, indent=2)

            logger.info(
                "Scaler state saved",
                path=str(path),
                n_samples_seen=self.n_samples_seen_,
                n_features=self.n_features_,
            )

        except Exception as e:
            logger.error("Failed to save scaler state", error=str(e), path=str(path))
            raise IOError(f"Failed to save scaler state: {e}")

    def load_state(self, path: str) -> None:
        """
        Load scaler state from a JSON file.

        Args:
            path: File path from where state will be loaded.

        Raises:
            IOError: If file cannot be read or contains invalid data.
            FileNotFoundError: If state file does not exist.
        """
        path_obj = Path(path)

        if not path_obj.exists():
            logger.info("Scaler state file does not exist, starting fresh", path=str(path))
            return

        try:
            with open(path, "r") as f:
                state = json.load(f)

            # Validate version compatibility
            version = state.get("version", "1.0")
            if version != "1.0":
                logger.warning("Scaler state version mismatch", loaded_version=version)

            # Load state
            self.mean_ = np.array(state["mean"]) if state["mean"] is not None else None
            self.var_ = np.array(state["var"]) if state["var"] is not None else None
            self.n_samples_seen_ = state["n_samples_seen"]
            self.n_features_ = state["n_features"]

            logger.info(
                "Scaler state loaded",
                path=str(path),
                n_samples_seen=self.n_samples_seen_,
                n_features=self.n_features_,
            )

        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in scaler state file", error=str(e), path=str(path))
            raise IOError(f"Invalid JSON in scaler state file: {e}")
        except KeyError as e:
            logger.error("Missing required key in scaler state", missing_key=str(e), path=str(path))
            raise IOError(f"Missing required key in scaler state: {e}")
        except Exception as e:
            logger.error("Failed to load scaler state", error=str(e), path=str(path))
            raise IOError(f"Failed to load scaler state: {e}")

    def reset(self) -> None:
        """Reset the scaler to its initial state."""
        self.mean_ = None
        self.var_ = None
        self.n_samples_seen_ = 0
        self.n_features_ = None
        logger.info("Scaler state reset")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current statistics of the scaler.

        Returns:
            Dictionary containing scaler statistics.
        """
        return {
            "n_samples_seen": self.n_samples_seen_,
            "n_features": self.n_features_,
            "mean": self.mean_.tolist() if self.mean_ is not None else None,
            "variance": self.var_.tolist() if self.var_ is not None else None,
            "std": (
                np.sqrt(self.var_ / max(1, self.n_samples_seen_ - 1)).tolist()
                if self.var_ is not None
                else None
            ),
            "is_fitted": self.mean_ is not None,
        }

    def __repr__(self) -> str:
        """String representation of the scaler."""
        fitted = "fitted" if self.mean_ is not None else "unfitted"
        return (
            f"OnlineStandardScaler("
            f"n_samples_seen={self.n_samples_seen_}, "
            f"n_features={self.n_features_}, "
            f"{fitted})"
        )
