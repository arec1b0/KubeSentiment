"""Business logic service exports with lazy loading."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - used only for static analysis
    from app.services.prediction import PredictionService

__all__ = ["PredictionService"]


def __getattr__(name: str) -> Any:
    """Lazily import services to avoid heavyweight dependencies at import time."""

    if name == "PredictionService":
        from app.services.prediction import PredictionService

        return PredictionService
    raise AttributeError(f"module 'app.services' has no attribute {name!r}")
