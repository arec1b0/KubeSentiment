# ADR 010: Refactor Model Hierarchy for Maintainability

**Status:** Accepted
**Date:** 2025-12-13
**Authors:** KubeSentiment Team
**Supersedes:** N/A

## Context

The KubeSentiment application supports multiple model backends (PyTorch, ONNX) to balance accuracy and performance. As the application evolved, significant code duplication emerged between `ONNXSentimentAnalyzer` and `PyTorchSentimentAnalyzer`:

1.  **Duplicate Logic**: Both classes implemented identical logic for:
    -   Text preprocessing (truncation, cleaning).
    -   Batch processing (iterating, error handling, result aggregation).
    -   Caching (LRU cache management).
    -   Metrics tracking (counting predictions, measuring inference time).
2.  **Inconsistent Interfaces**: Minor differences in method signatures or return values could drift over time.
3.  **Maintenance Burden**: Fixing a bug in preprocessing or updating metrics logic required changes in multiple files.
4.  **Testing Complexity**: Testing common logic required duplicating tests for each backend.

We need a robust architectural pattern that enforces a consistent interface while centralizing shared logic.

## Decision

We will refactor the model layer to use the **Strategy Pattern** with a shared **Base Class** for common functionality.

### Implementation Strategy

1.  **`ModelStrategy` Protocol**: Define a strict `Protocol` that all model backends must implement. This ensures compile-time (or static analysis) enforcement of the interface.
    -   `predict(text: str) -> dict`
    -   `predict_batch(texts: list[str]) -> list[dict]`
    -   `is_ready() -> bool`
    -   `get_model_info() -> dict`
    -   `get_performance_metrics() -> dict`

2.  **`BaseModelMetrics` Class**: Create a base class that implements the shared logic.
    -   **Metrics**: Centralized tracking of `prediction_count`, `inference_time`, `cache_hits/misses`.
    -   **Caching**: A unified `_init_cache` method that wraps internal prediction methods with `lru_cache` based on configuration.
    -   **Preprocessing**: Shared `_preprocess_text` and `_preprocess_batch_texts` methods.
    -   **Batch Utilities**: Helper methods like `_build_batch_results` to handle batch response formatting and error placeholders.

3.  **Composition over Inheritance (Partial)**: While we use inheritance for the shared *utility* logic (`BaseModelMetrics`), the primary architectural definition is the `ModelStrategy` protocol. This allows future backends (e.g., API-based like OpenAI) to implement the protocol without necessarily inheriting from `BaseModelMetrics` if the shared logic doesn't apply.

## Consequences

### Positive

-   **DRY (Don't Repeat Yourself)**: Common logic for caching, metrics, and preprocessing is written once in `base.py`.
-   **Consistent Behavior**: All models now handle edge cases (empty text, truncation) and metrics exactly the same way.
-   **Simplified Backends**: `ONNXSentimentAnalyzer` and `PyTorchSentimentAnalyzer` now focus purely on their specific inference runtime logic.
-   **Centralized Caching**: Cache configuration and invalidation are managed in one place.
-   **Type Safety**: The `ModelStrategy` protocol ensures all backends satisfy the application's contract.

### Negative

-   **Coupling**: Changes to `BaseModelMetrics` affect all subclasses.
-   **Indirection**: Developers must check the base class to understand the full behavior of a model implementation.
-   **Base Class Bloat**: Risk of the base class accumulating unrelated logic over time if strict separation of concerns is not maintained.
-   **LSP Violations**: Potential for Liskov Substitution Principle violations if future models deviate significantly from the shared logic assumptions.

### Neutral

-   **Refactoring Effort**: Required touching core critical paths, necessitating regression testing.

## Implementation Details

### The ModelStrategy Protocol

```python
@runtime_checkable
class ModelStrategy(Protocol):
    def predict(self, text: str) -> dict[str, Any]: ...
    def predict_batch(self, texts: list[str]) -> list[dict[str, Any]]: ...
    # ... other methods
```

### The Base Class

```python
class BaseModelMetrics:
    def __init__(self) -> None:
        self._prediction_count = 0
        self._cache_hits = 0

    def _init_cache(self, method, enabled, size):
        # dynamic lru_cache wrapping
```

## Related ADRs

-   [ADR 001: Use ONNX for Model Optimization](001-use-onnx-for-model-optimization.md)
-   [ADR 004: Use FastAPI as Web Framework](004-use-fastapi-as-web-framework.md) - Model hierarchy designed to support FastAPI dependency injection.
-   [ADR 011: Standardize Concurrency and Serialization](011-standardize-concurrency-serialization.md) - Addresses concurrency concerns that motivated the singleton pattern.
