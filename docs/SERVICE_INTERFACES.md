# Service Interfaces Documentation

## Overview

KubeSentiment now implements a comprehensive interface-based architecture following the Dependency Inversion Principle (DIP). All services implement abstract base class (ABC) interfaces, enabling:

- **Loose Coupling**: Components depend on abstractions, not concrete implementations
- **Easier Testing**: Mock interfaces instead of concrete classes
- **Better Dependency Inversion**: High-level modules don't depend on low-level modules
- **Clearer Contracts**: Explicit method signatures and documentation

## Interface Hierarchy

All interfaces are defined in `app/interfaces/` with the following structure:

```
app/interfaces/
├── __init__.py                      # Central exports
├── prediction_interface.py          # IPredictionService
├── batch_interface.py               # IAsyncBatchService
├── stream_interface.py              # IStreamProcessor
├── cache_interface.py               # ICacheClient
├── kafka_interface.py               # IKafkaConsumer
├── storage_interface.py             # IDataWriter
├── drift_interface.py               # IDriftDetector
├── explainability_interface.py      # IExplainabilityEngine
├── optimization_interface.py        # IGPUBatchOptimizer
├── resilience_interface.py          # ICircuitBreaker, ILoadMetrics
├── registry_interface.py            # IModelRegistry
└── buffer_interface.py              # IAnomalyBuffer
```

## Core Services

### 1. IPredictionService

**Location**: `app/interfaces/prediction_interface.py`
**Implementation**: `app/services/prediction.py::PredictionService`

**Purpose**: Core sentiment prediction service

**Contract**:
```python
def predict(text: str) -> Dict[str, Any]
def predict_batch(texts: List[str]) -> List[Dict[str, Any]]
```

**Usage Example**:
```python
from app.interfaces import IPredictionService
from app.core.dependencies import get_prediction_service

def my_function(prediction_service: IPredictionService):
    result = prediction_service.predict("Great product!")
    # result: {"sentiment": "POSITIVE", "confidence": 0.95, ...}
```

---

### 2. IAsyncBatchService

**Location**: `app/interfaces/batch_interface.py`
**Implementation**: `app/services/async_batch_service.py::AsyncBatchService`

**Purpose**: High-throughput asynchronous batch processing with priority queues

**Key Methods**:
- `async start()` - Start batch processing workers
- `async submit_batch_job()` - Submit texts for batch processing
- `async get_job_status()` - Track job progress
- `async get_job_results()` - Retrieve paginated results
- `async cancel_job()` - Cancel pending jobs

**Priority Levels**: `HIGH`, `MEDIUM`, `LOW`
**Job States**: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `CANCELLED`, `EXPIRED`

---

### 3. IStreamProcessor

**Location**: `app/interfaces/stream_interface.py`
**Implementation**: `app/services/stream_processor.py::StreamProcessor`

**Purpose**: Dynamic batching and stream processing for optimized inference

**Key Methods**:
- `async predict_async()` - Queue single prediction with dynamic batching
- `async predict_async_batch()` - Process pre-formed batch
- `get_stats()` - Get processing statistics

**Features**: Automatic batch aggregation, configurable wait times, online feature normalization

---

### 4. ICacheClient

**Location**: `app/interfaces/cache_interface.py`
**Implementation**: `app/services/redis_cache.py::RedisCacheClient`

**Purpose**: Distributed caching with Redis

**Key Methods**:
```python
def get(key: str, cache_type: CacheType) -> Optional[Any]
def set(key: str, value: Any, cache_type: CacheType, ttl: Optional[int])
def delete(key: str, cache_type: CacheType) -> bool
```

**Cache Types**: `PREDICTION`, `FEATURE`, `MODEL`, `METADATA`

---

## Infrastructure Services

### 5. IKafkaConsumer

**Location**: `app/interfaces/kafka_interface.py`
**Implementation**: `app/services/kafka_consumer.py::HighThroughputKafkaConsumer`

**Purpose**: Multi-threaded Kafka consumer with batching and DLQ support

