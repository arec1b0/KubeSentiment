# Error Handling Guide

## Overview

KubeSentiment implements a comprehensive, standardized error handling system that provides clear, actionable error messages to API clients while maintaining detailed logging for debugging and monitoring.

## Architecture

### Exception Hierarchy

All custom exceptions inherit from the base `ServiceError` class, which provides:
- HTTP status code mapping
- Machine-readable error codes
- Optional context dictionaries for additional details

```
ServiceError (base)
├── ValidationError (400)
│   ├── TextValidationError
│   │   ├── TextTooLongError
│   │   └── TextEmptyError
│   ├── BatchSizeExceededError
│   ├── EmptyBatchError
│   ├── InvalidModelError
│   ├── ConfigurationError (500)
│   │   ├── SecurityConfigError
│   │   ├── ModelConfigError
│   │   └── SettingsValidationError
│   ├── InvalidSecretsConfigError
│   ├── InvalidModelPathError
│   ├── FeatureMismatchError
│   ├── UnfittedScalerError
│   ├── InvalidScalerStateError
│   └── UnsupportedBackendError
├── AuthenticationError (401)
│   ├── VaultAuthenticationError
│   └── KubernetesAuthenticationError
├── NotFoundError (404)
│   └── ModelMetadataNotFoundError
├── ConflictError (409)
├── InternalError (500)
│   ├── ModelInitializationError
│   ├── ModelCachingError
│   ├── ModelExportError
│   ├── ScalerStatePersistenceError
│   ├── AsyncContextError
│   ├── ServiceNotStartedError
│   ├── HealthCheckError
│   └── TracingError
├── ServiceUnavailableError (503)
│   ├── QueueCapacityExceededError
│   └── CircuitBreakerOpenError
└── ModelError (500)
    ├── ModelNotLoadedError (503)
    ├── ModelInferenceError
    └── ModelLoadingError
```

## Error Codes

Error codes follow a structured format with category-based ranges:

### Ranges
- **1000-1099**: Input validation errors
- **2000-2099**: Model errors
- **3000-3099**: Security and authentication errors
- **4000-4099**: System and service errors
- **5000-5099**: Configuration errors
- **6000-6099**: Feature processing errors

### Complete Error Code List

#### Input Validation (1000-1099)
| Code | Description |
|------|-------------|
| E1001 | Invalid input text provided |
| E1002 | Text too long |
| E1003 | Text empty or whitespace only |
| E1004 | Text contains invalid characters |
| E1005 | Batch size exceeded |
| E1006 | Empty batch |

#### Model Errors (2000-2099)
| Code | Description |
|------|-------------|
| E2001 | Model not loaded |
| E2002 | Model inference failed |
| E2003 | Model timeout |
| E2004 | Model loading failed |
| E2005 | Model initialization failed |
| E2006 | Model caching failed |
| E2007 | Model metadata not found |
| E2008 | Invalid model path |
| E2009 | Model export failed |
| E2010 | Unsupported backend |

#### Security & Authentication (3000-3099)
| Code | Description |
|------|-------------|
| E3001 | Invalid model name |
| E3002 | Unauthorized access |
| E3003 | Vault authentication failed |
| E3004 | Kubernetes authentication failed |
| E3005 | Invalid secrets configuration |

#### System & Service (4000-4099)
| Code | Description |
|------|-------------|
| E4001 | Internal server error |
| E4002 | Service unavailable |
| E4003 | Rate limit exceeded |
| E4004 | Async context error |
| E4005 | Queue capacity exceeded |
| E4006 | Service not started |
| E4007 | Circuit breaker open |
| E4008 | Health check failed |
| E4009 | Tracing error |

#### Configuration (5000-5099)
| Code | Description |
|------|-------------|
| E5001 | Security config error |
| E5002 | Model config error |
| E5003 | Settings validation error |

#### Feature Processing (6000-6099)
| Code | Description |
|------|-------------|
| E6001 | Feature mismatch |
| E6002 | Unfitted scaler |
| E6003 | Scaler persistence failed |
| E6004 | Invalid scaler state |

## Error Response Format

### Standard Error Response

All error responses follow a consistent JSON structure:

```json
{
  "error_code": "E2001",
  "error_message": "Model 'sentiment-v1' is not loaded or unavailable",
  "status_code": 503,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-11-14T10:30:00.123456",
  "context": {
    "model_name": "sentiment-v1",
    "backend": "pytorch"
  }
}
```

### Validation Error Response

Validation errors include detailed field-level information:

