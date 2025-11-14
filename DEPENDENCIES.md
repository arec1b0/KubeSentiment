# Dependency Management

This document explains the dependency structure of KubeSentiment and the rationale behind the organization.

## Overview

Dependencies are organized into modular groups to improve:
- **Installation flexibility**: Install only what you need
- **Build times**: Faster Docker builds with smaller base images
- **Clarity**: Clear separation of concerns
- **Maintenance**: Easier to audit and update dependencies

## Dependency Groups

### Core (`requirements.txt`)

Essential dependencies required for the application to run. These include:

- **Web Framework**: FastAPI, Uvicorn
- **Data Validation**: Pydantic, Pydantic Settings
- **ML Inference**: PyTorch, Transformers, ONNX Runtime
- **Monitoring**: Prometheus Client, Structlog
- **Caching & Streaming**: Redis, Kafka
- **Secrets Management**: HVAC (HashiCorp Vault)
- **Kubernetes Integration**: kubernetes-client
- **Feature Engineering**: NLTK, TextStat
- **Optional MLOps Features**: OpenTelemetry, MLflow, SHAP, Captum, Evidently

**Install with:**
```bash
pip install -r requirements.txt
```

### Cloud-Specific Dependencies

#### AWS (`requirements-aws.txt`)
- boto3: AWS SDK for S3, Lambda, etc.
- s3fs: S3 filesystem interface
- mangum: ASGI adapter for AWS Lambda

**Install with:**
```bash
pip install -r requirements.txt -r requirements-aws.txt
```

#### GCP (`requirements-gcp.txt`)
- google-cloud-storage: GCS SDK
- gcsfs: GCS filesystem interface

**Install with:**
```bash
pip install -r requirements.txt -r requirements-gcp.txt
```

#### Azure (`requirements-azure.txt`)
- azure-storage-blob: Azure Blob Storage SDK
- adlfs: Azure Data Lake filesystem interface

**Install with:**
```bash
pip install -r requirements.txt -r requirements-azure.txt
```

### Development (`requirements-dev.txt`)

Tools for code quality, formatting, and development workflow:

- **Formatting**: Black, isort
- **Linting**: Ruff, Flake8 (with plugins)
- **Type Checking**: mypy
- **Security**: Bandit
- **Pre-commit Hooks**: pre-commit
- **Documentation**: interrogate

**Install with:**
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### Testing (`requirements-test.txt`)

Dependencies for running tests:

- pytest
- pytest-asyncio
- pytest-cov
- httpx (for async HTTP testing)

**Install with:**
```bash
pip install -r requirements.txt -r requirements-test.txt
```

### ONNX Optimized (`requirements-onnx.txt`)

Minimal dependencies for ONNX-optimized deployments (existing file, unchanged):

- Lighter PyTorch build
- ONNX Runtime optimizations
- Optimum library

**Install with:**
```bash
pip install -r requirements-onnx.txt
```

## Makefile Shortcuts

The Makefile provides convenient shortcuts for common installation patterns:

```bash
make install          # Core dependencies only
make install-dev      # Core + test + dev dependencies
make install-test     # Core + test dependencies
make install-aws      # Core + AWS dependencies
make install-gcp      # Core + GCP dependencies
make install-azure    # Core + Azure dependencies
```

## Removed Dependencies

The following dependencies were removed during the cleanup as they were not used in the codebase:

| Dependency | Reason for Removal |
|------------|-------------------|
| `great-expectations` | Not imported anywhere in codebase |
| `pandera` | Not imported anywhere in codebase |
| `vaderSentiment` | NLTK's built-in VADER is used instead |
| `hydra-core` | Not imported anywhere in codebase |
| `dynaconf` | Not imported anywhere in codebase |
| `onnx` | Only `onnxruntime` is used; `onnx` package not needed |
| `mlflow-skinny` | Redundant with main `mlflow` package |
| `asyncio-throttle` | Not imported anywhere in codebase |
| `scikit-learn` | Not directly imported (scipy provides needed functionality) |

## Dependency Analysis

A comprehensive codebase analysis was performed to identify all third-party imports. Key findings:

### Most Critical Dependencies (High Usage)
1. **fastapi** - Web framework (app, tests, serverless, chaos)
2. **pydantic** - Data validation (used throughout)
3. **torch** - ML inference (app, serverless)
4. **transformers** - NLP models (app, serverless)
5. **prometheus_client** - Metrics (app, benchmarking)
6. **redis** - Caching (app)
7. **kafka** - Message streaming (app, benchmarking)

### Conditionally Used Dependencies
These are imported only when specific features are enabled:
- **mlflow** - MLOps tracking (optional feature)
- **evidently** - Drift detection (optional feature)
- **shap, captum** - Model explainability (optional feature)
- **opentelemetry** - Distributed tracing (optional feature)

### Development/Testing Only
- **pytest** - Testing framework
- **black, ruff, flake8** - Code quality tools
- **mypy** - Type checking

## CI/CD Integration

The GitHub Actions CI/CD pipeline has been updated to use the new dependency structure:

```yaml
- name: Install dependencies
  run: |
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    pip install -r requirements-test.txt
    pip install -r requirements-dev.txt
```

This ensures:
- Core dependencies are installed first
- Test dependencies are available for running tests
- Development tools are available for linting and formatting checks

## Docker Images

### Standard Dockerfile
Uses only `requirements.txt` for minimal runtime dependencies.

### Optimized Dockerfile
Uses both `requirements.txt` and `requirements-onnx.txt` for ONNX-optimized inference.

Cloud-specific dependencies (AWS, GCP, Azure) are **not** included in Docker images by default, as they are typically only needed when running with specific cloud providers. These can be added to custom builds if needed.

## Maintenance Guidelines

### Adding New Dependencies

1. Determine the appropriate group:
   - Runtime required? → `requirements.txt`
   - Cloud-specific? → `requirements-{aws,gcp,azure}.txt`
   - Development tool? → `requirements-dev.txt`
   - Testing only? → `requirements-test.txt`

2. Add with a version pin or minimum version:
   ```
   package==1.2.3      # Exact version (preferred for reproducibility)
   package>=1.2.0      # Minimum version (for flexibility)
   ```

3. Add a comment explaining why the dependency is needed

4. Update this documentation if adding a new category

### Upgrading Dependencies

1. Check for breaking changes in changelogs
2. Update version in appropriate requirements file
3. Run full test suite to verify compatibility
4. Update Docker images if needed

### Removing Dependencies

1. Verify the dependency is truly unused (use `grep -r "import package_name"`)
2. Check for indirect usage (imported by other dependencies)
3. Remove from requirements file
4. Document removal in this file
5. Test that application still functions correctly

## Security Considerations

- All dependencies should be regularly audited for security vulnerabilities
- Use `pip-audit` or similar tools to check for known CVEs
- Consider using Dependabot or Renovate for automated dependency updates
- Pin exact versions in production for reproducibility
- Review security advisories before upgrading

## Performance Implications

Different dependency groups have different impacts on:

- **Installation time**: More dependencies = longer install
- **Image size**: Core dependencies kept minimal for smaller images
- **Import time**: Heavy ML libraries (torch, transformers) increase startup time
- **Memory footprint**: ML models and libraries require significant RAM

The modular approach allows you to optimize for your specific deployment scenario.

---

**Last Updated:** 2025-11-14
**Maintained By:** KubeSentiment Team
