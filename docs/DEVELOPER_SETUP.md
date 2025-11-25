# ⚠️ DEPRECATED - KubeSentiment Developer Setup Guide

> **This document has been partially superseded.** For configuration setup, see **[docs/configuration/QUICK_START.md](docs/configuration/QUICK_START.md)**.
>
> For complete developer setup (IDE, pre-commit hooks, etc.), see **[docs/setup/DEVELOPMENT.md](docs/setup/DEVELOPMENT.md)**.

> **Last Updated:** 2025-11-19
> **Target Audience:** Contributors and developers
> **Time to Complete:** 15-30 minutes

## Overview

This guide walks you through setting up KubeSentiment for local development. After completing this guide, you'll have a fully functional development environment with all tools, dependencies, and pre-commit hooks installed.

## Prerequisites

Before starting, ensure you have:

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/))
- **Docker** (optional, for running infrastructure services)
  - [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
- **4GB+ RAM** (8GB+ recommended)
- **2GB+ Disk Space**

### Check Your System

```bash
# Check Python version
python3 --version
# Expected: Python 3.11.x or higher

# Check Git version
git --version
# Expected: git version 2.x.x or higher

# Check Docker (optional)
docker --version
# Expected: Docker version 20.10+ (optional)
```

## Quick Start (Automated)

The fastest way to set up your development environment:

### 1. Clone the Repository

```bash
git clone https://github.com/arec1b0/KubeSentiment.git
cd KubeSentiment
```

### 2. Run the Setup Script

```bash
# Basic setup (recommended for most developers)
python scripts/setup_dev_environment.py

# Or with specific options
python scripts/setup_dev_environment.py --full
python scripts/setup_dev_environment.py --with-observability
python scripts/setup_dev_environment.py --skip-hooks  # If pre-commit fails
```

### 3. Activate Virtual Environment

```bash
# On macOS/Linux
source .venv/bin/activate

# On Windows
.venv\Scripts\activate

# Verify activation (your prompt should show (.venv))
```

### 4. Start Development Server

```bash
# Option 1: Using Make (recommended)
make dev

# Option 2: Using uvicorn directly
PROFILE=local uvicorn app.main:app --reload
```

### 5. Verify Setup

Visit these URLs:
- **Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Manual Setup (Step-by-Step)

If the automated script doesn't work or you prefer manual setup:

### 1. Create Virtual Environment

```bash
# Create venv
python3.11 -m venv .venv

# Activate venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Install base requirements
pip install -r requirements.txt

# Install development tools
pip install -r requirements-dev.txt

# Install testing tools
pip install -r requirements-test.txt
```

### 3. Install Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# (Optional) Run hooks on all files
pre-commit run --all-files
```

### 4. Verify Installation

```bash
# Check Python packages
python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
python -c "import pydantic; print(f'Pydantic {pydantic.__version__}')"

# Check development tools
black --version
ruff --version
mypy --version
pytest --version
```

---

## Development Workflows

### Running the Application

#### Local Mode (No Dependencies)

```bash
# Uses mock models, no Redis/Kafka
PROFILE=local uvicorn app.main:app --reload

# Visit http://localhost:8000/docs
```

#### Development Mode (With Redis/Kafka)

```bash
# Requires Docker Compose
docker-compose up -d

# Then start the app
PROFILE=development uvicorn app.main:app --reload
```

#### Using Make

```bash
# Show all available commands
make help

# Start development server
make dev

# Run only the app
make run
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/unit/test_api.py

# Run specific test
pytest tests/unit/test_api.py::test_predict_success

# Run with coverage
pytest --cov=app --cov-report=html

# Run only fast tests (skip slow/integration)
pytest -m "not slow"
```

### Code Quality Checks

```bash
# Format code (Black + isort)
make format

# Run all linters
make lint

# Run specific linter
black app/
ruff check app/
mypy app/

# Check complexity
radon cc app/ -a

# Security scan
bandit -r app/
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "feat(api): add new endpoint"

# Pre-commit hooks run automatically
# If they fail, fix issues and try again

# Push to remote
git push -u origin feature/my-feature

# Create pull request on GitHub
```

---

## Docker-Based Development

### Using Docker Compose

For development with all services (Redis, Kafka, etc.):

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Remove volumes (careful - deletes data)
docker-compose down -v
```

### Available Services

- **app** (http://localhost:8000) - FastAPI application
- **redis** (localhost:6379) - Prediction caching
- **kafka** (localhost:9092) - Message broker
- **postgres** (localhost:5432) - Data storage
- **prometheus** (http://localhost:9090) - Metrics
- **grafana** (http://localhost:3000) - Dashboards

### Docker Compose Examples

```bash
# Start only app and redis
docker-compose up -d app redis

# Start with observability stack
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# Build images
docker-compose build

# Rebuild and start
docker-compose up --build -d
```

---

## Environment Configuration

### Profile-Based Configuration

KubeSentiment uses profile-based configuration (see ADR-009):

```bash
# Local development (no external services)
PROFILE=local MLOPS_DEBUG=true uvicorn app.main:app --reload

# Development (with services)
PROFILE=development uvicorn app.main:app --reload

# Staging
PROFILE=staging uvicorn app.main:app --reload

# Production
PROFILE=production uvicorn app.main:app --workers 4
```

### Common Environment Variables

```bash
# Debugging
MLOPS_DEBUG=true
MLOPS_LOG_LEVEL=DEBUG

# Server
MLOPS_SERVER_HOST=0.0.0.0
MLOPS_SERVER_PORT=8000

# Model
MLOPS_MODEL_BACKEND=onnx  # or pytorch
MLOPS_MODEL_CACHE_DIR=./models

# Redis (caching)
MLOPS_REDIS_ENABLED=true
MLOPS_REDIS_HOST=localhost
MLOPS_REDIS_PORT=6379

# Kafka (async processing)
MLOPS_KAFKA_ENABLED=true
MLOPS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Observability
MLOPS_OBSERVABILITY_ENABLED=true
MLOPS_PROMETHEUS_ENABLED=true
```

### .env File

Create a `.env` file in project root:

```bash
# Copy template
cp .env.local.template .env

# Edit values
nano .env

# Source in shell (optional - uvicorn reads from environment)
source .env
```

---

## IDE Configuration

### VS Code

1. **Install Python extension**
   - Search "Python" in Extensions
   - Install official Microsoft Python extension

2. **Configure Python interpreter**
   - Press Ctrl+Shift+P (Cmd+Shift+P on Mac)
   - Type "Python: Select Interpreter"
   - Choose `./.venv/bin/python`

3. **Configure linting**
   - Settings > Python > Linting
   - Enable Ruff, mypy
   - Disable Pylint (conflicts with Ruff)

4. **Configure formatting**
   - Settings > Python > Formatting
   - Provider: Black
   - Args: `["--line-length=100"]`

5. **Create launch configuration** (`.vscode/launch.json`)

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "jinja": true,
      "justMyCode": true,
      "env": {
        "PROFILE": "local",
        "MLOPS_DEBUG": "true"
      }
    }
  ]
}
```

### PyCharm

1. **Configure Python interpreter**
   - Settings > Project > Python Interpreter
   - Add Interpreter > Add Local Interpreter
   - Select `./.venv/bin/python`

2. **Configure code style**
   - Settings > Editor > Code Style > Python
   - Set line length: 100
   - Enable Black formatter

3. **Configure linters**
   - Settings > Tools > Python Integrated Tools
   - Default test runner: pytest
   - Package requirements file: requirements-test.txt

4. **Run configuration**
   - Run > Edit Configurations
   - Add Python configuration
   - Module: uvicorn
   - Parameters: `app.main:app --reload`
   - Environment: `PROFILE=local`

---

## Troubleshooting

### Python Not Found

```bash
# Check python paths
which python3.11
which python3

# If not found, install Python 3.11
# macOS: brew install python@3.11
# Linux: apt-get install python3.11
# Windows: Download from python.org
```

### Virtual Environment Issues

```bash
# Recreate venv
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate

# Reinstall packages
pip install -r requirements.txt requirements-dev.txt
```

### Pre-commit Hook Failures

```bash
# See what hooks are checking
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
pre-commit run ruff --all-files

# Temporarily disable hooks
git commit --no-verify  # Not recommended

# Uninstall hooks (then reinstall with: pre-commit install)
pre-commit uninstall
```

### Docker Compose Issues

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f [service]

# Reset services
docker-compose down -v
docker-compose up -d

# Check ports in use
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

### Import Errors

```bash
# Reinstall in development mode
pip install -e .

# Check Python path
python -c "import sys; print(sys.path)"

# Verify package installed
python -c "import app; print(app.__file__)"
```

---

## Next Steps

### 1. Read Key Documentation

- **[CLAUDE.md](../CLAUDE.md)** - AI assistant guide with patterns and conventions
- **[README.md](../README.md)** - Project overview
- **[docs/architecture/decisions/](./architecture/decisions/)** - Architecture decisions (ADRs)

### 2. Explore the Codebase

```bash
# Key directories
app/
  ├── api/         # API endpoints
  ├── core/        # Configuration & logging
  ├── models/      # ML model implementations
  ├── services/    # Business logic
  └── monitoring/  # Observability

tests/
  ├── unit/        # Fast, isolated tests
  ├── integration/ # Component integration
  └── performance/ # Performance benchmarks
```

### 3. Make Your First Contribution

```bash
# Create feature branch
git checkout -b feature/my-first-contribution

# Make a small change
# Run tests
make test

# Run linters
make lint

# Commit with conventional commit message
git commit -m "feat(api): add documentation example"

# Push and create PR
```

### 4. Learn the Code Patterns

Review these files to understand project patterns:

- **API Patterns**: `app/api/routes/predictions.py`
- **Model Factory**: `app/models/factory.py`
- **Configuration**: `app/core/config/settings.py`
- **Logging**: `app/core/logging.py`
- **Testing**: `tests/unit/test_api.py`

---

## Common Commands Reference

### Development

```bash
make help              # Show all available commands
make dev              # Start development server
make run              # Run application (no reload)
make shell            # Python interactive shell
```

### Testing

```bash
make test             # Run all tests
make test-unit        # Unit tests only
make test-integration # Integration tests only
make coverage         # Generate coverage report
```

### Code Quality

```bash
make format           # Format code (Black + isort)
make lint             # Run all linters
make complexity       # Check code complexity
make security         # Security scan (Bandit)
```

### Build & Deploy

```bash
make build            # Build Docker image
make deploy-dev       # Deploy to development
make deploy-staging   # Deploy to staging
```

---

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **Documentation**: Check `docs/` directory
- **Code Comments**: Review inline code documentation
- **ADRs**: Review Architecture Decision Records for design context
- **CLAUDE.md**: AI assistant guide with patterns

---

## Additional Resources

### Development Setup
- [Profile-Based Configuration](./CONFIGURATION_PROFILES.md)
- [Code Quality Standards](./CODE_QUALITY_IMPLEMENTATION.md)
- [Testing Strategy](./TESTING.md)

### Architecture & Design
- [Architecture Overview](./architecture.md)
- [ADR Index](./architecture/decisions/README.md)
- [Service Interfaces](./SERVICE_INTERFACES.md)

### APIs & Integration
- [API Reference](./API_REFERENCE.md)
- [API Versioning](./API_VERSIONING.md)
- [Error Handling](./ERROR_HANDLING.md)

### Deployment
- [Kubernetes Guide](./KUBERNETES.md)
- [Docker Setup](./DOCKER_SETUP.md)
- [GPU Deployment](./GPU_DEPLOYMENT_GUIDE.md)

---

**Happy coding! 🚀**

If you encounter any issues, please open a GitHub issue with:
- Your OS and Python version
- Steps to reproduce
- Error messages
- Relevant logs

---

**Last Updated:** 2025-11-19
**Maintainer:** AI Engineering Team
