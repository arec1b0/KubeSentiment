# AGENTS.md - AI Agent Guide for KubeSentiment

> **Last Updated:** 2025-12-04  
> **Purpose:** This document provides AI agents with a comprehensive understanding of the KubeSentiment project, including its architecture, subsystems, build commands, and development workflows.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Architecture](#project-architecture)
3. [High-Level Subsystems](#high-level-subsystems)
4. [Directory Structure](#directory-structure)
5. [Build & Development Commands](#build--development-commands)
6. [Configuration & Deployment](#configuration--deployment)
7. [Testing & Quality](#testing--quality)
8. [Key Conventions](#key-conventions)
9. [Related Documentation](#related-documentation)

---

## Project Overview

**KubeSentiment** is a production-ready, cloud-native MLOps sentiment analysis microservice built with FastAPI and designed for Kubernetes deployments.

### Core Purpose

Provides real-time sentiment analysis using state-of-the-art transformer models (DistilBERT) with enterprise-grade features including:
- High-performance inference with ONNX optimization (160x faster cold-start)
- GPU acceleration and multi-GPU support (800-3000 req/s per GPU)
- Distributed caching, async batch processing, and auto-scaling
- Full observability stack (Prometheus, Grafana, OpenTelemetry)
- Infrastructure as Code with Terraform
- Chaos engineering and comprehensive benchmarking

### Technology Stack

| Category | Technologies |
|----------|-------------|
| **Language** | Python 3.11+ |
| **Framework** | FastAPI, Uvicorn |
| **ML Models** | DistilBERT (Hugging Face Transformers), PyTorch, ONNX Runtime |
| **Caching** | Redis |
| **Message Queue** | Kafka |
| **Orchestration** | Kubernetes, Helm |
| **IaC** | Terraform (multi-cloud: AWS, GCP, Azure) |
| **Observability** | Prometheus, Grafana, OpenTelemetry, Structlog |
| **Secrets** | HashiCorp Vault |
| **CI/CD** | GitHub Actions, GitLab CI |
| **Security** | Trivy, Bandit |
| **Containers** | Docker (standard, optimized, distroless variants) |

---

## Project Architecture

### Application Architecture

KubeSentiment follows a **modular, layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│           FastAPI Application (app/main.py)             │
├─────────────────────────────────────────────────────────┤
│  Middleware Layer                                       │
│  - CorrelationIdMiddleware                              │
│  - RequestLoggingMiddleware                             │
│  - CORSMiddleware                                       │
│  - APIKeyAuthMiddleware                                 │
│  - MetricsMiddleware (Prometheus)                       │
├─────────────────────────────────────────────────────────┤
│  API Layer (app/api/routes/)                            │
│  - /api/v1/predict       - Real-time predictions        │
│  - /api/v1/batch/*       - Async batch processing       │
│  - /api/v1/health        - Health checks                │
│  - /api/v1/metrics       - Prometheus metrics           │
│  - /api/v1/model-info    - Model metadata               │
│  - Advanced monitoring routes (drift, MLflow, etc.)     │
├─────────────────────────────────────────────────────────┤
│  Service Layer (app/services/)                          │
│  - PredictionService         - Core inference           │
│  - AsyncBatchService         - Batch job management     │
│  - RedisCacheService         - Distributed caching      │
│  - KafkaConsumer             - Message processing       │
│  - DriftDetection            - Model drift monitoring   │
│  - ExplainabilityService     - Model interpretability   │
│  - MLflowRegistry            - Model registry           │
│  - GPUBatchOptimizer         - GPU batch optimization   │
├─────────────────────────────────────────────────────────┤
│  Model Layer (app/models/)                              │
│  - factory.py                - Model factory pattern    │
│  - base.py                   - Base model interface     │
│  - pytorch_sentiment.py      - PyTorch backend          │
│  - onnx_sentiment.py         - ONNX backend             │
│  - batch_job.py              - Batch processing models  │
├─────────────────────────────────────────────────────────┤
│  Infrastructure Layer (external services)               │
│  - Redis                     - Caching                  │
│  - Kafka                     - Async messaging          │
│  - HashiCorp Vault           - Secrets management       │
│  - Prometheus                - Metrics collection       │
│  - OpenTelemetry             - Distributed tracing      │
└─────────────────────────────────────────────────────────┘
```

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│               Kubernetes Cluster                        │
├─────────────────────────────────────────────────────────┤
│  Ingress Controller                                     │
│         ↓                                               │
│  Service (LoadBalancer)                                 │
│         ↓                                               │
│  Sentiment Analysis Pods (HPA enabled)                  │
│  - FastAPI containers                                   │
│  - GPU support (optional)                               │
│  - Auto-scaling based on metrics                        │
├─────────────────────────────────────────────────────────┤
│  Supporting Services                                    │
│  - Redis (caching)                                      │
│  - Kafka (message queue)                                │
│  - HashiCorp Vault (secrets)                            │
├─────────────────────────────────────────────────────────┤
│  Observability Stack                                    │
│  - Prometheus (metrics scraping)                        │
│  - Grafana (dashboards)                                 │
│  - Alertmanager (alerts)                                │
│  - OpenTelemetry Collector (traces)                     │
└─────────────────────────────────────────────────────────┘
```

---

## High-Level Subsystems

### 1. API Layer (`app/api/`)

**Purpose:** HTTP API endpoints and request/response handling

**Key Components:**
- `routes/predictions.py` - Real-time sentiment predictions
- `routes/async_batch.py` - Batch job submission and retrieval
- `routes/model_info.py` - Model metadata endpoints
- `routes/monitoring_routes.py` - Advanced monitoring (drift, explainability)
- `middleware/` - Request processing middleware (auth, logging, metrics, correlation)
- `schemas/` - Pydantic request/response models

**Design Patterns:**
- RESTful API design with versioning (`/api/v1`)
- Pydantic validation for all inputs/outputs
- Dependency injection for services and config
- Middleware chain for cross-cutting concerns

### 2. Core Layer (`app/core/`)

**Purpose:** Application configuration, logging, secrets, and lifecycle management

**Key Components:**
- `config/` - Profile-based configuration system (ADR-009)
  - `settings.py` - Main settings aggregator
  - `profiles.py` - Environment profiles (local, dev, staging, prod)
  - Domain-specific configs: `server.py`, `model.py`, `redis.py`, `kafka.py`, etc.
- `logging.py` - Structured logging with structlog
- `tracing.py` - OpenTelemetry distributed tracing
- `secrets.py` - HashiCorp Vault integration
- `events.py` - FastAPI lifespan event handlers
- `dependencies.py` - Dependency injection setup

**Configuration Profiles:**

| Profile | Use Case | Defaults |
|---------|----------|----------|
| `local` | Developer laptop | Mock model, no Redis/Kafka, hot-reload |
| `development` | Shared dev env | PyTorch model, Redis/Kafka optional |
| `staging` | Pre-production | ONNX model, Redis/Vault enabled |
| `production` | Production | ONNX model, all services enabled, optimized |

### 3. Models Layer (`app/models/`)

**Purpose:** ML model implementations and loading logic

**Key Components:**
- `base.py` - Abstract base interface for models
- `factory.py` - Factory pattern for model instantiation
- `pytorch_sentiment.py` - PyTorch-based inference
- `onnx_sentiment.py` - ONNX Runtime inference (production)
- `batch_job.py` - Batch processing data models
- `persistence.py` - Model persistence utilities

**Supported Backends:**
- **PyTorch**: Development and experimentation
- **ONNX**: Production (160x faster cold-start, 40% faster inference)
- **Mock**: Testing and local development

### 4. Services Layer (`app/services/`)

**Purpose:** Business logic and external service integrations

**Key Services:**

| Service | Purpose |
|---------|---------|
| `prediction.py` | Core sentiment analysis service |
| `async_batch_service.py` | Asynchronous batch job orchestration |
| `redis_cache.py` | Distributed caching with Redis |
| `kafka_consumer.py` | Kafka message consumption |
| `distributed_kafka_consumer.py` | High-throughput Kafka consumer |
| `drift_detection.py` | Model drift monitoring |
| `explainability.py` | Model interpretability (SHAP, LIME) |
| `mlflow_registry.py` | MLflow model registry integration |
| `gpu_batch_optimizer.py` | GPU batch optimization |
| `dead_letter_queue.py` | Failed message handling |
| `load_balancer.py` | Multi-GPU load balancing |

### 5. Features Layer (`app/features/`)

**Purpose:** Feature engineering and data processing

**Key Components:**
- `feature_engineering.py` - Feature transformation pipelines
- `online_normalization.py` - Real-time feature normalization

### 6. Interfaces Layer (`app/interfaces/`)

**Purpose:** Abstract interfaces and protocols for dependency inversion

**Key Interfaces:**
- `prediction_interface.py` - Prediction service contract
- `cache_interface.py` - Caching abstraction
- `kafka_interface.py` - Message queue abstraction
- `drift_interface.py` - Drift detection contract
- `explainability_interface.py` - Explainability contract
- `batch_interface.py` - Batch processing contract
- `storage_interface.py` - Storage abstraction

### 7. Monitoring Layer (`app/monitoring/`)

**Purpose:** Observability, metrics, and health checks

**Key Components:**
- Prometheus metrics exporters
- Health check endpoints
- Performance monitoring
- System metrics (CPU, memory, GPU)
- Model metrics (latency, throughput, accuracy)

### 8. Infrastructure Layer (`infrastructure/`)

**Purpose:** Terraform modules for cloud infrastructure

**Structure:**
```
infrastructure/
├── modules/          # Reusable Terraform modules
├── environments/     # Environment-specific configurations
│   ├── production/
│   ├── staging/
│   └── development/
└── providers.tf      # Cloud provider configurations
```

**Supported Clouds:**
- AWS (EKS, EC2, S3, CloudWatch)
- GCP (GKE, Compute Engine, Cloud Storage)
- Azure (AKS, VMs, Blob Storage)

### 9. Kubernetes Layer (`helm/`, `k8s/`)

**Purpose:** Kubernetes deployment configurations

**Helm Chart (`helm/mlops-sentiment/`):**
- `templates/` - K8s resource templates
- `values.yaml` - Default configuration values
- `values-dev.yaml`, `values-staging.yaml`, `values-production.yaml` - Environment overrides
- `values-gpu.yaml` - GPU-enabled configurations

**Features:**
- Horizontal Pod Autoscaling (HPA)
- GPU scheduling and resource allocation
- Network policies
- ConfigMaps and Secrets
- Service mesh integration
- Liveness and readiness probes

### 10. Benchmarking Layer (`benchmarking/`)

**Purpose:** Performance testing and analysis

**Capabilities:**
- CPU vs GPU performance comparisons
- Cost-effectiveness analysis
- Load testing (800-3000 req/s per GPU)
- Kafka throughput benchmarks (105,700 msg/s)
- HTML report generation

### 11. Chaos Engineering Layer (`chaos/`)

**Purpose:** Resilience and fault injection testing

**Tools:**
- **Chaos Mesh** - Kubernetes-native chaos experiments
- **Litmus** - Chaos engineering platform

**Experiments:**
- Pod kill tests
- Network partition tests
- HPA stress tests
- Resource exhaustion tests

### 12. SDK Layer (`sdk/`)

**Purpose:** Client libraries for consuming the API

**Available SDKs:**
- Python (`sdk/python/`)
- JavaScript (`sdk/javascript/`)

### 13. Serverless Layer (`serverless/`)

**Purpose:** Alternative deployment targets

**Platforms:**
- AWS Lambda (`serverless/aws-lambda/`)
- Google Cloud Run (`serverless/google-cloud-run/`)

---

## Directory Structure

```
KubeSentiment/
├── app/                          # Main application code
│   ├── api/                      # API routes, middleware, schemas
│   │   ├── middleware/           # Custom middleware (auth, logging, metrics)
│   │   ├── routes/               # API endpoint implementations
│   │   └── schemas/              # Pydantic request/response models
│   ├── core/                     # Core application logic
│   │   ├── config/               # Profile-based configuration
│   │   ├── logging.py            # Structured logging
│   │   ├── tracing.py            # OpenTelemetry setup
│   │   └── secrets.py            # Vault integration
│   ├── features/                 # Feature engineering
│   ├── interfaces/               # Abstract interfaces/protocols
│   ├── models/                   # ML model implementations
│   │   ├── factory.py            # Model factory
│   │   ├── pytorch_sentiment.py  # PyTorch backend
│   │   └── onnx_sentiment.py     # ONNX backend
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
│   ├── configuration/            # Configuration guides
│   ├── setup/                    # Setup and deployment guides
│   └── troubleshooting/          # Troubleshooting guides
│
├── infrastructure/               # Terraform IaC
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
├── Dockerfile.distroless         # Distroless Docker image
├── .gitlab-ci.yml                # GitLab CI pipeline
├── .pre-commit-config.yaml       # Pre-commit hooks
├── README.md                     # Main project documentation
├── CONTRIBUTING.md               # Contribution guidelines
├── CLAUDE.md                     # AI assistant guide (detailed)
└── AGENTS.md                     # This file
```

---

## Build & Development Commands

### Essential Commands (from `Makefile`)

#### Installation & Setup

```bash
make install              # Install Python dependencies
make install-dev          # Install dev dependencies (includes test & dev tools)
make install-test         # Install testing dependencies only
make install-aws          # Install AWS-specific dependencies
make install-gcp          # Install GCP-specific dependencies
make install-azure        # Install Azure-specific dependencies
```

#### Development

```bash
make dev                  # Start development server with docker-compose
make build                # Build standard Docker image
make build-distroless     # Build distroless Docker image (production)
make build-distroless-debug  # Build distroless debug image (includes shell)
```

#### Code Quality

```bash
make format               # Format code (black + isort)
make lint                 # Run all linters (black, isort, ruff, mypy, bandit)
make lint-fix             # Auto-fix linting issues
make complexity           # Check code complexity metrics
```

#### Testing

```bash
make test                 # Run tests with coverage
pytest -m unit            # Run unit tests only
pytest -m integration     # Run integration tests only
pytest -m "not slow"      # Skip slow tests
```

#### Deployment

```bash
make deploy-dev           # Deploy to development environment
make deploy-staging       # Deploy to staging environment
```

#### Benchmarking

```bash
make benchmark            # Run benchmarking suite
```

#### Chaos Engineering

```bash
make chaos-install        # Install Chaos Mesh and Litmus tools
make chaos-test-pod-kill  # Run pod kill chaos experiment
make chaos-test-network-partition  # Run network partition experiment
make chaos-test-suite     # Run full chaos engineering test suite
make chaos-test-hpa       # Run HPA-specific chaos test
make chaos-cleanup        # Clean up all chaos experiments
make chaos-status         # Check chaos tools and experiment status
```

#### Utilities

```bash
make clean                # Clean up cache files and build artifacts
make docs                 # Generate documentation
make help                 # Show available commands
```

### Docker Commands

```bash
# Build images
docker build -t sentiment-service:latest .
docker build -f Dockerfile.optimized -t sentiment-service:optimized .
docker build -f Dockerfile.distroless -t sentiment-service:distroless .

# Run with Docker Compose
docker-compose up --build
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d
docker-compose -f docker-compose.yml -f docker-compose.kafka.yml up -d
```

### Kubernetes/Helm Commands

```bash
# Install with Helm
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-sentiment \
  --create-namespace \
  --values ./helm/mlops-sentiment/values-production.yaml

# GPU-enabled deployment
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --values ./helm/mlops-sentiment/values-gpu.yaml

# Port forward for local testing
kubectl port-forward svc/mlops-sentiment 8000:80
```

### Terraform Commands

```bash
cd infrastructure/environments/production
terraform init
terraform plan
terraform apply
terraform destroy
```

### Running the Application Directly

```bash
# Set profile
export MLOPS_PROFILE=development

# Run with uvicorn (hot-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python module
python -m uvicorn app.main:app --reload
```

---

## Configuration & Deployment

### Configuration System

KubeSentiment uses a **profile-based configuration system** (see ADR-009) with the following hierarchy:

1. **Profile Defaults** (lowest priority)
2. **.env file**
3. **Environment Variables**
4. **Vault Secrets** (highest priority)

### Environment Variables

All configuration uses the `MLOPS_` prefix:

```bash
# Core settings
MLOPS_PROFILE=production                      # Profile: local, development, staging, production
MLOPS_MODEL_BACKEND=onnx                      # Backend: onnx, pytorch, mock
MLOPS_SERVER_PORT=8000                        # Server port
MLOPS_DEBUG=false                             # Debug mode

# Model settings
MLOPS_MODEL_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
MLOPS_MODEL_DEVICE=cuda                       # Device: cpu, cuda

# Redis settings
MLOPS_REDIS_ENABLED=true
MLOPS_REDIS_HOST=localhost
MLOPS_REDIS_PORT=6379

# Kafka settings
MLOPS_KAFKA_ENABLED=true
MLOPS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Vault settings
MLOPS_VAULT_ENABLED=true
MLOPS_VAULT_URL=http://localhost:8200
```

### Deployment Environments

| Environment | Configuration File | Profile | Purpose |
|-------------|-------------------|---------|---------|
| Local | `.env.local.template` | `local` | Developer laptops |
| Development | `values-dev.yaml` | `development` | Shared dev environment |
| Staging | `values-staging.yaml` | `staging` | Pre-production testing |
| Production | `values-production.yaml` | `production` | Production deployment |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service information |
| `POST` | `/api/v1/predict` | Real-time sentiment prediction |
| `POST` | `/api/v1/batch/predict` | Submit batch prediction job |
| `GET` | `/api/v1/batch/status/{job_id}` | Check batch job status |
| `GET` | `/api/v1/batch/results/{job_id}` | Get batch job results |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/metrics` | Prometheus metrics |
| `GET` | `/api/v1/model-info` | Model metadata |

**Note:** In debug mode (`MLOPS_DEBUG=true`), the `/api/v1` prefix is omitted.

### Docker Image Variants

| Dockerfile | Target | Size | Use Case |
|------------|--------|------|----------|
| `Dockerfile` | Standard | ~2GB | Development, general use |
| `Dockerfile.optimized` | Optimized | ~1.2GB | Optimized production |
| `Dockerfile.distroless` | Distroless | ~800MB | Secure production (no shell) |
| `Dockerfile.distroless` (debug) | Distroless + debug | ~900MB | Debugging with tools |

---

## Testing & Quality

### Test Structure

Tests are organized by type with pytest markers:

```python
@pytest.mark.unit          # Fast, isolated, heavily mocked
@pytest.mark.integration   # Test component interactions
@pytest.mark.performance   # Performance/benchmark tests
@pytest.mark.e2e           # End-to-end system tests
@pytest.mark.slow          # Long-running tests
```

### Coverage Requirements

- **Unit Tests**: 90%+ coverage
- **Integration Tests**: Critical paths covered
- **Performance Tests**: Baseline benchmarks established
- **E2E Tests**: Happy path scenarios covered

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

### Quality Standards

- **Test Coverage**: ≥ 80% (target: 90%+)
- **Complexity**: Cyclomatic complexity ≤ 10
- **Type Coverage**: 100% of functions must have type hints
- **Security**: No high-severity Bandit findings
- **Line Length**: 100 characters (Black)

---

## Key Conventions

### Logging Standards

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
```

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
- `style`: Code formatting
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
```

### Security Best Practices

1. **Never commit secrets** - Use environment variables or Vault
2. **Never log sensitive data** - No passwords, API keys, or PII
3. **Validate all inputs** - Use Pydantic models
4. **Use HTTPS** - Always in production
5. **Implement rate limiting** - Protect against abuse
6. **Enable CORS properly** - Only allow trusted origins
7. **Use security headers** - CSP, HSTS, X-Frame-Options
8. **Scan for vulnerabilities** - Use Bandit, Trivy

### Design Patterns

1. **Factory Pattern**: Model loading (`app/models/factory.py`)
2. **Strategy Pattern**: Multiple model backends (ONNX, PyTorch, Mock)
3. **Dependency Injection**: FastAPI dependencies
4. **Singleton Pattern**: Settings and model instances
5. **Repository Pattern**: Abstract interfaces for storage
6. **Circuit Breaker**: Resilience for external services
7. **Observer Pattern**: Event-driven Kafka consumers

---

## Related Documentation

### Essential Reading

| Document | Purpose |
|----------|---------|
| `README.md` | Main project documentation, features, quickstart |
| `CLAUDE.md` | Detailed AI assistant guide with comprehensive conventions |
| `CONTRIBUTING.md` | Contribution guidelines and development setup |
| `.github/copilot-instructions.md` | GitHub Copilot-specific instructions |

### Architecture Decision Records (ADRs)

Key ADRs documenting major architectural decisions:

| ADR | Title | Impact |
|-----|-------|--------|
| [001](docs/architecture/decisions/001-use-onnx-for-model-optimization.md) | Use ONNX for Model Optimization | 160x faster cold-start, 40% faster inference |
| [002](docs/architecture/decisions/002-use-redis-for-distributed-caching.md) | Use Redis for Distributed Caching | Distributed cache with LRU eviction |
| [003](docs/architecture/decisions/003-use-kafka-for-async-processing.md) | Use Kafka for Async Message Processing | High-throughput async batch processing |
| [004](docs/architecture/decisions/004-use-fastapi-as-web-framework.md) | Use FastAPI as Web Framework | Async, type-safe API framework |
| [005](docs/architecture/decisions/005-use-helm-for-kubernetes-deployments.md) | Use Helm for Kubernetes Deployments | Templated K8s deployments |
| [006](docs/architecture/decisions/006-use-hashicorp-vault-for-secrets.md) | Use HashiCorp Vault for Secrets Management | Centralized secrets management |
| [007](docs/architecture/decisions/007-three-pillars-of-observability.md) | Implement Three Pillars of Observability | Metrics, logs, traces |
| [008](docs/architecture/decisions/008-use-terraform-for-iac.md) | Use Terraform for Multi-Cloud IaC | Cloud-agnostic infrastructure |
| [009](docs/architecture/decisions/009-profile-based-configuration.md) | Implement Profile-Based Configuration System | Modular, profile-based config |

See `docs/architecture/decisions/README.md` for the complete ADR index.

### Configuration Documentation

| Document | Purpose |
|----------|---------|
| [Quick Start](docs/configuration/QUICK_START.md) | Get running in 5 minutes |
| [Architecture](docs/configuration/ARCHITECTURE.md) | Configuration system design |
| [Profiles](docs/configuration/PROFILES.md) | Profile-based defaults |
| [Environment Variables](docs/configuration/ENVIRONMENT_VARIABLES.md) | Complete reference |
| [Deployment](docs/configuration/DEPLOYMENT.md) | Environment-specific configurations |
| [Examples](docs/configuration/examples/) | Copy-paste ready configurations |

### Additional Resources

- **Architecture**: `docs/architecture.md`
- **Benchmarking**: `benchmarking/README.md`
- **GPU Support**: `helm/mlops-sentiment/README-GPU.md`
- **Quickstart**: `docs/setup/QUICKSTART.md`
- **Troubleshooting**: `docs/troubleshooting/`

---

## Quick Reference

### Important URLs (Local Development)

- **Application**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **Metrics**: http://localhost:8000/api/v1/metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Alertmanager**: http://localhost:9093

### Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application factory |
| `app/core/config/settings.py` | Main settings aggregator |
| `app/models/factory.py` | Model factory pattern |
| `Makefile` | Development commands |
| `pyproject.toml` | Python project config |
| `docker-compose.yml` | Local development stack |

### Performance Benchmarks

| Metric | Value |
|--------|-------|
| **GPU Throughput** | 800-3000 req/s per GPU |
| **ONNX Cold-Start** | 160x faster than PyTorch |
| **ONNX Inference** | 40% faster than PyTorch |
| **Kafka Throughput** | ~105,700 msg/s (synthetic) |

---

## AI Agent Guidelines

### When Analyzing Code

1. **Read relevant ADRs** before architectural changes
2. **Review CLAUDE.md** for detailed conventions
3. **Check existing patterns** in similar modules
4. **Examine tests** for testing patterns
5. **Verify configuration** with different profiles

### When Making Changes

1. **Use structured logging** with keyword arguments (not f-strings)
2. **Add type hints** for all functions
3. **Write tests** for new code (aim for 90%+ coverage)
4. **Update documentation** when adding features
5. **Run linters** before committing (`make lint`)
6. **Follow conventional commits** for clear history
7. **Consider observability** - add metrics/logs for critical paths
8. **Validate security** with Bandit for sensitive code

### Anti-Patterns to Avoid

❌ **DON'T:**
- Use f-strings in logging
- Hardcode secrets or credentials
- Skip input validation
- Write tests without fixtures
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
- Add type hints to all functions
- Update docs when adding features
- Run `make lint` and `make test` before committing
- Use async/await for I/O operations
- Add metrics and logs for new features

---

## Version History

| Date | Changes |
|------|---------|
| 2025-12-04 | Initial AGENTS.md creation - comprehensive project overview for AI agents |

---

**Note**: This document should be updated whenever significant architectural changes are introduced. For detailed conventions and patterns, see `CLAUDE.md`. For contribution guidelines, see `CONTRIBUTING.md`.
