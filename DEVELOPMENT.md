# Development Guide

**Version:** 1.0.0  
**Last Updated:** October 21, 2025

## Table of Contents

- [Getting Started](#getting-started)
- [Local Development Setup](#local-development-setup)
- [Development Workflow](#development-workflow)
- [Code Quality Standards](#code-quality-standards)
- [Testing Guidelines](#testing-guidelines)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- **Python**: 3.11 or higher
- **Docker**: Latest version (for containerized development)
- **Git**: For version control
- **kubectl**: For Kubernetes development (optional)
- **Helm**: For chart development (optional)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/arec1b0/mlops-sentiment.git
cd mlops-sentiment

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run the application
python run.py

# Access the API
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Swagger UI
```

---

## Local Development Setup

### Option 1: Native Python Environment

```bash
# 1. Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 2. Upgrade pip and install build tools
pip install --upgrade pip setuptools wheel

# 3. Install production dependencies
pip install -r requirements.txt

# 4. Install development dependencies
pip install -r requirements-dev.txt

# 5. Set up pre-commit hooks
pre-commit install

# 6. Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Docker Development

```bash
# Build development image
docker build -t sentiment-dev:latest .

# Run with live reload
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/app:/app/app \
  -e MLOPS_DEBUG=true \
  -e MLOPS_LOG_LEVEL=DEBUG \
  --name sentiment-dev \
  sentiment-dev:latest

# View logs
docker logs -f sentiment-dev
```

### Option 3: Docker Compose

```bash
# Start all services (app + monitoring stack)
docker-compose up -d

# View logs
docker-compose logs -f mlops-api

# Stop all services
docker-compose down
```

### Environment Variables

Create a `.env` file for local development:

```bash
# Core Configuration
MLOPS_APP_NAME="ML Model Serving API"
MLOPS_APP_VERSION="1.0.0"
MLOPS_DEBUG=true
MLOPS_LOG_LEVEL=DEBUG
MLOPS_HOST=0.0.0.0
MLOPS_PORT=8000

# Model Configuration
MLOPS_MODEL_NAME="distilbert-base-uncased-finetuned-sst-2-english"
MLOPS_MODEL_CACHE_DIR="./models"
MLOPS_MAX_TEXT_LENGTH=512
MLOPS_PREDICTION_CACHE_MAX_SIZE=1000

# Optional: ONNX Model Path (for optimized inference)
# MLOPS_ONNX_MODEL_PATH="./onnx_models/distilbert"

# Optional: Security (disable for local dev)
# MLOPS_API_KEY="your-dev-api-key"

# Optional: Vault (disable for local dev)
MLOPS_VAULT_ENABLED=false

# Monitoring
MLOPS_ENABLE_METRICS=true
MLOPS_METRICS_CACHE_TTL=5
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Write Code

Follow the project structure:

```
app/
├── core/           # Add core infrastructure here
├── api/            # Add API endpoints/middleware here
├── services/       # Add business logic here
├── ml/             # Add ML models/strategies here
├── monitoring/     # Add monitoring code here
└── utils/          # Add utilities here
```

### 3. Write Tests

```bash
# Create test file (mirrors source file)
tests/test_your_feature.py

# Run tests
pytest tests/test_your_feature.py -v

# Check coverage
pytest tests/test_your_feature.py --cov=app.your_module
```

### 4. Format and Lint

```bash
# Auto-format code
make format
# Or manually:
black app/ tests/
isort app/ tests/

# Lint code
make lint
# Or manually:
ruff check app/ tests/
flake8 app/ tests/
mypy app/
```

### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit (pre-commit hooks will run automatically)
git commit -m "feat: add new feature

- Detailed description
- What changed
- Why it changed
"
```

### 6. Push and Create PR

```bash
# Push to remote
git push origin feature/your-feature-name

# Create pull request on GitHub
# PR will trigger CI/CD pipeline
```

---

## Code Quality Standards

### Code Formatting

- **Line Length**: 100 characters (configured in `pyproject.toml`)
- **Formatter**: Black (deterministic)
- **Import Sorter**: isort (compatible with Black)

```bash
# Format all code
black app/ tests/
isort app/ tests/

# Check formatting without changes
black --check app/ tests/
isort --check-only app/ tests/
```

### Linting

- **Linter**: Ruff (fast Python linter)
- **Style Checker**: Flake8 (PEP 8 compliance)
- **Type Checker**: mypy (static type checking)

```bash
# Run all linters
ruff check app/ tests/
flake8 app/ tests/
mypy app/ --ignore-missing-imports --allow-untyped-decorators
```

### Type Hints

All functions must have type hints:

```python
# Good ✓
def predict(text: str, backend: str = "pytorch") -> Dict[str, Any]:
    """Predict sentiment for given text."""
    ...

# Bad ✗
def predict(text, backend="pytorch"):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def complex_function(param1: str, param2: int) -> bool:
    """One-line summary of what this function does.

    More detailed explanation if needed. Explain parameters,
    return values, and any exceptions raised.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param2 is negative
        ModelNotLoadedError: When model is not initialized

    Example:
        >>> result = complex_function("test", 42)
        >>> assert result is True
    """
    ...
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                   # Fast, isolated tests
├── integration/            # Tests with dependencies
└── e2e/                    # End-to-end tests
```

### Writing Unit Tests

```python
import pytest
from app.ml.sentiment import SentimentAnalyzer

class TestSentimentAnalyzer:
    """Unit tests for SentimentAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Provide a SentimentAnalyzer instance."""
        return SentimentAnalyzer()

    def test_predict_positive_sentiment(self, analyzer):
        """Test prediction of positive sentiment."""
        result = analyzer.predict("I love this!")
        
        assert result["label"] == "POSITIVE"
        assert result["score"] > 0.9
        assert "inference_time_ms" in result

    @pytest.mark.parametrize("text,expected", [
        ("", "TextEmptyError"),
        ("great", "POSITIVE"),
        ("terrible", "NEGATIVE"),
    ])
    def test_various_inputs(self, analyzer, text, expected):
        """Test various input scenarios."""
        if expected.endswith("Error"):
            with pytest.raises(eval(expected)):
                analyzer.predict(text)
        else:
            result = analyzer.predict(text)
            assert result["label"] == expected
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::test_health_check -v

# Run tests matching pattern
pytest -k "test_predict" -v

# Run tests by marker
pytest -m unit           # Fast unit tests
pytest -m integration    # Integration tests
pytest -m "not slow"     # Skip slow tests
```

### Test Markers

```python
import pytest

@pytest.mark.unit
def test_fast_unit_test():
    """Fast, isolated test."""
    pass

@pytest.mark.integration
def test_with_dependencies():
    """Test requiring external services."""
    pass

@pytest.mark.slow
def test_time_consuming():
    """Test that takes >5 seconds."""
    pass
```

### Coverage Requirements

- **Minimum Coverage**: 85% (enforced in CI)
- **Target Coverage**: 90%+
- **Critical Paths**: 100% coverage (prediction endpoints, model loading)

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Check coverage against threshold
pytest --cov=app --cov-fail-under=85
```

---

## Debugging

### Local Debugging

```python
# Enable debug logging
MLOPS_DEBUG=true MLOPS_LOG_LEVEL=DEBUG python run.py

# Add breakpoints in code
import pdb; pdb.set_trace()  # Classic debugger
import ipdb; ipdb.set_trace()  # Enhanced debugger (install: pip install ipdb)

# Or use VS Code/PyCharm built-in debugger
```

### Docker Debugging

```bash
# Attach to running container
docker exec -it sentiment-dev bash

# View logs
docker logs -f sentiment-dev

# Inspect container
docker inspect sentiment-dev
```

### API Debugging

```bash
# Test endpoints with curl
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Debug this!"}'

# Use httpie (install: pip install httpie)
http POST :8000/predict text="Debug this!"

# Interactive API docs
open http://localhost:8000/docs
```

### Performance Profiling

```python
# Profile with cProfile
python -m cProfile -o profile.stats run.py

# View results
python -m pstats profile.stats
> sort cumtime
> stats 20

# Or use line_profiler
from line_profiler import LineProfiler

lp = LineProfiler()
lp.add_function(your_function)
lp.run('your_function()')
lp.print_stats()
```

---

## Common Tasks

### Adding a New API Endpoint

1. **Create route handler** in `app/api/routes/`:

```python
# app/api/routes/new_feature.py
from fastapi import APIRouter, Depends
from app.api.schemas.responses import NewFeatureResponse
from app.core.dependencies import get_settings

router = APIRouter()

@router.get("/new-feature", response_model=NewFeatureResponse)
async def new_feature(settings = Depends(get_settings)):
    """New feature endpoint."""
    return {"result": "success"}
```

2. **Add schemas** in `app/api/schemas/`:

```python
# app/api/schemas/responses.py
class NewFeatureResponse(BaseModel):
    result: str
```

3. **Register router** in `app/main.py`:

```python
from app.api.routes import new_feature

app.include_router(
    new_feature.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["new-feature"]
)
```

4. **Write tests**:

```python
# tests/test_new_feature.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_new_feature():
    response = client.get("/api/v1/new-feature")
    assert response.status_code == 200
    assert response.json()["result"] == "success"
```

### Adding a New ML Model Backend

1. **Implement ModelStrategy protocol**:

```python
# app/ml/tensorrt_analyzer.py
from app.ml.model_strategy import ModelStrategy
from typing import Dict, Any

class TensorRTAnalyzer:
    """TensorRT model implementation."""
    
    def is_ready(self) -> bool:
        return self._engine is not None
    
    def predict(self, text: str) -> Dict[str, Any]:
        # Implementation
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        # Implementation
        pass
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        # Implementation
        pass
```

2. **Update factory** in `app/ml/`:

```python
# Add to ModelBackend enum
class ModelBackend(str, Enum):
    PYTORCH = "pytorch"
    ONNX = "onnx"
    TENSORRT = "tensorrt"  # New

# Add factory method
def get_tensorrt_analyzer() -> TensorRTAnalyzer:
    return TensorRTAnalyzer()
```

### Converting Model to ONNX

```bash
# Use provided conversion script
python scripts/convert_to_onnx.py \
  --model-name distilbert-base-uncased-finetuned-sst-2-english \
  --output-path ./onnx_models/distilbert

# Test ONNX model
MLOPS_ONNX_MODEL_PATH=./onnx_models/distilbert python run.py
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

#### Model Download Fails

```bash
# Clear cache and retry
rm -rf ~/.cache/huggingface/
python run.py
```

#### Import Errors

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"

# Add current directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### Tests Failing Locally But Passing in CI

```bash
# Use same environment as CI
MLOPS_DEBUG=true MLOPS_LOG_LEVEL=DEBUG pytest

# Check Python version
python --version  # Should be 3.11+
```

### Getting Help

1. **Check logs**:
   ```bash
   tail -f logs/app.log
   ```

2. **Check documentation**:
   - [Architecture](ARCHITECTURE.md)
   - [API Docs](http://localhost:8000/docs)
   - [Code Quality Guide](CODE_QUALITY_SETUP.md)

3. **Ask the team**:
   - Slack: #mlops-dev
   - Email: mlops-team@example.com

---

## Best Practices

### Do's ✓

- Write tests for all new features
- Use type hints everywhere
- Follow code style guidelines (Black, PEP 8)
- Keep functions small and focused
- Add docstrings to public functions
- Use dependency injection
- Log important events with correlation IDs
- Handle errors gracefully
- Update documentation when changing behavior

### Don'ts ✗

- Don't commit secrets or API keys
- Don't skip tests ("I'll add them later")
- Don't disable linters to make code pass
- Don't use global variables or singletons
- Don't hardcode configuration values
- Don't ignore security warnings
- Don't merge without code review
- Don't deploy on Friday afternoon

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/)
- [ONNX Runtime](https://onnxruntime.ai/docs/)

---

**Maintainers**: MLOps Development Team  
**Last Review**: October 2025  
**Next Review**: January 2026
