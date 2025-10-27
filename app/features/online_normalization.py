"""
Online Normalization for Streaming Data.

This module implements an online standard scaler using Welford's algorithm,
which allows for the numerically stable computation of a running mean and
variance. This is particularly useful in streaming scenarios where the entire
dataset is not available at once. The scaler supports state persistence to
maintain statistics across application restarts.
"""

import json
from pathlib import Path
from typing import Optional

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


class OnlineStandardScaler:
    """Performs online standardization of features using Welford's algorithm.

    This class maintains running statistics (mean and variance) that are
    updated incrementally as new batches of data arrive. This approach is
    well-suited for streaming data and large datasets, as it does not require
    holding all data in memory. The use of Welford's algorithm ensures
    numerical stability.

    Attributes:
        mean_: The running mean of each feature.
        var_: The running variance of each feature.
        n_samples_seen_: The total number of samples seen so far.
        n_features_: The number of features in the data.
    """

    def __init__(self):
        """Initializes the `OnlineStandardScaler`."""
        self.mean_: Optional[np.ndarray] = None
        self.var_: Optional[np.ndarray] = None
        self.n_samples_seen_: int = 0
        self.n_features_: Optional[int] = None

    def partial_fit(self, X: np.ndarray) -> "OnlineStandardScaler":
        """Updates the running mean and variance with a new batch of data.

        This method implements Welford's algorithm for a numerically stable,
        one-pass computation of mean and variance. It can be called repeatedly
        with new batches of data to update the running statistics.

        Args:
            X: A numpy array of shape `(n_samples, n_features)` containing the
                new batch of data.

        Returns:
            The scaler instance, allowing for method chaining.

        Raises:
            ValueError: If the input array has an inconsistent number of
                features compared to previous batches.
        """
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        n_samples, n_features = X.shape
        if n_samples == 0:
            return self

        if self.mean_ is None:
            self.mean_ = np.zeros(n_features, dtype=np.float64)
            self.var_ = np.zeros(n_features, dtype=np.float64)
            self.n_features_ = n_features
        elif n_features != self.n_features_:
            raise ValueError("Inconsistent number of features")

        for i in range(n_samples):
            self.n_samples_seen_ += 1
            delta = X[i] - self.mean_
            self.mean_ += delta / self.n_samples_seen_
            delta2 = X[i] - self.mean_
            self.var_ += delta * delta2

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Standardizes features using the current running statistics.

        This method scales the input data `X` by subtracting the running mean
        and dividing by the running standard deviation.

        Args:
            X: A numpy array of shape `(n_samples, n_features)` to be
                standardized.

        Returns:
            A standardized numpy array of the same shape as the input.

        Raises:
            ValueError: If the scaler has not been fitted yet or if the input
                data has an incorrect shape.
        """
        if self.mean_ is None or self.var_ is None:
            raise ValueError("Scaler must be fitted before transform")

        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        if X.shape[1] != self.n_features_:
            raise ValueError("Inconsistent number of features")

        std = np.sqrt(self.var_ / max(1, self.n_samples_seen_ - 1))
        std = np.where(std == 0, 1.0, std)

        return (X - self.mean_) / std

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """Fits the scaler to the data and then transforms it.

        This is a convenience method that combines `partial_fit` and
        `transform` in a single call.

        Args:
            X: A numpy array of shape `(n_samples, n_features)`.

        Returns:
            A standardized numpy array of the same shape as the input.
        """
        return self.partial_fit(X).transform(X)

    def save_state(self, path: str) -> None:
        """Saves the scaler's state to a JSON file for persistence.

        This allows the running statistics to be preserved across application
        restarts, which is crucial for stateful streaming applications.

        Args:
            path: The file path where the state will be saved.

        Raises:
            IOError: If the file cannot be written.
        """
        state = {
            "mean": self.mean_.tolist() if self.mean_ is not None else None,
            "var": self.var_.tolist() if self.var_ is not None else None,
            "n_samples_seen": self.n_samples_seen_,
            "n_features": self.n_features_,
            "version": "1.0",
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump(state, f, indent=2)
            logger.info("Scaler state saved", path=path)
        except Exception as e:
            raise IOError(f"Failed to save scaler state: {e}")

    def load_state(self, path: str) -> None:
        """Loads the scaler's state from a JSON file.

        This allows the scaler to resume from a previously saved state,
        maintaining a consistent normalization context across sessions.

        Args:
            path: The file path from which the state will be loaded.

        Raises:
            IOError: If the file cannot be read or contains invalid data.
        """
        if not Path(path).exists():
            logger.info("Scaler state file not found, starting fresh", path=path)
            return
        try:
            with open(path, "r") as f:
                state = json.load(f)
            self.mean_ = np.array(state["mean"]) if state["mean"] else None
            self.var_ = np.array(state["var"]) if state["var"] else None
            self.n_samples_seen_ = state["n_samples_seen"]
            self.n_features_ = state["n_features"]
            logger.info("Scaler state loaded", path=path)
        except (json.JSONDecodeError, KeyError) as e:
            raise IOError(f"Invalid scaler state file: {e}")

    def reset(self) -> None:
        """Resets the scaler to its initial, unfitted state."""
        self.mean_ = None
        self.var_ = None
        self.n_samples_seen_ = 0
        self.n_features_ = None
        logger.info("Scaler state reset")

    def get_stats(self) -> Dict[str, Any]:
        """Returns the current statistics of the scaler.

        This includes the number of samples seen, the number of features, and
        the current mean, variance, and standard deviation.

        Returns:
            A dictionary containing the scaler's statistics.
        """
        std = None
        if self.var_ is not None:
            std = np.sqrt(self.var_ / max(1, self.n_samples_seen_ - 1)).tolist()
        return {
            "n_samples_seen": self.n_samples_seen_,
            "n_features": self.n_features_,
            "mean": self.mean_.tolist() if self.mean_ is not None else None,
            "variance": self.var_.tolist() if self.var_ is not None else None,
            "std": std,
            "is_fitted": self.mean_ is not None,
        }

    def __repr__(self) -> str:
        """Returns a string representation of the scaler's state.

        Returns:
            A string showing the scaler's current state, including whether it
            has been fitted.
        """
        fitted = "fitted" if self.mean_ is not None else "unfitted"
        return (
            f"OnlineStandardScaler("
            f"n_samples_seen={self.n_samples_seen_}, "
            f"n_features={self.n_features_}, "
            f"status='{fitted}')"
        )
