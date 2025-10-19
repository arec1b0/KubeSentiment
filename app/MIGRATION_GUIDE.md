# Migration Guide: Old Structure → New Modular Architecture

## Overview

This guide helps you migrate from the old application structure to the new modular architecture. The refactoring maintains all existing functionality while improving organization, testability, and maintainability.

## What Changed

### File Structure Changes

#### Old Structure

```
app/
├── __init__.py
├── api.py                      # All API endpoints
├── api_onnx.py                 # ONNX-specific API
├── unified_api.py              # Unified API attempt
├── config.py                   # Configuration
├── logging_config.py           # Logging
├── middleware.py               # Auth middleware
├── correlation_middleware.py   # Correlation + logging
├── monitoring.py               # Metrics
├── exceptions.py               # Exceptions
├── error_codes.py              # Error codes
├── ml/
│   ├── sentiment.py            # PyTorch model
│   ├── onnx_optimizer.py       # ONNX model
│   └── model_strategy.py       # Strategy pattern
└── utils/
    └── error_handlers.py
```

#### New Structure

```
app/
├── core/                       # Core components
│   ├── config.py
│   ├── logging.py
│   ├── dependencies.py
│   └── events.py
├── api/                        # API layer
│   ├── routes/                 # Endpoints organized
│   ├── middleware/             # All middleware
│   └── schemas/                # Request/response schemas
├── models/                     # ML models
│   ├── base.py
│   ├── pytorch_sentiment.py
│   ├── onnx_sentiment.py
│   └── factory.py
├── services/                   # Business logic
│   └── prediction.py
├── monitoring/                 # Observability
│   ├── prometheus.py
│   └── health.py
├── utils/                      # Utilities
│   ├── exceptions.py
│   ├── error_codes.py
│   └── error_handlers.py
└── main.py
```

## Import Changes

### Configuration

**Old:**

```python
from app.config import get_settings, Settings
```

**New:**

```python
from app.core.config import get_settings, Settings
```

### Logging

**Old:**

```python
from app.logging_config import get_logger, setup_structured_logging
```

**New:**

```python
from app.core.logging import get_logger, setup_logging
```

### Exceptions

**Old:**

```python
from app.exceptions import ModelNotLoadedError, TextEmptyError
```

**New:**

```python
from app.utils.exceptions import ModelNotLoadedError, TextEmptyError
```

### Error Codes

**Old:**

```python
from app.error_codes import ErrorCode, raise_validation_error
```

**New:**

```python
from app.utils.error_codes import ErrorCode, raise_validation_error
```

### Models

**Old:**

```python
from app.ml.sentiment import SentimentAnalyzer, get_sentiment_analyzer
from app.ml.onnx_optimizer import ONNXSentimentAnalyzer
```

**New:**

```python
from app.models.pytorch_sentiment import SentimentAnalyzer, get_sentiment_analyzer
from app.models.onnx_sentiment import ONNXSentimentAnalyzer
# Or use the factory
from app.models.factory import ModelFactory
model = ModelFactory.create_model("pytorch")
```

### Monitoring

**Old:**

```python
from app.monitoring import get_metrics, PrometheusMetrics
```

**New:**

```python
from app.monitoring.prometheus import get_metrics, PrometheusMetrics
```

### Middleware

**Old:**

```python
from app.middleware import APIKeyAuthMiddleware
from app.correlation_middleware import CorrelationIdMiddleware
```

**New:**

```python
from app.api.middleware import APIKeyAuthMiddleware, CorrelationIdMiddleware
```

### API Schemas

**Old:**

```python
# Schemas were defined in api.py
class TextInput(BaseModel):
    ...
```

**New:**

```python
from app.api.schemas import TextInput, PredictionResponse
```

## API Endpoint Organization

### Old: Single File with All Endpoints

All endpoints were in `api.py`, `api_onnx.py`, or `unified_api.py`.

### New: Organized by Domain

**Health Checks:**

```python
from app.api.routes.health import router as health_router
```

**Predictions:**

```python
from app.api.routes.predictions import router as predictions_router
```

**Metrics:**

```python
from app.api.routes.metrics import router as metrics_router
```

**Model Info:**

```python
from app.api.routes.model_info import router as model_info_router
```

## Dependency Injection

### Old: Direct Instantiation

```python
@app.post("/predict")
async def predict(payload: TextInput):
    analyzer = SentimentAnalyzer()  # Direct instantiation
    result = analyzer.predict(payload.text)
    return result
```

### New: Dependency Injection

```python
from app.core.dependencies import get_prediction_service

@router.post("/predict")
async def predict(
    payload: TextInput,
    prediction_service = Depends(get_prediction_service)
):
    result = prediction_service.predict(payload.text)
    return result
```

## Service Layer Pattern

### Old: Direct Model Access

```python
@app.post("/predict")
async def predict(payload: TextInput):
    model = get_sentiment_analyzer()
    if not model.is_ready():
        raise HTTPException(...)
    result = model.predict(payload.text)
    return result
```

### New: Through Service Layer

```python
@router.post("/predict")
async def predict(
    payload: TextInput,
    prediction_service = Depends(get_prediction_service)
):
    # Service handles readiness checks and business logic
    result = prediction_service.predict(payload.text)
    return result
```

## Testing Migration

### Old Test Structure

```python
from app.ml.sentiment import SentimentAnalyzer
from app.config import get_settings

def test_prediction():
    analyzer = SentimentAnalyzer()
    result = analyzer.predict("Great!")
    assert result["label"] in ["POSITIVE", "NEGATIVE"]
```

### New Test Structure with Dependency Override

