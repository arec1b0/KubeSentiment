# MLOps Sentiment Analysis - Modular Architecture

## Overview

This document describes the refactored modular architecture of the MLOps sentiment analysis service. The new architecture follows domain-driven design principles, separation of concerns, and MLOps best practices.

## Architecture Principles

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Domain-Driven Design**: Organized by business domain (API, models, services, monitoring)
3. **Dependency Injection**: Loose coupling through dependency injection
4. **Factory Pattern**: Flexible model instantiation with the Factory pattern
5. **Service Layer**: Business logic separated from API and model layers
6. **Testability**: Each module can be tested independently

## Directory Structure

```
app/
├── core/                       # Core application components
│   ├── __init__.py
│   ├── config.py               # Configuration management (Pydantic Settings)
│   ├── logging.py              # Structured logging with correlation IDs
│   ├── dependencies.py         # Dependency injection for FastAPI
│   └── events.py               # Application lifecycle events
│
├── api/                        # API layer
│   ├── __init__.py
│   ├── routes/                 # Route handlers (endpoints)
│   │   ├── __init__.py
│   │   ├── health.py           # Health check endpoints
│   │   ├── predictions.py     # Prediction endpoints
│   │   ├── metrics.py          # Metrics endpoints
│   │   └── model_info.py       # Model information endpoints
│   ├── middleware/             # API middleware
│   │   ├── __init__.py
│   │   ├── correlation.py      # Correlation ID middleware
│   │   ├── auth.py             # API key authentication
│   │   ├── logging.py          # Request logging
│   │   └── metrics.py          # Metrics collection
│   └── schemas/                # Pydantic request/response schemas
│       ├── __init__.py
│       ├── requests.py         # Request schemas
│       └── responses.py        # Response schemas
│
├── models/                     # ML models
│   ├── __init__.py
│   ├── base.py                 # Base model interface (Protocol/ABC)
│   ├── pytorch_sentiment.py   # PyTorch implementation
│   ├── onnx_sentiment.py       # ONNX implementation
│   └── factory.py              # Model factory
│
├── services/                   # Business logic
│   ├── __init__.py
│   └── prediction.py           # Prediction service
│
├── monitoring/                 # Monitoring and observability
│   ├── __init__.py
│   ├── prometheus.py           # Prometheus metrics
│   └── health.py               # Health checking utilities
│
├── utils/                      # Utilities
│   ├── __init__.py
│   ├── exceptions.py           # Custom exceptions
│   ├── error_codes.py          # Error code definitions
│   └── error_handlers.py       # Error handling utilities
│
└── main.py                     # Application factory and entrypoint
```

## Module Descriptions

### Core Module (`app/core/`)

The core module contains fundamental application components:

- **config.py**: Centralized configuration management using Pydantic Settings with environment variable support
- **logging.py**: Structured logging setup with correlation IDs for distributed tracing
- **dependencies.py**: Dependency injection functions for FastAPI endpoints
- **events.py**: Application lifecycle management (startup/shutdown)

**Key Features:**

- Environment-specific configuration
- Structured JSON logging
- Correlation ID propagation
- Clean dependency injection

### API Module (`app/api/`)

The API module handles all HTTP request/response logic:

#### Routes (`app/api/routes/`)

- **health.py**: Health check and readiness probe endpoints
- **predictions.py**: Sentiment prediction endpoints
- **metrics.py**: Prometheus and JSON metrics endpoints
- **model_info.py**: Model information endpoints

#### Middleware (`app/api/middleware/`)

- **correlation.py**: Adds correlation IDs to all requests
- **auth.py**: API key authentication
- **logging.py**: Request/response logging
- **metrics.py**: Automatic metrics collection

#### Schemas (`app/api/schemas/`)

- **requests.py**: Pydantic request models with validation
- **responses.py**: Pydantic response models

**Key Features:**

- Modular route organization
- Reusable middleware components
- Type-safe request/response schemas
- Automatic input validation

### Models Module (`app/models/`)

The models module contains all ML model implementations:

- **base.py**: Model interface (Protocol) defining the contract
- **pytorch_sentiment.py**: PyTorch-based sentiment analyzer
- **onnx_sentiment.py**: ONNX Runtime-based sentiment analyzer
- **factory.py**: Factory pattern for model instantiation

**Key Features:**

