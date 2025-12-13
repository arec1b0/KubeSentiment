# ADR 011: Standardize Concurrency and Serialization

**Status:** Accepted
**Date:** 2025-12-13
**Authors:** KubeSentiment Team
**Supersedes:** N/A

## Context

As KubeSentiment scales to handle high-throughput workloads (as per [ADR 003](003-use-kafka-for-async-processing.md)), we face challenges related to resource management and data exchange:

1.  **Concurrency Management**: Deep learning models (ONNX, PyTorch) are heavy resources. Spawning a new model per request is impossible. Spawning one per thread is memory-prohibitive. We need a strategy to share models safely across concurrent requests (FastAPI/Uvicorn workers).
2.  **Thread Contention**: Python's GIL and the underlying runtime's (ONNX/PyTorch) internal threading can conflict, leading to excessive context switching and degraded performance.
3.  **Data Serialization**: The boundary between the HTTP/Kafka layer and the core model logic was fuzzy. Some methods returned Pydantic models, others raw tuples. This coupled the model core to the API layer.

## Decision

We will implement a **Singleton-based Concurrency Strategy** and **Primitive-based Serialization** for the model layer.

### 1. Singleton Pattern for Model Instances

We will use the Singleton pattern to ensure exactly **one model instance per process**.
-   **Implementation**: A global factory method (e.g., `get_onnx_sentiment_analyzer(path)`) caches instances.
-   **Thread Safety**: The model instance itself must be thread-safe.
    -   **Stateless Inference**: The core `predict` method relies on the underlying runtime (ONNX Runtime is thread-safe).
    -   **Shared State**: Metrics (counters) and Cache (LRU) are shared. We accept the theoretical race condition on metric counters (using Python's `+=`) as a trade-off for avoiding lock overhead in the hot path. `lru_cache` is inherently thread-safe.

### 2. Threading Configuration

We will configure the underlying runtimes to optimize for the FastAPI/Uvicorn execution model:
-   **Intra-op Threads**: Set to `1` (or low value) by default. This forces the heavy lifting to be sequential *within* a single request, allowing the Uvicorn worker pool to handle parallelism via multiple requests. This prevents "thread explosion" where every request spawns multiple computation threads.
-   **Inter-op Threads**: Set to `1`.
-   **Execution Mode**: `ORT_SEQUENTIAL` for ONNX.

### 3. Primitive-based Serialization

The `ModelStrategy` interface will strictly use **Python primitives** (str, dict, list, int/float) for inputs and outputs, rather than Pydantic models or framework-specific objects.
-   **Input**: `text: str`
-   **Output**: `dict[str, Any]` (containing `label`, `score`, `inference_time_ms`)
-   **Rationale**: Decouples the core logic from the API layer. The API layer (FastAPI) is responsible for validation and converting these dicts into Pydantic models for the external response.

## Consequences

### Positive

-   **Resource Efficiency**: Single model instance per process minimizes memory footprint (crucial for GPU memory).
-   **Predictable Performance**: Restricting intra-op threads prevents CPU saturation when many requests arrive simultaneously.
-   **Decoupling**: The model core is independent of the web framework. It can be easily used in CLI tools or offline scripts without needing the full API stack.
-   **Thread Safety**: Explicitly addressing thread safety ensures stability under load.

### Negative

-   **Global State**: Singleton pattern introduces global state, which can make unit testing harder (requires careful setup/teardown or mocking).
    -   *Mitigation*: Use pytest fixtures with `clear_instances()` helper or dependency injection mocks for unit tests.
-   **Metric Accuracy**: Lack of strict locking on metrics means counts might be slightly off under extreme concurrency.
    -   *Note*: This is acceptable for telemetry, but critical business metrics (e.g., billing) should use atomic operations or a database.

### Neutral

-   **Serialization Overhead**: Converting between Dicts and Pydantic models adds a negligible overhead compared to model inference time.

## Implementation Details

### Singleton Factory

```python
_onnx_analyzer_instances = {}

def get_onnx_sentiment_analyzer(model_path: str):
    if model_path not in _onnx_analyzer_instances:
        _onnx_analyzer_instances[model_path] = ONNXSentimentAnalyzer(model_path)
    return _onnx_analyzer_instances[model_path]
```

### Thread Configuration (ONNX)

```python
sess_options.intra_op_num_threads = 1  # Let Uvicorn handle concurrency
sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
```

## Related ADRs

-   [ADR 003: Use Kafka for Async Processing](003-use-kafka-for-async-processing.md) - High-throughput requirements driving the concurrency strategy.
-   [ADR 004: Use FastAPI as Web Framework](004-use-fastapi-as-web-framework.md) - The target runtime environment for these concurrency settings.
-   [ADR 009: Profile-Based Configuration System](009-profile-based-configuration.md) - Defines where thread settings are stored.
