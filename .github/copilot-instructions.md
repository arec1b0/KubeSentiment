# GitHub Copilot Instructions for MLOps Project

## Project Overview

- **Purpose:** Production-ready FastAPI microservice for real-time sentiment analysis using DistilBERT (Hugging Face), containerized with Docker, following MLOps best practices.
- **Key Components:**
  - `app/main.py`: FastAPI app factory, middleware, and entrypoint
  - `app/api.py`: All API endpoints (`/predict`, `/health`, `/metrics`), Pydantic schemas
  - `app/ml/sentiment.py`: Model loading, inference, and error handling
  - `app/config.py`: Centralized config via Pydantic, supports env vars (prefix `MLOPS_`)
  - `app/monitoring.py`: Prometheus metrics collection for MLOps observability
- **API Endpoints:** `/predict`, `/health`, `/metrics` (see `README.md` for details)

## Architecture & Patterns

- **Service Structure:** Modular FastAPI app with clear separation:
  - API logic (`api.py`) imports model logic (`ml/sentiment.py`) and config (`config.py`)
  - Model is loaded at startup and cached for all requests
  - All endpoints use dependency injection for config and model
- **Error Handling:**
  - Global exception handler in `main.py` returns JSON with error_id
  - Model loading failures degrade gracefully (mock responses, clear status)
- **Monitoring:**
  - `/metrics` endpoint exposes system and model metrics (PyTorch, CUDA, memory)
  - All responses include `X-Process-Time-MS` header (middleware in `main.py`)
- **Configuration:**
  - All settings can be overridden via env vars (see `app/config.py`)
  - Example: `MLOPS_MODEL_NAME`, `MLOPS_DEBUG`, etc.

## Developer Workflows

- **Local Dev:**
  - Install: `pip install -r requirements.txt`
  - Run: `uvicorn app.main:app --reload`
- **Docker:**
  - Build: `docker build -t sentiment-service:0.1 .`
  - Run: `docker run -d -p 8000:8000 sentiment-service:0.1`
- **Testing:**
  - (If present) Run `pytest` or see `test_service.py` for test entrypoints
- **Debugging:**
  - Enable debug logs: set `MLOPS_DEBUG=true` or `MLOPS_LOG_LEVEL=DEBUG`
  - Logs output to stdout (see `logging` config in `main.py`)

## Project-Specific Conventions

- **API versioning:**
  - In production, endpoints are prefixed with `/api/v1` (see `main.py`)
  - In debug mode, endpoints are at root (`/predict`, etc.)
- **Input validation:**
  - All input via Pydantic models; empty/whitespace text is rejected
- **Model management:**
  - Model is loaded once at startup; failures do not crash the service
  - Model cache dir can be set via config

## Integration & Extensibility

- **Model:** Uses Hugging Face `transformers` pipeline; model name/configurable
- **Metrics:** Uses PyTorch for system info; works with/without CUDA
- **Extending:** Add new endpoints to `api.py`, new models to `ml/`

## References

- See `README.md` for API usage, deployment, and troubleshooting
- See `app/config.py` for all configurable settings
- Example API usage and responses are in `README.md`

---

## 🤖 ML Model Development Standards

### Framework Requirements

- Use **PyTorch** or **TensorFlow** for deep learning models
- Use **Transformers** library for NLP models (current: DistilBERT)
- Implement **scikit-learn** for traditional ML algorithms when needed
- Use **MLflow** for experiment tracking and model registry
- Track model lineage, hyperparameters, and metrics

### Model Design Best Practices

- Implement base classes with abstract methods for consistency
- Use dependency injection for model loading
- Cache models at startup (singleton pattern)
- Implement graceful degradation on model load failures
- Use semantic versioning for model releases (MAJOR.MINOR.PATCH)

---

## 📊 Monitoring & Observability

### Three Pillars

- **Metrics:** Prometheus + Grafana for quantitative measurements
- **Logs:** Structured JSON logging with correlation IDs
- **Traces:** OpenTelemetry for distributed tracing

### Key Metrics to Track

- `ml_predictions_total`: Counter for total predictions
- `ml_prediction_duration_seconds`: Histogram for latency
- `ml_model_accuracy`: Gauge for model performance
- `ml_data_drift_score`: Gauge for data drift detection
- `ml_prediction_errors_total`: Counter for error tracking

### Logging Standards

- Use **structlog** for structured JSON logging
- Include correlation IDs in all log entries
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Never log sensitive data or PII
- Include request/response metadata for debugging