- Strategy pattern for model interchangeability
- Factory pattern for flexible model creation
- LRU caching for predictions
- Support for multiple backends (PyTorch, ONNX)

**Factory Pattern Usage:**

```python
from app.models.factory import ModelFactory

# Create a model
model = ModelFactory.create_model("pytorch")
# or
model = ModelFactory.create_model("onnx")
```

### Services Module (`app/services/`)

The services module encapsulates business logic:

- **prediction.py**: Prediction service coordinating between models and API

**Key Features:**

- Business logic separation
- Service layer pattern
- Coordination between models and API
- Independent testability

**Service Layer Benefits:**

- Decouples API from model implementation
- Provides a place for business rules
- Easier to test business logic
- Reusable across different interfaces (REST, gRPC, CLI)

### Monitoring Module (`app/monitoring/`)

The monitoring module provides observability:

- **prometheus.py**: Prometheus metrics collection and export
- **health.py**: Health checking utilities for models and system

**Metrics Collected:**

- Request counts and durations
- Model inference times
- Prediction confidence scores
- System resource usage
- Model availability status

### Utils Module (`app/utils/`)

The utils module contains shared utilities:

- **exceptions.py**: Custom exception hierarchy
- **error_codes.py**: Standardized error codes
- **error_handlers.py**: Error handling utilities

**Custom Exception Hierarchy:**

```
ServiceError (base)
├── ValidationError
│   ├── TextEmptyError
│   └── TextTooLongError
├── ModelError
│   ├── ModelNotLoadedError
│   └── ModelInferenceError
├── AuthenticationError
├── NotFoundError
└── ServiceUnavailableError
```

## Data Flow

### Prediction Request Flow

```
1. HTTP Request → Correlation Middleware
   ↓
2. Correlation Middleware → Request Logging Middleware
   ↓
3. Request Logging → Auth Middleware
   ↓
4. Auth Middleware → Metrics Middleware
   ↓
5. Metrics Middleware → API Route Handler
   ↓
6. Route Handler → Prediction Service
   ↓
7. Prediction Service → Model (via Factory)
   ↓
8. Model → Inference + Caching
   ↓
9. Response ← API Route Handler
   ↓
10. Response Headers Added (correlation ID, inference time)
```

### Dependency Injection Flow

```
Route Handler
   ↓ depends on
Prediction Service
   ↓ depends on
Model Instance (from Factory)
   ↓ depends on
Settings (from Config)
```

## Design Patterns Used

### 1. Factory Pattern

**Location**: `app/models/factory.py`
**Purpose**: Create model instances based on backend type
**Benefits**:

- Encapsulates model creation logic
- Easy to add new model backends
- Centralized model instantiation

### 2. Strategy Pattern

**Location**: `app/models/base.py`
**Purpose**: Define interchangeable model interfaces
**Benefits**:

- Models can be swapped at runtime
- Uniform interface for different backends
- Testability with mock strategies

### 3. Dependency Injection

**Location**: `app/core/dependencies.py`
**Purpose**: Provide dependencies to FastAPI routes
**Benefits**:

- Loose coupling
- Easy testing with dependency overrides
- Clear dependency graphs

### 4. Service Layer Pattern

**Location**: `app/services/`
**Purpose**: Encapsulate business logic
**Benefits**:

- Separates business logic from API
- Reusable across interfaces
- Independently testable

### 5. Middleware Chain

**Location**: `app/api/middleware/`
**Purpose**: Process requests through layers
**Benefits**:

- Cross-cutting concerns (logging, auth, metrics)
- Reusable components
- Clear separation of concerns

## Configuration Management

Configuration is centralized in `app/core/config.py` using Pydantic Settings:

```python
from app.core.config import get_settings

settings = get_settings()
```

**Environment Variables:**

- Prefix: `MLOPS_`
- Example: `MLOPS_MODEL_NAME`, `MLOPS_DEBUG`

**Configuration Features:**

- Type validation
- Default values
- Environment-specific overrides
- Cross-field validation

## Logging and Observability

### Structured Logging

- Format: JSON
- Correlation IDs: Automatically added to all logs
- Context: Service, version, component information

### Metrics

- Format: Prometheus
- Endpoint: `/metrics`
- Auto-collection: Via middleware

### Health Checks

