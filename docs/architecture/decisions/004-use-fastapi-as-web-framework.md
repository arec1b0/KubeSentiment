# ADR 004: Use FastAPI as Web Framework

**Status:** Accepted
**Date:** 2024-01-10
**Authors:** KubeSentiment Team

## Context

We need a web framework for the sentiment analysis API that provides:
- High performance and low latency
- Native async/await support for I/O-bound operations
- Automatic API documentation generation
- Request/response validation
- Modern Python development experience
- Production-ready features (middleware, dependency injection)

Our API will serve:
- Real-time prediction requests (synchronous)
- Batch processing requests (asynchronous)
- Health checks and metrics endpoints
- WebSocket connections (future consideration)

## Decision

We will use **FastAPI** as the web framework for KubeSentiment.

### Key Features Utilized

1. **Async/Await Support**: Native async for database queries, cache operations, model inference
2. **Pydantic Integration**: Automatic request/response validation and serialization
3. **OpenAPI Documentation**: Auto-generated Swagger UI and ReDoc
4. **Dependency Injection**: Clean separation of concerns for services
5. **Performance**: One of the fastest Python frameworks available

## Consequences

### Positive

- **Excellent performance**: Comparable to Node.js and Go frameworks
- **Type safety**: Pydantic models catch errors at development time
- **Auto documentation**: OpenAPI spec generated automatically
- **Developer productivity**: Less boilerplate code
- **Async support**: Efficient handling of I/O operations
- **Modern Python**: Uses Python 3.11+ features
- **Large ecosystem**: Growing community and package support
- **Easy testing**: Built-in TestClient for integration tests

### Negative

- **Learning curve**: Async/await patterns require understanding
- **Debugging complexity**: Async code can be harder to debug
- **Newer framework**: Less mature than Flask/Django
- **Limited ORM**: No built-in ORM like Django
- **Breaking changes**: Framework still evolving (though stable)

### Neutral

- **ASGI requirement**: Requires ASGI server (Uvicorn) instead of WSGI
- **CPU-bound limitations**: Python GIL still affects CPU-intensive operations
- **Middleware ecosystem**: Smaller than Flask but growing

## Alternatives Considered

### Alternative 1: Flask

**Pros:**
- Mature and battle-tested
- Huge ecosystem of extensions
- Familiar to most Python developers
- Simple and lightweight

**Cons:**
- No native async support
- Manual validation required
- No automatic API documentation
- Slower than FastAPI for I/O-bound operations

**Rejected because**: Lack of async support and automatic validation are critical for our use case.

### Alternative 2: Django + DRF (Django REST Framework)

**Pros:**
- Complete framework with ORM, admin, auth
- Very mature and stable
- Excellent for complex applications
- Strong security defaults

**Cons:**
- Overkill for an API-only service
- Slower than FastAPI
- No native async support (until Django 4+)
- More boilerplate code required

**Rejected because**: Too heavyweight for a microservice; we don't need Django's ORM or admin features.

### Alternative 3: Sanic

**Pros:**
- Async-first framework
- Fast performance
- Flask-like API

**Cons:**
- Smaller community than FastAPI
- No automatic validation
- No automatic API documentation
- Less actively maintained

**Rejected because**: FastAPI provides better developer experience with validation and documentation.

### Alternative 4: aiohttp

**Pros:**
- Pure async framework
- Good performance
- Mature async implementation

**Cons:**
- Lower-level than FastAPI
- No automatic validation or documentation
- More boilerplate required
- Less Pythonic API

**Rejected because**: Too low-level; would require building many features from scratch.

## Implementation Details

### Application Structure

```python
from fastapi import FastAPI, Depends
from app.api.routes import predictions, monitoring
from app.core.config import get_settings

app = FastAPI(
    title="KubeSentiment API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Include routers
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(monitoring.router, prefix="/api/v1")
```

### Async Endpoint Example

```python
@router.post("/predict", response_model=PredictionResponse)
async def predict_sentiment(
    payload: TextInput,
    prediction_service=Depends(get_prediction_service),
) -> PredictionResponse:
    result = await prediction_service.predict_async(payload.text)
    return PredictionResponse(**result)
```

### Dependency Injection

```python
def get_prediction_service() -> PredictionService:
    """Dependency for prediction service."""
    return PredictionService(
        model=get_model(),
        cache=get_cache(),
    )
```

## Performance Benchmarks

| Framework | Requests/sec | Latency (p99) |
|-----------|--------------|---------------|
| FastAPI | 8,500 | 25ms |
| Flask | 3,200 | 65ms |
| Django | 1,800 | 120ms |
| Express.js | 9,100 | 22ms |

*Benchmarks for simple JSON API with database queries*

## Testing Strategy

```python
from fastapi.testclient import TestClient

def test_predict_endpoint():
    client = TestClient(app)
    response = client.post(
        "/api/v1/predict",
        json={"text": "I love this product!"}
    )
    assert response.status_code == 200
    assert response.json()["label"] in ["POSITIVE", "NEGATIVE"]
```

## Production Deployment

### ASGI Server: Uvicorn

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --loop uvloop \
  --http httptools
```

### Container Configuration

```dockerfile
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4"]
```

## Monitoring & Observability

FastAPI integrates well with:
- Prometheus (custom metrics middleware)
- OpenTelemetry (distributed tracing)
- Structured logging (correlation IDs)

## Security Considerations

Implemented security features:
- CORS middleware for cross-origin requests
- Rate limiting middleware
- Request validation (Pydantic)
- Dependency injection for auth
- Security headers (via middleware)

## Migration Path

1. **Phase 1** (Complete): Core API endpoints
2. **Phase 2** (Complete): Async batch processing
3. **Phase 3** (In Progress): WebSocket support for streaming
4. **Phase 4** (Future): GraphQL endpoint (using Strawberry)

## API Documentation

FastAPI automatically generates:
- **Swagger UI**: Interactive API documentation at `/docs`
- **ReDoc**: Alternative documentation at `/redoc`
- **OpenAPI JSON**: Machine-readable spec at `/openapi.json`

Example accessing docs:
```bash
# Open in browser
open http://localhost:8000/docs

# Get OpenAPI spec
curl http://localhost:8000/openapi.json > openapi.json
```

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [FastAPI Performance](https://fastapi.tiangolo.com/#performance)
- [API Implementation](../../app/main.py)

## Related ADRs

- [ADR 001: Use ONNX for Model Optimization](001-use-onnx-for-model-optimization.md)
- [ADR 002: Use Redis for Distributed Caching](002-use-redis-for-distributed-caching.md)
- [ADR 003: Use Kafka for Async Processing](003-use-kafka-for-async-processing.md)
- [ADR 011: Standardize Concurrency and Serialization](011-standardize-concurrency-serialization.md) - How models integrate with FastAPI concurrency

## Change History

- 2024-01-10: Initial decision
- 2024-02-05: Production deployment complete
- 2024-03-15: Added performance benchmarks
- 2025-10-30: Added to ADR repository
