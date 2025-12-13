# Scripts Directory

This directory contains utility scripts for development, testing, and operations, organized by function.

## Directory Structure

### `scripts/ci/` - Continuous Integration & Quality
Scripts used by CI/CD pipelines and local quality checks.
- `check_code_quality.py`: Runs formatters and linters (Black, Ruff, Isort).
- `quality_gate.py`: Enforces quality standards (coverage, complexity, etc.).
- `format_code.sh` / `format_code.ps1`: Applies code formatting.

### `scripts/infra/` - Infrastructure & Deployment
Scripts for setting up environments and deploying the application.
- `setup-kind.sh`: Sets up a local Kubernetes cluster using Kind.
- `setup-minikube.sh`: Sets up a local Kubernetes cluster using Minikube.
- `deploy-helm.sh`: Helper to deploy the application via Helm.
- `setup-monitoring.sh`: Deploys the observability stack (Prometheus/Grafana).
- `build-optimized-image.sh`: Builds production Docker images.
- `healthcheck.py`: Used by Docker/K8s for service health verification.

### `scripts/setup/` - Environment Setup
Scripts for initializing the local development environment.
- `setup_dev_environment.py`: Bootstraps the dev environment (venv, dependencies, pre-commit).
- `cleanup.sh`: Removes temporary build artifacts.

### `scripts/ops/` - Operations & Maintenance
Scripts for operational tasks.
- `convert_to_onnx.py`: Converts PyTorch models to ONNX format.
- `migrate-secrets-to-vault.py`: Helper for secret migration.
- `rotate-secrets.py`: Utility for rotating secrets.

### `scripts/tests/` - Testing & Benchmarks
Scripts for running tests and benchmarks.
- `benchmark_vectorization.py`: Benchmarks model performance.
- `test-cold-start.sh`: Measures application startup time.
- `test_profiles.py`: Tests profile loading.
- `validate_profiles.py`: Validates configuration profiles.