**Key Methods**:
- `async start()` - Begin consuming messages
- `async stop()` - Graceful shutdown with offset commit
- `get_metrics()` - Consumer performance metrics

---

### 6. IDataWriter

**Location**: `app/interfaces/storage_interface.py`
**Implementation**: `app/services/data_writer.py::DataLakeWriter`

**Purpose**: Stream predictions to cloud storage (S3/GCS/Azure) in Parquet format

**Key Methods**:
- `async write_prediction()` - Queue prediction for writing
- `async flush()` - Force write buffer to storage
- `get_stats()` - Buffer statistics

**Supported Clouds**: AWS S3, Google Cloud Storage, Azure Blob Storage

---

## Monitoring Services

### 7. IDriftDetector

**Location**: `app/interfaces/drift_interface.py`
**Implementation**: `app/services/drift_detection.py::DriftDetector`

**Purpose**: Model drift detection with statistical tests

**Key Methods**:
- `add_prediction()` - Record prediction for analysis
- `check_drift()` - Perform drift tests (PSI, KS, Chi-squared)
- `update_baseline()` - Update reference distribution
- `export_drift_report()` - Generate HTML report

**Statistical Tests**: Population Stability Index (PSI), Kolmogorov-Smirnov, Chi-squared

---

### 8. IExplainabilityEngine

**Location**: `app/interfaces/explainability_interface.py`
**Implementation**: `app/services/explainability.py::ExplainabilityEngine`

**Purpose**: Model explainability and interpretability

**Key Methods**:
- `extract_attention_weights()` - Get transformer attention scores
- `compute_integrated_gradients()` - Gradient-based attribution
- `explain_prediction()` - Comprehensive explanation with visualizations
- `generate_html_explanation()` - HTML visualization

---

## Optimization Services

### 9. IGPUBatchOptimizer

**Location**: `app/interfaces/optimization_interface.py`
**Implementation**: `app/services/gpu_batch_optimizer.py::GPUBatchOptimizer`

**Purpose**: GPU-optimized batch processing with multi-GPU support

**Key Methods**:
- `get_optimal_batch_size()` - Calculate batch size based on GPU memory
- `distribute_batches()` - Split work across GPUs
- `process_batch_parallel()` - Parallel GPU processing
- `get_gpu_stats()` - GPU utilization metrics

**Load Balancing**: Round-robin, least-loaded, utilization-based

---

## Resilience Services

### 10. ICircuitBreaker

**Location**: `app/interfaces/resilience_interface.py`
**Implementation**: `app/services/load_balancer.py::CircuitBreaker`

**Purpose**: Circuit breaker pattern for overload protection

**Key Methods**:
- `call()` - Execute function with circuit protection
- `get_state()` - Get current state (CLOSED/OPEN/HALF_OPEN)
- `reset()` - Manual circuit reset

---

### 11. ILoadMetrics

**Location**: `app/interfaces/resilience_interface.py`
**Implementation**: `app/services/load_balancer.py::LoadBalancingMetrics`

**Purpose**: Instance health monitoring and load shedding

**Key Methods**:
- `get_instance_load()` - Current CPU/memory/request metrics
- `should_accept_request()` - Load shedding decision
- `record_request_start()` / `record_request_end()` - Request tracking
- `get_hpa_metrics()` - Kubernetes HPA-compatible metrics

---

## Model Management

### 12. IModelRegistry

**Location**: `app/interfaces/registry_interface.py`
**Implementation**: `app/services/mlflow_registry.py::ModelRegistry`

**Purpose**: MLflow Model Registry integration

**Key Methods**:
- `register_model()` - Register new model version
- `get_production_model()` - Get production version
- `transition_model_stage()` - Move between stages (None → Staging → Production → Archived)
- `promote_to_production()` - Fast-track promotion
- `log_prediction_metrics()` - Track model metrics

---

### 13. IAnomalyBuffer

**Location**: `app/interfaces/buffer_interface.py`
**Implementation**: `app/services/anomaly_buffer.py::BoundedAnomalyBuffer`