- Liveness: `/health`
- Readiness: `/ready`
- Model status included

## Testing Strategy

### Unit Tests

- Test individual functions/methods
- Mock dependencies
- Fast execution

### Integration Tests

- Test module interactions
- Use test doubles for external services
- Database and model fixtures

### API Tests

- Test endpoints end-to-end
- Use FastAPI TestClient
- Override dependencies for testing

**Example Test Structure:**

```python
# Test with dependency override
from app.core.dependencies import get_model_service

def mock_model_service():
    return MockModel()

app.dependency_overrides[get_model_service] = mock_model_service
```

## Migration from Old Structure

### Old Structure Issues

1. Multiple API files (api.py, api_onnx.py, unified_api.py)
2. Scattered middleware
3. No clear separation of concerns
4. Difficult to test
5. Tight coupling between layers

### New Structure Benefits

1. Single, unified API
2. Organized middleware
3. Clear module boundaries
4. Easy to test independently
5. Loose coupling via dependency injection

### Migration Path

1. ✅ Core module created
2. ✅ API module with routes, middleware, schemas
3. ✅ Models module with factory
4. ✅ Services module for business logic
5. ✅ Monitoring module organized
6. ✅ Utils module consolidated
7. ✅ Updated main.py

## Best Practices

### Adding New Features

**New API Endpoint:**

1. Create schema in `app/api/schemas/`
2. Create route in `app/api/routes/`
3. Add business logic to service if needed
4. Update tests

**New Model Backend:**

1. Implement model interface in `app/models/`
2. Add to factory in `app/models/factory.py`
3. Update configuration if needed
4. Add tests

**New Middleware:**

1. Create in `app/api/middleware/`
2. Add to `app/main.py`
3. Test middleware independently

### Code Style

- Use type hints everywhere
- Follow PEP 8 with Black formatter
- Use Ruff for linting
- Write docstrings for all public functions
- Keep functions focused (single responsibility)

### Error Handling

- Use custom exceptions from `app/utils/exceptions.py`
- Add error codes for client errors
- Log errors with context
- Return structured error responses

## Performance Considerations

### Caching

- Prediction results cached with LRU eviction
- Configurable cache size
- Blake2b hashing for cache keys

### Model Loading

- Models loaded once at startup
- Singleton pattern via `lru_cache`
- Lazy loading supported

### Async Operations

- FastAPI async handlers
- Non-blocking I/O where possible
- Proper resource cleanup

## Security

### Authentication

- API key authentication middleware
- Configurable exempt paths
- Constant-time comparison

### Input Validation

- Pydantic schema validation
- Max text length enforcement
- Model name whitelist

### CORS

- Explicit origin list (no wildcards)
- Configurable per environment

## Monitoring and Alerting

### Metrics to Monitor

- Request rate and latency
- Model inference time
- Prediction confidence distribution
- Error rates
- System resources (CPU, memory)
- Cache hit ratio

### Alerting Rules

- Model unavailability
- High error rate
- Slow inference time
- Resource exhaustion

## Deployment

### Docker

```bash
docker build -t sentiment-api:latest .
docker run -p 8000:8000 sentiment-api:latest
```

### Kubernetes

- Use Helm charts in `helm/`
- Configure via values files
- Health probes configured
- Horizontal Pod Autoscaler enabled

### Environment Variables

```bash
export MLOPS_MODEL_NAME="distilbert-base-uncased-finetuned-sst-2-english"
export MLOPS_DEBUG=false
export MLOPS_LOG_LEVEL=INFO
```

## Future Enhancements

1. **Model Registry Integration**: Connect to MLflow Model Registry
2. **A/B Testing**: Support multiple model versions simultaneously
3. **Batch Predictions**: Endpoint for batch inference
4. **Model Monitoring**: Drift detection and performance tracking
5. **Caching Layer**: Redis for distributed caching
6. **Rate Limiting**: Token bucket or leaky bucket algorithm
7. **GraphQL API**: Alternative to REST
8. **gRPC Support**: High-performance RPC

## Conclusion

The refactored architecture provides:

- ✅ Clear module boundaries
- ✅ Separation of concerns
- ✅ Easy testability
- ✅ Maintainability
- ✅ Scalability
- ✅ MLOps best practices
- ✅ Production-ready code

For questions or improvements, please refer to the contributing guidelines.