```json
{
  "error_code": "E1001",
  "error_message": "Request validation failed",
  "detail": "The request data failed validation. Please check the errors below.",
  "validation_errors": [
    {
      "loc": ["body", "text"],
      "msg": "Text length of 15000 characters exceeds the maximum of 10000",
      "type": "text_too_long"
    }
  ],
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-11-14T10:30:00.123456"
}
```

## Usage Examples

### Raising Custom Exceptions

```python
from app.utils.exceptions import (
    TextTooLongError,
    ModelNotLoadedError,
    VaultAuthenticationError,
)

# Input validation
if len(text) > max_length:
    raise TextTooLongError(
        text_length=len(text),
        max_length=max_length,
        context={"user_id": user_id}
    )

# Model errors
if not self.model_loaded:
    raise ModelNotLoadedError(
        model_name="sentiment-analyzer",
        context={"backend": "pytorch"}
    )

# Authentication errors
if not vault_client.is_authenticated():
    raise VaultAuthenticationError(
        "Failed to authenticate with Vault",
        context={"vault_addr": vault_addr}
    )
```

### Handling Exceptions

```python
from app.utils.exceptions import ModelError, ValidationError

try:
    result = model.predict(text)
except ValidationError as e:
    # Handle validation errors (400-level)
    logger.warning(f"Validation failed: {e}", error_code=e.code)
    # Let the global handler format the response
    raise
except ModelError as e:
    # Handle model-specific errors (500-level)
    logger.error(f"Model error: {e}", error_code=e.code)
    # Optionally wrap with additional context
    raise ModelInferenceError(
        f"Prediction failed: {e}",
        model_name="sentiment-v1",
        context={"original_error": str(e)}
    )
```

### Using Error Codes Programmatically

```python
from app.utils.error_codes import ErrorCode, ErrorMessages, raise_validation_error

# Get error message
message = ErrorMessages.get_message(ErrorCode.TEXT_TOO_LONG)

# Raise with standard error response
raise_validation_error(
    error_code=ErrorCode.TEXT_TOO_LONG,
    detail=f"Text exceeds {max_length} characters",
    status_code=400,
    text_length=len(text),
    max_length=max_length
)
```

## API Client Error Handling

### HTTP Status Code Mapping

| Status Code | Meaning | Action |
|-------------|---------|--------|
| 400 | Bad Request | Fix request data, check validation errors |
| 401 | Unauthorized | Provide valid API key or authentication token |
| 404 | Not Found | Check resource identifier (e.g., model name) |
| 409 | Conflict | Resource already exists or operation conflicts |
| 422 | Unprocessable Entity | Fix validation errors in request body |
| 500 | Internal Server Error | Retry with exponential backoff, contact support |
| 503 | Service Unavailable | Service is temporarily down, retry later |

### Example Client Implementation (Python)

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure retries for transient errors
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    backoff_factor=1
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("https://", adapter)