**Purpose**: In-memory bounded buffer for anomaly detection results

**Key Methods**:
- `add()` - Add anomaly entry with automatic eviction
- `get()` - Retrieve by ID
- `get_all()` - Get all non-expired entries
- `cleanup_expired()` - Manual cleanup
- `get_stats()` - Buffer utilization

**Features**: Thread-safe, TTL-based expiration, bounded size with FIFO eviction

---

## Dependency Injection

All services are injected through `app/core/dependencies.py` with interface return types:

```python
from app.interfaces import IPredictionService

def get_prediction_service(...) -> IPredictionService:
    return PredictionService(...)
```

**FastAPI Integration**:
```python
from fastapi import Depends
from app.interfaces import IPredictionService
from app.core.dependencies import get_prediction_service

@app.post("/predict")
async def predict(
    text: str,
    service: IPredictionService = Depends(get_prediction_service)
):
    return service.predict(text)
```

---

## Testing with Interfaces

### Mocking Services

```python
from unittest.mock import Mock
from app.interfaces import IPredictionService

def test_my_function():
    # Mock the interface, not the concrete class
    mock_service = Mock(spec=IPredictionService)
    mock_service.predict.return_value = {
        "sentiment": "POSITIVE",
        "confidence": 0.95
    }

    result = my_function(mock_service)

    assert result is not None
    mock_service.predict.assert_called_once()
```

### Test Fixtures

```python
import pytest
from app.interfaces import IPredictionService

@pytest.fixture
def mock_prediction_service():
    mock = Mock(spec=IPredictionService)
    mock.predict.return_value = {"sentiment": "POSITIVE"}
    return mock

def test_with_fixture(mock_prediction_service: IPredictionService):
    result = mock_prediction_service.predict("test")
    assert result["sentiment"] == "POSITIVE"
```

---

## Benefits

### 1. Loose Coupling
Services depend on interfaces, not implementations. You can swap implementations without changing client code.

### 2. Easier Testing
Mock interfaces instead of complex concrete classes. No need for test doubles with real dependencies.

### 3. Dependency Inversion
High-level modules (API layer) depend on abstractions. Low-level modules (services) implement those abstractions.

### 4. Clearer Contracts
Interface methods have explicit signatures, type hints, and documentation. Easy to understand service capabilities.

### 5. Future Extensibility
Add new implementations without modifying existing code:
```python
class NewPredictionService(IPredictionService):
    def predict(self, text: str) -> Dict[str, Any]:
        # New implementation
        pass
```

---

## Migration Guide

### Before (Concrete Dependencies)
```python
from app.services.prediction import PredictionService

def my_function(service: PredictionService):
    return service.predict("text")
```

### After (Interface Dependencies)
```python
from app.interfaces import IPredictionService

def my_function(service: IPredictionService):
    return service.predict("text")
```

**No breaking changes** - existing code continues to work. Concrete services now implement interfaces.

---

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│         API Layer (FastAPI)             │
│  Depends on: Interfaces (IPrediction*)  │
└───────────────┬─────────────────────────┘
                │ Dependency Injection
                ▼
┌─────────────────────────────────────────┐
│         Service Interfaces              │
│  (IPredictionService, IStreamProcessor) │
└───────────────┬─────────────────────────┘
                │ Implements
                ▼
┌─────────────────────────────────────────┐
│      Concrete Service Implementations   │
│  (PredictionService, StreamProcessor)   │
└───────────────┬─────────────────────────┘
                │ Uses
                ▼
┌─────────────────────────────────────────┐
│    Infrastructure (Models, Cache, DB)   │
└─────────────────────────────────────────┘
```

---

## References

- [SOLID Principles - Dependency Inversion](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Python ABC Documentation](https://docs.python.org/3/library/abc.html)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Testing with Mocks](https://docs.python.org/3/library/unittest.mock.html)

---

**Last Updated**: 2025-11-14
**Version**: 1.0
**Author**: KubeSentiment Team
