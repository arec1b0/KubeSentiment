# MLOps Sentiment Analysis Microservice

[![CI/CD Pipeline](https://github.com/arec1b0/MLOps/actions/workflows/ci.yml/badge.svg)](https://github.com/arec1b0/MLOps/actions/workflows/ci.yml)
[![Quality Gate](https://img.shields.io/badge/quality%20gate-passing-brightgreen)](#)
[![Security Scan](https://img.shields.io/badge/security-scanned-green)](#)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)](#)

A production-ready sentiment analysis microservice built with FastAPI, featuring comprehensive MLOps practices including automated CI/CD, monitoring, testing, and deployment automation. This project demonstrates enterprise-grade MLOps implementation suitable for production environments.

## 🏗️ Architecture Overview

This microservice implements a sentiment analysis solution using modern MLOps practices:

- **FastAPI** for high-performance API development with automatic documentation
- **DistilBERT** for efficient sentiment classification with transformer models
- **Docker** for containerization and deployment portability
- **Kubernetes** for orchestration and scaling
- **Prometheus & Grafana** for monitoring and observability
- **GitHub Actions** for automated CI/CD pipeline

## 🚀 Features

### Core Functionality
- **Real-time sentiment analysis** using pre-trained transformer models
- **Health monitoring** with comprehensive endpoint diagnostics
- **Performance metrics** and system monitoring capabilities
- **Automatic API documentation** with Swagger UI and ReDoc
- **Graceful error handling** with fallback mechanisms
- **Input validation** with Pydantic schemas

### MLOps Capabilities
- **Automated Testing** with 44+ comprehensive tests covering all modules
- **Code Quality Gates** with linting, formatting, and type checking
- **Security Scanning** with vulnerability and dependency checks
- **Container Security** with non-root users and security best practices
- **Infrastructure as Code** with Kubernetes manifests and Helm charts
- **Monitoring & Alerting** with Prometheus rules and Grafana dashboards
- **Deployment Automation** with multi-environment support

## 📋 Quick Start

### Prerequisites

- **Docker** and Docker Compose
- **Python 3.9+** (for local development)
- **Kubernetes** (for production deployment)

### 🐳 Docker Deployment (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd MLOps

# Deploy with monitoring stack
docker-compose up -d

# Or deploy standalone
./scripts/deploy.sh
```

### 🛠️ Local Development

```bash
# Set up development environment
./scripts/setup_dev.sh

# Activate virtual environment
source venv/bin/activate

# Start development server
python -m uvicorn app.main:app --reload
```

### ☸️ Kubernetes Deployment

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app=mlops-sentiment-service
```

## 📚 API Documentation

### Endpoints

| Endpoint | Method | Description | Response |
|----------|---------|-------------|----------|
| `/` | GET | Service information | Service details |
| `/health` | GET | Health check | Health status |
| `/metrics` | GET | Performance metrics | System metrics |
| `/predict` | POST | Sentiment analysis | Prediction results |
| `/docs` | GET | Swagger UI | Interactive docs |

### Example Usage

#### Health Check
```bash
curl -X GET http://localhost:8000/api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "model_status": "available", 
  "version": "1.0.0",
  "timestamp": 1726251097.5
}
```

#### Sentiment Prediction
```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this amazing service!"}'
```

**Response:**
```json
{
  "label": "POSITIVE",
  "score": 0.9998,
  "inference_time_ms": 45.2,
  "model_name": "distilbert-base-uncased-finetuned-sst-2-english",
  "text_length": 26
}
```

#### Performance Metrics
```bash
curl -X GET http://localhost:8000/api/v1/metrics
```

**Response:**
```json
{
  "torch_version": "2.0.0+cpu",
  "cuda_available": false,
  "cuda_memory_allocated_mb": 0.0,
  "cuda_memory_reserved_mb": 0.0,
  "cuda_device_count": 0
}
```

## 🔧 Development Workflow

### Code Quality

```bash
# Run all quality checks
./scripts/quality_check.sh

# Individual checks
black --check app tests          # Code formatting
flake8 app tests                # Linting
mypy app --ignore-missing-imports # Type checking
pytest tests/ --cov=app         # Testing with coverage
```

### Testing

```bash
# Run test suite
./scripts/run_tests.sh

# Run specific tests
pytest tests/test_api.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## 📊 Monitoring & Observability

### Metrics Collection
- **System Metrics**: CPU, memory, disk usage
- **Application Metrics**: Request/response times, error rates
- **Model Metrics**: Inference time, model status
- **Business Metrics**: Prediction distribution, throughput

### Health Checks
- **Liveness Probe**: Service availability
- **Readiness Probe**: Model readiness
- **Startup Probe**: Initialization status

### Logging
- **Structured JSON Logging** with correlation IDs
- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Security Event Logging** for audit trails

### Alerting Rules
- High error rates (>10% for 5 minutes)
- High latency (95th percentile >1s for 5 minutes)
- Service unavailability (>1 minute)
- Resource utilization (CPU >80%, Memory >90%)

## 🔒 Security

### API Security
- **Input Validation** with Pydantic schemas
- **CORS Configuration** with configurable origins
- **Rate Limiting** (configurable)
- **Error Handling** without information leakage

### Container Security
- **Non-root User** execution
- **Read-only Root Filesystem**
- **Minimal Base Images** (Python slim)
- **Security Scanning** with Bandit and Safety

### Infrastructure Security
- **Network Policies** for Kubernetes
- **Secret Management** with ConfigMaps and Secrets
- **RBAC** for service accounts
- **TLS Encryption** for all communications

## ⚙️ Configuration

All configuration is managed through environment variables with the `MLOPS_` prefix:

```bash
# Application Settings
MLOPS_DEBUG=false
MLOPS_LOG_LEVEL=INFO
MLOPS_HOST=0.0.0.0
MLOPS_PORT=8000

# Model Settings  
MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
MLOPS_MODEL_CACHE_DIR=./models
MLOPS_MAX_TEXT_LENGTH=512

# Performance Settings
MLOPS_WORKERS=1
MLOPS_MAX_REQUEST_TIMEOUT=30
MLOPS_ENABLE_METRICS=true

# Security Settings
MLOPS_CORS_ORIGINS=*
MLOPS_API_KEY=your-api-key
```

## 🚀 Deployment

### Environment-Specific Deployments

#### Development
```bash
# Local development with hot reload
MLOPS_DEBUG=true python -m uvicorn app.main:app --reload
```

#### Staging
```bash
# Staging deployment with monitoring
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

#### Production
```bash
# Production Kubernetes deployment
kubectl apply -f k8s/
```

### Scaling
- **Horizontal Pod Autoscaler** based on CPU/memory metrics
- **Pod Disruption Budgets** for availability
- **Resource Limits** and requests properly configured

## 📈 Performance

### Benchmarks
- **Response Time**: <100ms (95th percentile)
- **Throughput**: 1000+ requests/second
- **Memory Usage**: <2GB per instance
- **Model Loading**: <60 seconds cold start

### Optimization
- **Model Caching** for fast inference
- **Connection Pooling** for database connections
- **Async/Await** for non-blocking operations
- **CPU-optimized** PyTorch builds

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for detailed information about:

- Development setup and workflow
- Code quality standards and testing
- Security guidelines and best practices
- Documentation requirements
- Review process and release management

### Quick Contribution Setup

```bash
# Fork and clone the repository
git clone <your-fork-url>
cd MLOps

# Set up development environment
./scripts/setup_dev.sh

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test
./scripts/quality_check.sh

# Submit pull request
```

## 📋 Project Structure

```
├── .github/
│   └── workflows/          # CI/CD pipeline definitions
├── app/                    # Main application code
│   ├── ml/                # Machine learning modules
│   ├── main.py            # FastAPI app factory
│   ├── api.py             # API endpoints
│   └── config.py          # Configuration management
├── tests/                 # Comprehensive test suite
├── k8s/                   # Kubernetes manifests
├── monitoring/            # Prometheus & Grafana config
├── scripts/               # Utility scripts
├── docker-compose.yml     # Local development stack
├── Dockerfile             # Container definition
├── pyproject.toml         # Project configuration
└── requirements.txt       # Python dependencies
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Acknowledgments

- **Hugging Face** for the DistilBERT model
- **FastAPI** for the excellent web framework
- **PyTorch** for the ML infrastructure
- **Open Source Community** for the amazing tools

---

**Built with ❤️ for Production MLOps**

*This project demonstrates enterprise-grade MLOps practices suitable for production environments.*
