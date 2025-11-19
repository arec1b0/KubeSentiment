# CLAUDE.md - AI Assistant Guide for KubeSentiment

> **Last Updated:** 2025-11-19
> **Purpose:** This document provides AI assistants with comprehensive guidance on the KubeSentiment codebase structure, development workflows, and key conventions to follow when making contributions.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Architecture & Design Patterns](#architecture--design-patterns)
4. [Development Workflows](#development-workflows)
5. [Code Quality Standards](#code-quality-standards)
6. [Testing Strategy](#testing-strategy)
7. [Configuration Management](#configuration-management)
8. [Deployment & Infrastructure](#deployment--infrastructure)
9. [Key Conventions](#key-conventions)
10. [Common Tasks](#common-tasks)
11. [Important Files & Locations](#important-files--locations)
12. [ADR References](#adr-references)

---

## Project Overview

**KubeSentiment** is a production-grade, cloud-native MLOps microservice for sentiment analysis built with FastAPI. It demonstrates modern MLOps best practices including observability, scalability, security, and automation.

### Core Technologies

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **ML Models:** DistilBERT (Hugging Face Transformers)
- **Inference:** ONNX Runtime (production), PyTorch (development)
- **Orchestration:** Kubernetes with Helm
- **Caching:** Redis
- **Async Processing:** Kafka
- **Infrastructure:** Terraform (multi-cloud)
- **Observability:** Prometheus, Grafana, OpenTelemetry
- **Secrets:** HashiCorp Vault
- **CI/CD:** GitHub Actions, GitLab CI

### Key Features

- High-performance AI inference with ONNX optimization (160x faster cold-start)
- GPU acceleration with multi-GPU support
- Cloud-native Kubernetes deployment with auto-scaling
- Full observability stack (metrics, logs, traces)
- Infrastructure as Code (Terraform)
- Comprehensive benchmarking suite
- Chaos engineering capabilities
- Profile-based configuration system

---

## Repository Structure

```
KubeSentiment/
├── app/                          # Main application code
│   ├── api/                      # API routes and endpoints
│   │   ├── routes/               # Individual route modules
│   │   └── dependencies.py       # Dependency injection
│   ├── core/                     # Core application logic
│   │   ├── config/               # Profile-based configuration
│   │   ├── logging.py            # Structured logging setup
│   │   └── security.py           # Security utilities
│   ├── features/                 # Feature modules
│   ├── interfaces/               # Abstract interfaces/protocols
│   ├── models/                   # ML model implementations
│   │   ├── base.py               # Base model interface
│   │   ├── pytorch_sentiment.py  # PyTorch backend
│   │   ├── onnx_sentiment.py     # ONNX backend
│   │   └── factory.py            # Model factory pattern
│   ├── services/                 # Business logic services
│   ├── monitoring/               # Monitoring and metrics
│   ├── utils/                    # Utility functions
│   └── main.py                   # FastAPI application factory
│
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests (fast, isolated)
│   ├── integration/              # Integration tests
│   ├── performance/              # Performance tests
│   └── fixtures/                 # Test fixtures
│
├── docs/                         # Documentation
│   ├── architecture/             # Architecture documentation
│   │   └── decisions/            # ADRs (Architecture Decision Records)
│   ├── setup/                    # Setup and deployment guides
│   └── troubleshooting/          # Troubleshooting guides
│
├── infrastructure/               # IaC (Terraform)
│   ├── modules/                  # Reusable Terraform modules
│   └── environments/             # Environment-specific configs
│
├── helm/                         # Kubernetes Helm charts
│   └── mlops-sentiment/          # Main Helm chart
│       ├── templates/            # K8s resource templates
│       └── values*.yaml          # Environment-specific values
│
├── k8s/                          # Raw Kubernetes manifests
│
├── config/                       # Configuration files
│   ├── prometheus.yml            # Prometheus config
│   ├── grafana-*.json            # Grafana dashboards
│   └── alertmanager.yml          # Alert configuration
│
├── benchmarking/                 # Performance benchmarking
│   ├── scripts/                  # Benchmark scripts
│   └── configs/                  # Benchmark configurations
│
├── chaos/                        # Chaos engineering
│   ├── chaos-mesh/               # Chaos Mesh experiments
│   ├── litmus/                   # Litmus experiments
│   └── scripts/                  # Chaos test scripts
│
├── notebooks/                    # Jupyter notebooks
│   ├── experiments/              # ML experiments
│   ├── production/               # Production analysis
│   └── tutorials/                # Tutorial notebooks
│
├── scripts/                      # Utility scripts
│
├── sdk/                          # Client SDKs
│   ├── python/                   # Python SDK
│   └── javascript/               # JavaScript SDK
│
├── serverless/                   # Serverless deployments
│   ├── aws-lambda/               # AWS Lambda functions
│   └── google-cloud-run/         # Google Cloud Run
│
├── .github/                      # GitHub-specific files
│   ├── workflows/                # GitHub Actions workflows
│   └── copilot-instructions.md   # GitHub Copilot instructions
│
├── Makefile                      # Development commands
├── pyproject.toml                # Python project config & tools
├── requirements*.txt             # Python dependencies
├── docker-compose*.yml           # Docker Compose configs
├── Dockerfile                    # Production Docker image
├── Dockerfile.optimized          # Optimized Docker image
├── .gitlab-ci.yml                # GitLab CI pipeline
└── .pre-commit-config.yaml       # Pre-commit hooks
```

---

## Architecture & Design Patterns

### Application Architecture

KubeSentiment follows a **modular, layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────┐
│           FastAPI Application               │
├─────────────────────────────────────────────┤
│  API Layer (Routes & Endpoints)             │
│  - /api/v1/predict                          │
│  - /api/v1/health                           │
│  - /api/v1/metrics                          │
│  - /api/v1/batch/*                          │
├─────────────────────────────────────────────┤
│  Service Layer (Business Logic)             │
│  - Prediction Service                       │
│  - Batch Processing Service                 │
│  - Cache Service                            │
├─────────────────────────────────────────────┤
│  Model Layer (ML Models)                    │
│  - PyTorch Backend                          │
│  - ONNX Backend                             │
│  - Model Factory                            │
├─────────────────────────────────────────────┤
│  Infrastructure Layer                       │
│  - Redis (Caching)                          │
│  - Kafka (Async Processing)                 │
│  - Vault (Secrets)                          │
│  - Prometheus (Metrics)                     │
└─────────────────────────────────────────────┘
```

### Design Patterns Used

1. **Factory Pattern**: Model loading (`app/models/factory.py`)
2. **Strategy Pattern**: Multiple model backends (ONNX, PyTorch, Mock)
3. **Dependency Injection**: FastAPI dependencies for services and config
4. **Singleton Pattern**: Settings and model instances cached at startup
5. **Repository Pattern**: Abstract interfaces for storage and caching
6. **Circuit Breaker**: Resilience for external service calls
7. **Observer Pattern**: Event-driven Kafka consumers

### API Design

- **Versioned API**: All endpoints prefixed with `/api/v1` (production)
- **Debug Mode**: In development, prefix omitted for easier testing
- **RESTful**: Follows REST principles for resource naming
- **Pydantic Validation**: All inputs/outputs validated with Pydantic models
- **OpenAPI/Swagger**: Auto-generated documentation at `/docs`

---

## Development Workflows

### Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/arec1b0/KubeSentiment.git
cd KubeSentiment

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
make install-dev
# Or manually:
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -r requirements-test.txt

# 4. Install pre-commit hooks (IMPORTANT)
pre-commit install

# 5. Run locally with Docker Compose
docker-compose up --build

# 6. Or run directly with uvicorn (hot-reload)
PROFILE=local uvicorn app.main:app --reload
```

### Branch Strategy

- **main/master**: Production-ready code
- **develop**: Integration branch for features
- **feature/***: Feature branches
- **bugfix/***: Bug fix branches
- **hotfix/***: Critical production fixes

### Git Workflow

1. Create feature branch from `develop`
2. Make changes following conventions
3. Run tests and linters locally (`make lint`, `make test`)
4. Commit with conventional commit messages
5. Push and create PR to `develop`
6. Await CI/CD checks and code review
7. Merge after approval

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes

**Examples:**
```
feat(api): add batch prediction endpoint
fix(model): resolve ONNX model loading issue
docs(adr): add ADR for profile-based configuration
test(api): add unit tests for health endpoint
refactor(config): simplify settings structure
```

---

## Code Quality Standards

### Python Style Guide

- **Python Version**: 3.11+
- **Line Length**: 100 characters
- **Style Guide**: PEP 8
- **Type Hints**: Required for all functions
- **Docstrings**: Google or NumPy style

### Code Quality Tools

| Tool | Purpose | Config File |
|------|---------|-------------|
| **Black** | Code formatting | `pyproject.toml` |
| **isort** | Import sorting | `pyproject.toml` |
| **Ruff** | Fast linting | `pyproject.toml` |
| **mypy** | Type checking | `pyproject.toml` |
| **Bandit** | Security scanning | `pyproject.toml` |
| **Radon** | Complexity analysis | `pyproject.toml` |
| **pre-commit** | Git hooks | `.pre-commit-config.yaml` |

### Running Code Quality Checks

```bash
# Format code
make format

# Run all linters
make lint

# Check complexity
make complexity

# Run security scan
bandit -r app/ -c pyproject.toml

# Run all checks before commit
pre-commit run --all-files
```

### Code Quality Requirements

- **Test Coverage**: ≥ 80% (target: 90%+)
- **Complexity**: Cyclomatic complexity ≤ 10
- **Type Coverage**: 100% of functions must have type hints
- **Security**: No high-severity Bandit findings
- **Import Organization**: isort profile: black

---

## Testing Strategy

### Test Organization

Tests are organized by type with pytest markers:

```python
@pytest.mark.unit          # Fast, isolated, heavily mocked
@pytest.mark.integration   # Test component interactions
@pytest.mark.performance   # Performance/benchmark tests
@pytest.mark.e2e           # End-to-end system tests
@pytest.mark.slow          # Long-running tests
```

### Test Structure

```python
"""Module docstring explaining what is tested."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.models.pytorch_sentiment import SentimentAnalyzer


@pytest.fixture
def mock_analyzer():
    """Fixture docstring."""
    analyzer = Mock(spec=SentimentAnalyzer)
    analyzer.predict.return_value = {
        "label": "POSITIVE",
        "score": 0.95,
        "inference_time_ms": 150.0,
    }
    return analyzer


@pytest.mark.unit
class TestPredictEndpoint:
    """Test class for /predict endpoint."""

    def test_predict_success(self, client, mock_analyzer):
        """Test successful prediction."""
        response = client.post("/predict", json={"text": "I love this!"})

        assert response.status_code == 200
        data = response.json()
        assert "label" in data
        assert "score" in data
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only
pytest -m "not slow"              # Skip slow tests

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_api.py

# Run specific test
pytest tests/unit/test_api.py::TestPredictEndpoint::test_predict_success
```

### Test Coverage Requirements

- **Unit Tests**: 90%+ coverage
- **Integration Tests**: Critical paths covered
- **Performance Tests**: Baseline benchmarks established
- **E2E Tests**: Happy path scenarios covered

---

## Configuration Management

### Profile-Based Configuration System

KubeSentiment uses a **profile-based configuration system** (ADR-009) with modular domain-specific settings.

#### Configuration Profiles

| Profile | Use Case | Defaults |
|---------|----------|----------|
| `local` | Developer laptop | Mock model, no Redis/Kafka, hot-reload |
| `development` | Shared dev env | ONNX model, Redis/Kafka enabled |
| `staging` | Pre-production | Production settings, lower resources |
| `production` | Production | ONNX model, all features enabled |

#### Configuration Hierarchy (Priority)

1. **Profile Defaults** (lowest priority)
2. **.env file**
3. **Environment Variables**
4. **Vault Secrets** (highest priority)

#### Environment Variables

All settings use the `MLOPS_` prefix:

```bash
# Profile selection
PROFILE=production

# Server settings
MLOPS_SERVER_HOST=0.0.0.0
MLOPS_SERVER_PORT=8000
MLOPS_SERVER_WORKERS=4

# Model settings
MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
MLOPS_MODEL_BACKEND=onnx
MLOPS_MODEL_CACHE_DIR=/app/models

# Redis settings
MLOPS_REDIS_HOST=localhost
MLOPS_REDIS_PORT=6379
MLOPS_REDIS_ENABLED=true

# Kafka settings
MLOPS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
MLOPS_KAFKA_ENABLED=true
```

#### Accessing Configuration

```python
from app.core.config import get_settings

settings = get_settings()

# Access nested settings
print(settings.server.host)
print(settings.model.backend)
print(settings.redis.url)
```

### Environment Templates

- `.env.local.template` - Local development
- `.env.development.template` - Development environment
- `.env.staging.template` - Staging environment
- `.env.production.template` - Production environment

---

## Deployment & Infrastructure

### Docker

#### Building Images

```bash
# Standard build
docker build -t sentiment-service:latest .

# Optimized build
docker build -f Dockerfile.optimized -t sentiment-service:optimized .

# Build with specific backend
docker build --build-arg MODEL_BACKEND=onnx -t sentiment-service:onnx .
```

#### Docker Compose

```bash
# Start all services
docker-compose up -d

# With observability stack
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# With Kafka
docker-compose -f docker-compose.yml -f docker-compose.kafka.yml up -d
```

### Kubernetes

#### Helm Deployment

```bash
# Install to dev environment
make deploy-dev

# Install to staging
make deploy-staging

# Manual installation
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-sentiment \
  --create-namespace \
  --values ./helm/mlops-sentiment/values-production.yaml \
  --set image.tag=latest
```

#### GPU Support

For GPU-enabled deployments:

```bash
# Install with GPU support
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --values ./helm/mlops-sentiment/values-gpu.yaml
```

See: `helm/mlops-sentiment/README-GPU.md`

### Infrastructure as Code

#### Terraform

```bash
cd infrastructure/environments/production

# Initialize
terraform init

# Plan
terraform plan

# Apply
terraform apply

# Destroy
terraform destroy
```

#### Supported Cloud Providers

- AWS (requirements-aws.txt)
- GCP (requirements-gcp.txt)
- Azure (requirements-azure.txt)

---

## Key Conventions

### Logging Standards

#### Structured Logging (Application Code)

**ALWAYS use structured logging with keyword arguments:**

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# ✅ CORRECT - Structured logging
logger.info("User authenticated", user_id=user.id, method="oauth")
logger.error("Database connection failed",
             error=str(e),
             database="postgres",
             exc_info=True)

# ❌ INCORRECT - F-strings (DO NOT USE)
logger.info(f"User {user.id} authenticated")  # DON'T DO THIS
logger.error(f"Failed: {str(e)}")             # DON'T DO THIS
```

#### Standard Logging (Scripts)

For standalone scripts:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Use 'extra' parameter for structured data
logger.info("Migration started", extra={"environment": "prod"})
```

#### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General information about application flow
- **WARNING**: Unexpected but recoverable situations
- **ERROR**: Error occurred but app continues
- **CRITICAL**: Critical error causing app failure

### API Endpoint Conventions

#### Endpoint Naming

- Use **nouns** for resources: `/predictions`, `/models`, `/health`
- Use **plural** for collections: `/predictions` not `/prediction`
- Use **kebab-case**: `/model-info` not `/modelInfo`
- Nest resources: `/batch/results/{job_id}`

#### Request/Response Models

```python
from pydantic import BaseModel, Field

class PredictionRequest(BaseModel):
    """Request schema for predictions."""
    text: str = Field(..., min_length=1, max_length=5000)

class PredictionResponse(BaseModel):
    """Response schema for predictions."""
    label: str
    score: float = Field(..., ge=0.0, le=1.0)
    inference_time_ms: float
    model_name: str
    cached: bool = False
```

### Error Handling

#### Custom Exceptions

```python
from app.core.exceptions import ModelNotLoadedError, InferenceError

class ModelNotLoadedError(Exception):
    """Raised when model is not loaded."""
    pass

# Usage
if not self.model:
    raise ModelNotLoadedError("Model must be loaded before inference")
```

#### API Error Responses

```python
from fastapi import HTTPException, status

# Bad request
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid input text"
)

# Service unavailable
raise HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Model not available"
)
```

### Security Best Practices

1. **Never commit secrets**: Use environment variables or Vault
2. **Never log sensitive data**: No passwords, API keys, or PII
3. **Validate all inputs**: Use Pydantic models for validation
4. **Use HTTPS**: Always in production
5. **Implement rate limiting**: Protect against abuse
6. **Enable CORS properly**: Only allow trusted origins
7. **Use security headers**: CSP, HSTS, X-Frame-Options
8. **Scan for vulnerabilities**: Use Bandit, Trivy

---

## Common Tasks

### Adding a New API Endpoint

1. **Create route file**: `app/api/routes/my_feature.py`

```python
from fastapi import APIRouter, Depends
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["my-feature"])

@router.post("/my-endpoint")
async def my_endpoint(
    request: MyRequest,
    settings = Depends(get_settings)
):
    """Endpoint docstring."""
    # Implementation
    return {"result": "success"}
```

2. **Register router**: Add to `app/main.py`

```python
from app.api.routes import my_feature

app.include_router(my_feature.router)
```

3. **Add tests**: `tests/unit/test_my_feature.py`

### Adding a New Configuration Domain

1. **Create settings file**: `app/core/config/my_domain.py`

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class MyDomainSettings(BaseSettings):
    """My domain configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MLOPS_MYDOMAIN_",
        case_sensitive=True
    )

    setting_name: str = Field(
        default="default_value",
        description="Setting description"
    )
```

2. **Add to main settings**: `app/core/config/settings.py`

```python
from .my_domain import MyDomainSettings

class Settings(BaseConfig):
    my_domain: MyDomainSettings = Field(default_factory=MyDomainSettings)
```

### Adding a New ADR

1. **Create ADR file**: `docs/architecture/decisions/NNN-title.md`
2. **Use template**: Follow existing ADR structure
3. **Update index**: Add entry to `docs/architecture/decisions/README.md`
4. **Link related ADRs**: Reference in "Related ADRs" section

### Running Benchmarks

```bash
# Quick benchmark
make benchmark

# Full benchmarking suite
cd benchmarking
./run_benchmarks.sh

# Kafka performance test
python benchmarking/kafka_performance_test.py
```

### Chaos Engineering

```bash
# Install chaos tools
make chaos-install

# Run pod kill experiment
make chaos-test-pod-kill CHAOS_NAMESPACE=default

# Run network partition experiment
make chaos-test-network-partition

# Run full chaos suite
make chaos-test-suite

# Clean up experiments
make chaos-cleanup
```

---

## Important Files & Locations

### Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python project config, tool settings |
| `Makefile` | Common development commands |
| `.pre-commit-config.yaml` | Pre-commit hook configuration |
| `.flake8` | Flake8 linter configuration |
| `.editorconfig` | Editor settings for consistency |
| `.coveragerc` | Test coverage configuration |

### Core Application Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application factory |
| `app/core/config/settings.py` | Main settings aggregator |
| `app/core/logging.py` | Structured logging setup |
| `app/models/factory.py` | Model factory pattern |
| `app/models/base.py` | Base model interface |

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `CONTRIBUTING.md` | Contribution guidelines |
| `docs/architecture/decisions/README.md` | ADR index |
| `.github/copilot-instructions.md` | GitHub Copilot instructions |
| `IMPLEMENTATION_SUMMARY.md` | Implementation overview |

### Infrastructure Files

| File | Purpose |
|------|---------|
| `helm/mlops-sentiment/values.yaml` | Default Helm values |
| `helm/mlops-sentiment/values-production.yaml` | Production Helm values |
| `infrastructure/modules/` | Terraform modules |
| `k8s/` | Raw Kubernetes manifests |

---

## ADR References

Architecture Decision Records (ADRs) document key architectural decisions. Always review relevant ADRs before making architectural changes.

### Key ADRs

| ADR | Title | Summary |
|-----|-------|---------|
| [001](docs/architecture/decisions/001-use-onnx-for-model-optimization.md) | Use ONNX for Model Optimization | ONNX Runtime for 160x faster cold-start and 40% faster inference |
| [002](docs/architecture/decisions/002-use-redis-for-distributed-caching.md) | Use Redis for Distributed Caching | Redis for distributed cache with LRU eviction |
| [003](docs/architecture/decisions/003-use-kafka-for-async-processing.md) | Use Kafka for Async Message Processing | Kafka for high-throughput async batch processing |
| [004](docs/architecture/decisions/004-use-fastapi-as-web-framework.md) | Use FastAPI as Web Framework | FastAPI for async, type-safe API framework |
| [005](docs/architecture/decisions/005-use-helm-for-kubernetes-deployments.md) | Use Helm for Kubernetes Deployments | Helm for templated K8s deployments |
| [006](docs/architecture/decisions/006-use-hashicorp-vault-for-secrets.md) | Use HashiCorp Vault for Secrets Management | Vault for centralized secrets management |
| [007](docs/architecture/decisions/007-three-pillars-of-observability.md) | Implement Three Pillars of Observability | Metrics, logs, traces for full observability |
| [008](docs/architecture/decisions/008-use-terraform-for-iac.md) | Use Terraform for Multi-Cloud IaC | Terraform for cloud-agnostic infrastructure |
| [009](docs/architecture/decisions/009-profile-based-configuration.md) | Implement Profile-Based Configuration System | Modular, profile-based configuration with Pydantic |

### ADR Template Location

`docs/architecture/decisions/TEMPLATE.md`

---

## AI Assistant Guidelines

### When Making Changes

1. **Read relevant ADRs** before architectural changes
2. **Follow logging conventions** (structured logging with kwargs)
3. **Use type hints** for all functions
4. **Write tests** for new code (aim for 90%+ coverage)
5. **Update documentation** when adding features
6. **Run linters** before committing (`make lint`)
7. **Use conventional commits** for clear history
8. **Check security** with Bandit for sensitive code
9. **Consider observability** - add metrics/logs for critical paths
10. **Validate configuration** - test with different profiles

### When Analyzing Code

- Look for patterns documented in this file
- Check ADRs for context on architectural decisions
- Review `CONTRIBUTING.md` for contribution guidelines
- Examine existing tests for testing patterns
- Check `.github/copilot-instructions.md` for additional context

### Anti-Patterns to Avoid

❌ **DON'T:**
- Use f-strings in logging
- Hardcode secrets or credentials
- Skip input validation
- Write tests without fixtures
- Create files without reading existing code
- Ignore type hints
- Skip documentation updates
- Commit without running linters
- Use synchronous code where async is needed
- Deploy without monitoring

✅ **DO:**
- Use structured logging with keyword arguments
- Use environment variables for configuration
- Validate all inputs with Pydantic
- Use pytest fixtures for test setup
- Read existing code for patterns
- Add type hints to all functions
- Update docs when adding features
- Run `make lint` and `make test` before committing
- Use async/await for I/O operations
- Add metrics and logs for new features

---

## Quick Reference

### Essential Commands

```bash
# Development
make install-dev              # Install dev dependencies
make format                   # Format code with Black & isort
make lint                     # Run all linters
make test                     # Run tests with coverage
make dev                      # Start dev server with Docker Compose

# Build & Deploy
make build                    # Build Docker image
make deploy-dev               # Deploy to dev environment
make deploy-staging           # Deploy to staging

# Code Quality
make complexity               # Check code complexity
pre-commit run --all-files    # Run pre-commit hooks

# Chaos Engineering
make chaos-install            # Install chaos tools
make chaos-test-suite         # Run chaos test suite
make chaos-cleanup            # Clean up experiments

# Benchmarking
make benchmark                # Run benchmarks
```

### Important URLs (Local Development)

- Application: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health
- Metrics: http://localhost:8000/api/v1/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Alertmanager: http://localhost:9093

### Key Environment Variables

```bash
PROFILE=local|development|staging|production
MLOPS_MODEL_BACKEND=onnx|pytorch|mock
MLOPS_SERVER_PORT=8000
MLOPS_REDIS_ENABLED=true
MLOPS_KAFKA_ENABLED=true
MLOPS_DEBUG=false
```

---

## Getting Help

- **Documentation**: See `docs/` directory
- **ADRs**: See `docs/architecture/decisions/`
- **Contributing**: See `CONTRIBUTING.md`
- **Issues**: Check GitHub/GitLab issues
- **Code Examples**: Look at existing code patterns
- **Makefile**: Run `make help` for available commands

---

## Version History

| Date | Changes |
|------|---------|
| 2025-11-19 | Initial CLAUDE.md creation - comprehensive guide for AI assistants |

---

**Note**: This document should be updated whenever significant architectural changes or new patterns are introduced. When in doubt, follow the patterns established in existing code and documented in ADRs.