---

## 🔄 Data Engineering Standards

### Data Validation

- Use **Pandera** or **Great Expectations** for schema validation
- Validate data types, ranges, and constraints at ingestion
- Implement data quality checks and alerts
- Create data quality reports for monitoring

### Processing Best Practices

- Use **pandas with pyarrow** backend for efficiency
- Implement **vectorized operations** instead of loops
- Apply lazy evaluation patterns where possible
- Use chunked processing for large datasets
- Implement proper error handling and retries

---

## 🐳 Container & Deployment

### Docker Best Practices

- Use multi-stage builds for smaller images
- Create non-root users for security
- Set PYTHONUNBUFFERED=1 and PYTHONDONTWRITEBYTECODE=1
- Implement health checks and readiness probes
- Pin all dependency versions

### Kubernetes Standards

- Define resource requests and limits
- Implement horizontal pod autoscaling (HPA)
- Use proper liveness and readiness probes
- Implement network policies for security
- Use ConfigMaps for configuration, Secrets for credentials

---

## 🧪 Testing Standards

### Coverage Requirements

- Maintain **>90% code coverage** for core modules
- Write unit tests for all functions
- Create integration tests for API endpoints
- Test model inference and error handling
- Use pytest with fixtures for test data

### Testing Patterns

```python
import pytest

@pytest.fixture
def sentiment_model():
    return SentimentAnalyzer()

def test_prediction_format(sentiment_model):
    result = sentiment_model.predict("Great!")
    assert "label" in result
    assert "score" in result
    assert 0 <= result["score"] <= 1
```

---

## 🔒 Security Standards

### API Security

- Never commit secrets to version control
- Use environment variables or secret managers
- Implement input validation for all requests
- Use authentication and authorization in production
- Implement rate limiting
- Create audit logs for predictions

### Data Privacy

- Never log sensitive data or PII
- Implement data encryption at rest and in transit
- Follow GDPR/compliance requirements
- Document data retention policies

---

## 🐍 Python Code Quality

### Standards

- Use **Python 3.11+** with type hints
- Follow **PEP 8** style guidelines
- Use **black** for formatting (line length: 100)
- Use **ruff** for linting
- Implement pre-commit hooks

### Code Style Example

```python
from typing import Dict, Optional
from pydantic import BaseModel, Field

class PredictionRequest(BaseModel):
    """Request schema for predictions."""
    text: str = Field(..., min_length=1, description="Input text")

def predict(text: str, version: str = "latest") -> Dict[str, float]:
    """
    Predict sentiment for text.

    Args:
        text: Input text to analyze
        version: Model version to use

    Returns:
        Dictionary with label and score
    """
    # Implementation
```

---

## ⚠️ Anti-Patterns to Avoid

### DON'T

- ❌ Hardcode secrets or credentials
- ❌ Use Jupyter notebooks for production code
- ❌ Process all data in memory for large datasets
- ❌ Skip data validation and quality checks
- ❌ Deploy without health checks and monitoring
- ❌ Ignore error handling and retries
- ❌ Train models without validation sets
- ❌ Skip logging for predictions and errors
- ❌ Use manual deployment processes
- ❌ Monitor vanity metrics without business context

### DO

- ✅ Use environment variables for configuration
- ✅ Implement comprehensive error handling
- ✅ Write tests with >90% coverage
- ✅ Use structured logging with correlation IDs
- ✅ Implement proper monitoring and alerting
- ✅ Follow SOLID principles
- ✅ Use dependency injection
- ✅ Validate all inputs with Pydantic
- ✅ Implement CI/CD pipelines
- ✅ Track experiments with MLflow

---

## 🤝 For AI Coding Assistants

When generating code:

1. Use **type hints** for all functions and variables
2. Implement **proper error handling** with custom exceptions
3. Add **comprehensive docstrings** (Google/NumPy style)
4. Include **logging** with appropriate levels
5. **Write tests** alongside production code
6. **Validate inputs** using Pydantic models
7. Maintain **modularity** and separation of concerns
8. Consider **observability** (metrics, logs, traces)
9. Follow **security best practices**
10. Update **configuration** when adding features

When suggesting improvements:

- Prioritize security and performance
- Consider scalability and maintainability
- Follow MLOps best practices from `.cursor/rules/`
- Suggest testing strategies
- Recommend monitoring for critical paths

---

*For detailed MLOps standards, see `.cursor/rules/` directory.*
*Last Updated: October 2025*
