# Scripts Directory

This directory contains utility scripts for development, testing, and operations, organized by function.

## Directory Structure

### `scripts/ci/` - Continuous Integration & Quality
Scripts used by CI/CD pipelines and local quality checks.
- `check_code_quality.py`: Runs formatters and linters (Black, Ruff, Isort).
  ```bash
  python scripts/ci/check_code_quality.py
  ```
- `quality_gate.py`: Enforces quality standards (coverage, complexity, etc.).
  ```bash
  python scripts/ci/quality_gate.py
  ```
- `format_code.sh` / `format_code.ps1`: Applies code formatting.

### `scripts/infra/` - Infrastructure & Deployment
Scripts for setting up environments and deploying the application.
- `setup-kind.sh`: Sets up a local Kubernetes cluster using Kind.
  ```bash
  ./scripts/infra/setup-kind.sh
  ```
- `setup-minikube.sh`: Sets up a local Kubernetes cluster using Minikube.
- `deploy-helm.sh`: Helper to deploy the application via Helm.
- `setup-monitoring.sh`: Deploys the observability stack (Prometheus/Grafana).
- `build-optimized-image.sh`: Builds production Docker images.
- `healthcheck.py`: Used by Docker/K8s for service health verification.

### `scripts/setup/` - Environment Setup
Scripts for initializing the local development environment.
- `setup_dev_environment.py`: Bootstraps the dev environment (venv, dependencies, pre-commit).
  ```bash
  python scripts/setup/setup_dev_environment.py
  ```
- `cleanup.sh`: Removes temporary build artifacts.

### `scripts/ops/` - Operations & Maintenance
Scripts for operational tasks.
- `convert_to_onnx.py`: Converts PyTorch models to ONNX format.
  ```bash
  python scripts/ops/convert_to_onnx.py --model-name ...
  ```
- `migrate-secrets-to-vault.py`: Helper for secret migration.
- `rotate-secrets.py`: Utility for rotating secrets.

### `scripts/tests/` - Testing & Benchmarks
Scripts for running tests and benchmarks.
- `benchmark_vectorization.py`: Benchmarks model performance.
- `test-cold-start.sh`: Measures application startup time.
- `test_profiles.py`: Tests profile loading.
- `validate_profiles.py`: Validates configuration profiles.

## Usage Notes

### Exit Codes
- **0**: Success.
- **1**: Failure (e.g., linting errors, quality gate breach, setup failure).

### Module Structure
This directory is structured as a Python package to support shared utilities.
However, most scripts are designed to be run as standalone executables from the project root.

Example:
```bash
# Correct execution from project root
python scripts/ci/check_code_quality.py
```