def predict_sentiment(text: str, api_key: str):
    """Make a prediction with proper error handling."""
    try:
        response = session.post(
            "https://api.example.com/api/v1/predict",
            json={"text": text},
            headers={"X-API-Key": api_key}
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        error_data = e.response.json()
        error_code = error_data.get("error_code")
        error_message = error_data.get("error_message")

        # Handle specific error codes
        if error_code == "E1002":  # TEXT_TOO_LONG
            print(f"Text too long: {error_message}")
            # Truncate and retry
            context = error_data.get("context", {})
            max_length = context.get("max_length")
            return predict_sentiment(text[:max_length], api_key)

        elif error_code == "E3002":  # UNAUTHORIZED
            print("Invalid API key")
            raise

        elif error_code in ["E4002", "E4005", "E4007"]:  # Service unavailable
            print(f"Service temporarily unavailable: {error_message}")
            # Implement exponential backoff retry
            raise

        else:
            print(f"Error {error_code}: {error_message}")
            raise
```

## Best Practices

### 1. Always Use Custom Exceptions

❌ **Don't:**
```python
raise ValueError("Model path is invalid")
raise RuntimeError("Failed to load model")
```

✅ **Do:**
```python
raise InvalidModelPathError(path=model_path)
raise ModelLoadingError("Failed to load model", model_name="sentiment-v1")
```

### 2. Provide Contextual Information

```python
# Good: Includes context for debugging
raise ModelInferenceError(
    "Prediction failed due to tensor dimension mismatch",
    model_name="sentiment-v1",
    context={
        "expected_shape": (1, 512),
        "received_shape": (1, 256),
        "backend": "pytorch"
    }
)
```

### 3. Log Before Raising

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    result = dangerous_operation()
except Exception as e:
    logger.error(
        "Operation failed",
        operation="dangerous_operation",
        error=str(e),
        exc_info=True
    )
    raise ModelError("Operation failed") from e
```

### 4. Don't Catch Too Broadly

❌ **Don't:**
```python
try:
    process_data()
except Exception:
    # Too broad, catches everything
    pass
```

✅ **Do:**
```python
try:
    process_data()
except (ValidationError, ModelError) as e:
    # Specific exception types
    logger.error(f"Processing failed: {e}")
    raise
except Exception as e:
    # Unexpected error
    logger.exception("Unexpected error during processing")
    raise InternalError("Data processing failed") from e
```

### 5. Re-raise Custom Exceptions

```python
# When catching custom exceptions, let them propagate
try:
    operation()
except (ValidationError, ModelError):
    # These are already well-formatted, just re-raise
    raise
except SomeOtherError as e:
    # Wrap in appropriate custom exception
    raise InternalError("Operation failed") from e
```

## Testing Error Handling

### Unit Testing

```python
import pytest
from app.utils.exceptions import TextTooLongError, ModelNotLoadedError

def test_text_validation():
    """Test that text validation raises appropriate errors."""
    with pytest.raises(TextTooLongError) as exc_info:
        validate_text("x" * 10001, max_length=10000)

    assert exc_info.value.code == "TEXT_TOO_LONG"
    assert exc_info.value.status_code == 400

def test_model_not_loaded():
    """Test model not loaded error."""
    with pytest.raises(ModelNotLoadedError) as exc_info:
        model = SentimentModel()
        model.predict("test")

    assert exc_info.value.code == "MODEL_NOT_LOADED"
    assert exc_info.value.status_code == 503
```

### Integration Testing

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_error_response_format():
    """Test that error responses follow the standard format."""
    response = client.post(
        "/api/v1/predict",
        json={"text": "x" * 10001}
    )

    assert response.status_code == 400
    data = response.json()

    # Check standard error response fields
    assert "error_code" in data
    assert "error_message" in data
    assert "status_code" in data
    assert "correlation_id" in data
    assert "timestamp" in data

    # Check specific error
    assert data["error_code"] == "E1002"
```

## Monitoring and Alerting

### Key Metrics to Track

1. **Error rate by error code**: Monitor trends in specific error types
2. **4xx vs 5xx ratio**: Track client vs server errors
3. **P99 error response time**: Ensure errors are returned quickly
4. **Circuit breaker activations**: Monitor E4007 errors

### Example Prometheus Queries

```promql
# Total error rate
rate(http_requests_total{status=~"4..|5.."}[5m])

# Errors by code
sum by (error_code) (rate(http_requests_total{status=~"4..|5.."}[5m]))

# 5xx error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Alerting Rules

```yaml
# Alert on high 5xx error rate
- alert: HighServerErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: High server error rate detected
    description: Server error rate is {{ $value }} errors/sec

# Alert on circuit breaker open
- alert: CircuitBreakerOpen
  expr: count by (service) (http_requests_total{error_code="E4007"}) > 0
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: Circuit breaker open for {{ $labels.service }}
```

## Migration Guide

### Migrating from Generic Exceptions

If you have existing code using generic exceptions, follow this pattern:

**Before:**
```python
def validate_input(text: str):
    if len(text) > 10000:
        raise ValueError("Text is too long")
```

**After:**
```python
from app.utils.exceptions import TextTooLongError

def validate_input(text: str, max_length: int = 10000):
    if len(text) > max_length:
        raise TextTooLongError(
            text_length=len(text),
            max_length=max_length
        )
```

## Troubleshooting

### Common Issues

**Issue**: Custom exceptions not being caught by global handler

**Solution**: Ensure the exception inherits from `ServiceError`:
```python
class MyCustomError(ServiceError):  # Must inherit from ServiceError
    status_code = 400
```

**Issue**: Error responses missing correlation_id

**Solution**: Ensure `CorrelationIdMiddleware` is registered before other middleware in `main.py`

**Issue**: Context not appearing in error response

**Solution**: Context must be a dictionary or None:
```python
# Correct
raise ModelError("Failed", context={"key": "value"})

# Wrong
raise ModelError("Failed", context="string")  # Will be ignored
```

## References

- [Exception hierarchy](../app/utils/exceptions.py)
- [Error codes](../app/utils/error_codes.py)
- [Error handlers](../app/utils/error_handlers.py)
- [Global exception handler](../app/main.py)