```python
from app.core.dependencies import get_model_service
from app.models.factory import ModelFactory
from fastapi.testclient import TestClient

def test_prediction():
    # Override dependencies for testing
    def mock_model():
        return MockModel()

    app.dependency_overrides[get_model_service] = mock_model

    client = TestClient(app)
    response = client.post("/predict", json={"text": "Great!"})
    assert response.status_code == 200
```

## Configuration Updates

### Environment Variables

No changes needed - all environment variables work the same:

```bash
MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
MLOPS_DEBUG=false
MLOPS_LOG_LEVEL=INFO
```

### Configuration Access

```python
# Both old and new code
from app.core.config import get_settings
settings = get_settings()
```

## Middleware Order

The middleware order is important. The new structure maintains the correct order:

1. `CorrelationIdMiddleware` - First, to add correlation IDs
2. `RequestLoggingMiddleware` - Log with correlation IDs
3. `CORSMiddleware` - CORS handling
4. `APIKeyAuthMiddleware` - Authentication
5. `MetricsMiddleware` - Metrics collection (last)

## Running the Application

### Development

```bash
# Old and new - same command
python -m uvicorn app.main:app --reload

# Or using the direct script
python app/main.py
```

### Production

```bash
# Old and new - same command
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker

```bash
# No changes needed
docker build -t sentiment-api .
docker run -p 8000:8000 sentiment-api
```

## Breaking Changes

### ⚠️ None for External API

The external API remains unchanged:

- All endpoints work the same
- Request/response formats unchanged
- Authentication unchanged
- Configuration unchanged

### ⚠️ Internal Code Only

Internal code that directly imports from old locations needs updates:

- Update import statements (see "Import Changes" above)
- Use dependency injection instead of direct instantiation
- Use the factory pattern for model creation

## Step-by-Step Migration

### For Application Code

1. **Update Imports**

   ```bash
   # Find all imports to update
   grep -r "from app.config import" app/
   grep -r "from app.logging_config import" app/
   grep -r "from app.exceptions import" app/
   ```

2. **Replace Imports**
   - `app.config` → `app.core.config`
   - `app.logging_config` → `app.core.logging`
   - `app.exceptions` → `app.utils.exceptions`
   - `app.error_codes` → `app.utils.error_codes`
   - `app.ml.sentiment` → `app.models.pytorch_sentiment`
   - `app.ml.onnx_optimizer` → `app.models.onnx_sentiment`
   - `app.monitoring` → `app.monitoring.prometheus`

3. **Update Direct Model Instantiation**

   ```python
   # Old
   from app.ml.sentiment import SentimentAnalyzer
   model = SentimentAnalyzer()

   # New
   from app.models.factory import ModelFactory
   model = ModelFactory.create_model("pytorch")
   ```

### For Tests

1. **Update Test Imports**
   Same as application code imports.

2. **Use Dependency Overrides**

   ```python
   from app.core.dependencies import get_model_service

   def test_with_mock():
       app.dependency_overrides[get_model_service] = lambda: MockModel()
       # Your test code
   ```

3. **Test New Modules**
   - Test routes independently
   - Test services independently
   - Test models independently

## Verification Checklist

After migration, verify:

- [ ] Application starts without errors
- [ ] All endpoints respond correctly
- [ ] Health checks work (`/health`, `/ready`)
- [ ] Metrics endpoint works (`/metrics`)
- [ ] Predictions work (`/predict`)
- [ ] Authentication works (if enabled)
- [ ] Logging outputs correctly
- [ ] Correlation IDs present in logs
- [ ] Tests pass
- [ ] Docker build works
- [ ] Kubernetes deployment works

## Rollback Plan

If issues occur:

1. **Keep Old Files**: Don't delete old files immediately
2. **Git Branch**: Keep changes in a feature branch
3. **Gradual Migration**: Migrate one module at a time
4. **Feature Flags**: Use environment variables to toggle between old/new

## Benefits of New Structure

✅ **Improved Organization**

- Clear module boundaries
- Easier to navigate
- Logical grouping

✅ **Better Testability**

- Independent module testing
- Easy mocking with dependency injection
- Service layer separation

✅ **Enhanced Maintainability**

- Single responsibility per module
- Easier to modify
- Clear dependencies

✅ **Scalability**

- Easy to add new features
- Simple to add new models
- Straightforward extensions

✅ **MLOps Best Practices**

- Factory pattern for models
- Service layer for business logic
- Proper dependency injection
- Observability built-in

## Common Issues and Solutions

### Issue: Import Errors

**Solution**: Update all import statements to new paths

### Issue: Circular Imports

**Solution**: Use dependency injection instead of direct imports

### Issue: Tests Failing

**Solution**: Update test imports and use dependency overrides

### Issue: Model Not Loading

**Solution**: Check model factory configuration and backend selection

### Issue: Middleware Order

**Solution**: Verify middleware is added in correct order in `main.py`

## Getting Help

- Check `ARCHITECTURE.md` for detailed architecture documentation
- Review `app/UNIFIED_API_README.md` for API usage
- See `tests/` for example usage patterns
- Check logs with correlation IDs for debugging

## Timeline Recommendation

1. **Phase 1** (Day 1): Core module migration
2. **Phase 2** (Day 2): API and middleware migration
3. **Phase 3** (Day 3): Models and services migration
4. **Phase 4** (Day 4): Testing and verification
5. **Phase 5** (Day 5): Deployment and monitoring

## Conclusion

The new modular architecture maintains backward compatibility while providing:

- Better code organization
- Improved testability
- Enhanced maintainability
- MLOps best practices
- Production-ready structure

All existing functionality is preserved - only the internal organization has changed.
