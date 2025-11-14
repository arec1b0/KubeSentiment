# Configuration Profiles Guide

## Overview

KubeSentiment uses a **profile-based configuration system** that provides environment-specific defaults, significantly reducing the number of environment variables you need to configure manually. Instead of setting dozens of environment variables, you simply specify a profile (local, development, staging, or production), and the system automatically applies appropriate defaults.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Available Profiles](#available-profiles)
3. [Using Profiles](#using-profiles)
4. [Profile Defaults](#profile-defaults)
5. [Overriding Profile Defaults](#overriding-profile-defaults)
6. [Deployment Examples](#deployment-examples)
7. [Migration Guide](#migration-guide)
8. [Custom Profiles](#custom-profiles)

---

## Quick Start

### Local Development

```bash
# Copy the template
cp .env.local.template .env

# Set profile
export MLOPS_PROFILE=local

# Run the application
python -m uvicorn app.main:app --reload
```

### Docker

```bash
# Build with profile
docker build --build-arg MLOPS_PROFILE=production -t kubesentiment:latest .

# Run with profile
docker run -e MLOPS_PROFILE=staging -p 8000:8000 kubesentiment:latest
```

### Kubernetes

```bash
# Deploy development environment
kubectl apply -f k8s/config-dev.yaml

# Deploy staging environment
kubectl apply -f k8s/config-staging.yaml

# Deploy production environment
kubectl apply -f k8s/config-production.yaml
```

---

## Available Profiles

### 1. Local Profile

**Use Case:** Minimal local development without external dependencies

**Key Features:**
- No external services required (Redis, Kafka, Vault disabled)
- Runs on localhost only
- Minimal logging for clean output
- Fast startup

**Ideal For:**
- Quick local testing
- Development without Docker Compose
- CI/CD unit tests

### 2. Development Profile

**Use Case:** Full-featured development with optional services

**Key Features:**
- Debug mode enabled
- Verbose logging (DEBUG level)
- External services disabled by default (can be enabled)
- Small cache sizes
- Permissive CORS

**Ideal For:**
- Feature development
- Integration testing
- Debugging issues

### 3. Staging Profile

**Use Case:** Pre-production testing environment

**Key Features:**
- Production-like configuration
- Redis and Vault enabled
- MLOps features enabled (MLflow, drift detection)
- Distributed tracing enabled
- Moderate resource allocation

**Ideal For:**
- Pre-production validation
- Performance testing
- User acceptance testing (UAT)
- Integration testing

### 4. Production Profile

**Use Case:** Live production deployment

**Key Features:**
- All services enabled (Redis, Kafka, Vault, Data Lake)
- All MLOps features enabled
- Optimized performance settings
- Strict security
- Minimal logging (WARNING level)
- Large cache sizes

**Ideal For:**
- Production deployments
- Maximum reliability
- Optimal performance

---

## Using Profiles

### Method 1: Environment Variable

The simplest way to use a profile is to set the `MLOPS_PROFILE` environment variable:

```bash
export MLOPS_PROFILE=development
python -m uvicorn app.main:app
```

### Method 2: .env File

Create a `.env` file from a template:

```bash
# For local development
cp .env.local.template .env

# For development with services
cp .env.development.template .env

# For staging
cp .env.staging.template .env

# For production
cp .env.production.template .env
```

Then edit the `.env` file to customize settings as needed.

### Method 3: Docker Build Argument

Bake the profile into your Docker image:

```bash
docker build \
  --build-arg MLOPS_PROFILE=production \
  --build-arg VERSION=1.0.0 \
  -t kubesentiment:1.0.0 .
```

### Method 4: Kubernetes ConfigMap

The profile is set in the ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubesentiment-config
data:
  MLOPS_PROFILE: "production"
```

---

## Profile Defaults

### Local Profile Defaults

```python
MLOPS_DEBUG: "true"
MLOPS_WORKERS: "1"
MLOPS_ENVIRONMENT: "local"
MLOPS_HOST: "127.0.0.1"
MLOPS_LOG_LEVEL: "INFO"

# All external services disabled
MLOPS_REDIS_ENABLED: "false"
MLOPS_KAFKA_ENABLED: "false"
MLOPS_VAULT_ENABLED: "false"
MLOPS_DATA_LAKE_ENABLED: "false"
MLOPS_MLFLOW_ENABLED: "false"

# Minimal caching
MLOPS_PREDICTION_CACHE_MAX_SIZE: "100"
```

### Development Profile Defaults

```python
MLOPS_DEBUG: "true"
MLOPS_WORKERS: "1"
MLOPS_ENVIRONMENT: "development"
MLOPS_LOG_LEVEL: "DEBUG"
MLOPS_ENABLE_METRICS: "true"
MLOPS_ENABLE_TRACING: "false"

# External services disabled by default
MLOPS_REDIS_ENABLED: "false"
MLOPS_KAFKA_ENABLED: "false"
MLOPS_VAULT_ENABLED: "false"
MLOPS_DATA_LAKE_ENABLED: "false"

# MLOps features disabled for faster startup
MLOPS_MLFLOW_ENABLED: "false"
MLOPS_DRIFT_DETECTION_ENABLED: "false"
MLOPS_EXPLAINABILITY_ENABLED: "false"

# Relaxed security
MLOPS_API_KEY: ""
MLOPS_ALLOWED_ORIGINS: "*"
MLOPS_CORS_ORIGINS: "*"

# Small cache
MLOPS_PREDICTION_CACHE_MAX_SIZE: "100"
MLOPS_MAX_TEXT_LENGTH: "512"
```

### Staging Profile Defaults

```python
MLOPS_DEBUG: "false"
MLOPS_WORKERS: "2"
MLOPS_ENVIRONMENT: "staging"
MLOPS_LOG_LEVEL: "INFO"
MLOPS_ENABLE_METRICS: "true"
MLOPS_ENABLE_TRACING: "true"
MLOPS_TRACING_BACKEND: "jaeger"

# External services enabled
MLOPS_REDIS_ENABLED: "true"
MLOPS_KAFKA_ENABLED: "false"  # Optional in staging
MLOPS_VAULT_ENABLED: "true"
MLOPS_DATA_LAKE_ENABLED: "false"

# MLOps features enabled
MLOPS_MLFLOW_ENABLED: "true"
MLOPS_DRIFT_DETECTION_ENABLED: "true"
MLOPS_EXPLAINABILITY_ENABLED: "true"

# Performance features
MLOPS_ASYNC_BATCH_ENABLED: "true"
MLOPS_ASYNC_BATCH_SIZE: "50"
MLOPS_ASYNC_BATCH_TIMEOUT: "5.0"

# Moderate caching
MLOPS_PREDICTION_CACHE_MAX_SIZE: "1000"
MLOPS_REDIS_PREDICTION_CACHE_TTL: "3600"
```

### Production Profile Defaults

```python
MLOPS_DEBUG: "false"
MLOPS_WORKERS: "4"
MLOPS_ENVIRONMENT: "production"
MLOPS_LOG_LEVEL: "WARNING"
MLOPS_ENABLE_METRICS: "true"
MLOPS_ENABLE_TRACING: "true"
MLOPS_TRACING_BACKEND: "otlp"

# All external services enabled
MLOPS_REDIS_ENABLED: "true"
MLOPS_KAFKA_ENABLED: "true"
MLOPS_VAULT_ENABLED: "true"
MLOPS_DATA_LAKE_ENABLED: "true"

# All MLOps features enabled
MLOPS_MLFLOW_ENABLED: "true"
MLOPS_DRIFT_DETECTION_ENABLED: "true"
MLOPS_EXPLAINABILITY_ENABLED: "true"

# Production-optimized performance
MLOPS_ASYNC_BATCH_ENABLED: "true"
MLOPS_ASYNC_BATCH_SIZE: "100"
MLOPS_ASYNC_BATCH_TIMEOUT: "2.0"
MLOPS_ASYNC_MAX_WORKERS: "10"

# Large caching
MLOPS_PREDICTION_CACHE_MAX_SIZE: "10000"
MLOPS_REDIS_MAX_CONNECTIONS: "100"
MLOPS_REDIS_PREDICTION_CACHE_TTL: "7200"

# Kafka configuration
MLOPS_KAFKA_CONSUMER_THREADS: "8"
MLOPS_KAFKA_BATCH_SIZE: "200"
MLOPS_KAFKA_MAX_POLL_RECORDS: "1000"
```

For complete defaults, see `app/core/config/profiles.py`.

---

## Overriding Profile Defaults

Profile defaults are applied **only if the environment variable is not already set**. This allows you to:

1. Use profile defaults for most settings
2. Override specific settings as needed

### Example: Development with Redis Enabled

```bash
# .env file
MLOPS_PROFILE=development

# Override the default (Redis disabled in dev profile)
MLOPS_REDIS_ENABLED=true
MLOPS_REDIS_HOST=localhost
MLOPS_REDIS_PORT=6379
```

### Example: Production with Custom Cache Size

```bash
# .env file
MLOPS_PROFILE=production

# Override the default cache size (10000 in prod profile)
MLOPS_PREDICTION_CACHE_MAX_SIZE=50000
```

### Priority Order

Configuration values are loaded in this order (highest priority first):

1. **Explicitly set environment variables** (highest priority)
2. **`.env` file values**
3. **Profile defaults**
4. **Pydantic field defaults** (lowest priority)

---

## Deployment Examples

### Local Development (Minimal)

```bash
# .env
MLOPS_PROFILE=local

# That's it! Everything else has sensible defaults
```

### Development with External Services

```bash
# .env
MLOPS_PROFILE=development

# Enable services as needed
MLOPS_REDIS_ENABLED=true
MLOPS_REDIS_HOST=localhost

MLOPS_KAFKA_ENABLED=true
MLOPS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Docker Compose (Development)

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      args:
        MLOPS_PROFILE: development
    environment:
      - MLOPS_PROFILE=development
      - MLOPS_REDIS_ENABLED=true
      - MLOPS_REDIS_HOST=redis
    ports:
      - "8000:8000"
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Kubernetes (Staging)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubesentiment-staging
data:
  # Profile handles most configuration
  MLOPS_PROFILE: "staging"

  # Override service endpoints
  MLOPS_REDIS_HOST: "redis-staging"
  MLOPS_VAULT_ADDR: "https://vault-staging.example.com"
  MLOPS_MLFLOW_TRACKING_URI: "https://mlflow-staging.example.com"
```

### Kubernetes (Production)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubesentiment-prod
data:
  # Profile provides production defaults
  MLOPS_PROFILE: "production"

  # Only specify environment-specific values
  MLOPS_REDIS_HOST: "redis-prod.production.svc.cluster.local"
  MLOPS_KAFKA_BOOTSTRAP_SERVERS: "kafka-prod.production.svc.cluster.local:9092"
  MLOPS_VAULT_ADDR: "https://vault.production.example.com"
```

---

## Migration Guide

### From Environment Variables to Profiles

**Before (Old Approach):**

```bash
# Had to set ~50 environment variables
export MLOPS_DEBUG=false
export MLOPS_LOG_LEVEL=WARNING
export MLOPS_WORKERS=4
export MLOPS_ENVIRONMENT=production
export MLOPS_REDIS_ENABLED=true
export MLOPS_REDIS_MAX_CONNECTIONS=100
export MLOPS_REDIS_PREDICTION_CACHE_TTL=7200
export MLOPS_KAFKA_ENABLED=true
export MLOPS_KAFKA_CONSUMER_THREADS=8
export MLOPS_KAFKA_BATCH_SIZE=200
# ... 40+ more variables
```

**After (Profile Approach):**

```bash
# Just set the profile
export MLOPS_PROFILE=production

# Only override environment-specific values
export MLOPS_REDIS_HOST=my-redis-server
export MLOPS_KAFKA_BOOTSTRAP_SERVERS=my-kafka-server:9092
```

### Migration Steps

1. **Identify your environment** (local, development, staging, production)
2. **Set `MLOPS_PROFILE`** to the appropriate value
3. **Review profile defaults** in `app/core/config/profiles.py`
4. **Keep only environment-specific overrides** (endpoints, credentials)
5. **Remove redundant environment variables** that match profile defaults
6. **Test thoroughly** to ensure behavior is unchanged

### Backward Compatibility

The profile system is **fully backward compatible**:

- If `MLOPS_PROFILE` is not set, the system works as before
- All existing environment variables continue to work
- You can migrate incrementally, one environment at a time

---

## Custom Profiles

You can create custom profiles for specific use cases.

### Example: Custom CI/CD Profile

```python
# app/core/config/profiles.py

class CICDProfile(ConfigProfile):
    """Profile optimized for CI/CD pipelines."""

    @property
    def name(self) -> str:
        return "cicd"

    @property
    def description(self) -> str:
        return "CI/CD pipeline testing environment"

    def get_overrides(self) -> Dict[str, Any]:
        return {
            "MLOPS_DEBUG": "false",
            "MLOPS_LOG_LEVEL": "WARNING",
            "MLOPS_WORKERS": "1",
            "MLOPS_ENVIRONMENT": "cicd",

            # Disable all external services
            "MLOPS_REDIS_ENABLED": "false",
            "MLOPS_KAFKA_ENABLED": "false",
            "MLOPS_VAULT_ENABLED": "false",

            # Minimal resources for fast tests
            "MLOPS_PREDICTION_CACHE_MAX_SIZE": "10",
            "MLOPS_MAX_TEXT_LENGTH": "128",
        }

# Register the profile
ProfileRegistry.register_profile(CICDProfile())
```

Usage:

```bash
export MLOPS_PROFILE=cicd
pytest tests/
```

---

## Best Practices

### 1. Use Profiles for Environment Defaults

Don't repeat configuration across environments. Let profiles handle defaults.

❌ **Bad:**
```yaml
# Repeating 50+ environment variables in each ConfigMap
```

✅ **Good:**
```yaml
# Just set the profile and environment-specific overrides
MLOPS_PROFILE: "production"
MLOPS_REDIS_HOST: "redis-prod"
```

### 2. Override Only What's Necessary

Only set environment variables that differ from profile defaults.

❌ **Bad:**
```bash
MLOPS_PROFILE=production
MLOPS_DEBUG=false  # Redundant - already false in production profile
MLOPS_LOG_LEVEL=WARNING  # Redundant
MLOPS_WORKERS=4  # Redundant
```

✅ **Good:**
```bash
MLOPS_PROFILE=production
MLOPS_REDIS_HOST=my-custom-redis-server  # Only override what's specific
```

### 3. Keep Secrets in Secret Management

Never put credentials in profiles or ConfigMaps.

❌ **Bad:**
```yaml
MLOPS_PROFILE: "production"
MLOPS_API_KEY: "my-secret-key"  # Don't do this!
```

✅ **Good:**
```yaml
# ConfigMap
MLOPS_PROFILE: "production"

# Secret (separate)
MLOPS_API_KEY: <encrypted-value>
```

### 4. Document Custom Overrides

If you override profile defaults, document why.

```yaml
# ConfigMap
MLOPS_PROFILE: "production"

# Custom: Increased cache size for high-traffic load
MLOPS_PREDICTION_CACHE_MAX_SIZE: "50000"

# Custom: Our Redis cluster endpoint
MLOPS_REDIS_HOST: "redis-cluster-prod.internal"
```

### 5. Test Profile Changes

When adding or modifying profiles, test all affected environments.

```bash
# Test each profile
MLOPS_PROFILE=local pytest
MLOPS_PROFILE=development pytest
MLOPS_PROFILE=staging pytest
MLOPS_PROFILE=production pytest
```

---

## Troubleshooting

### Profile Not Loading

**Problem:** Settings don't match expected profile defaults

**Solution:**
```python
# Check if profile is loading
from app.core.config import settings

print(f"Active profile: {settings.get_active_profile()}")
print(f"Environment: {settings.environment}")
print(f"Debug mode: {settings.debug}")
```

### Verify Profile Defaults

```python
from app.core.config.profiles import load_profile

# See what defaults a profile provides
overrides = load_profile('production')
for key, value in overrides.items():
    print(f"{key}={value}")
```

### List Available Profiles

```python
from app.core.config import Settings

profiles = Settings.get_available_profiles()
for name, info in profiles.items():
    print(f"{name}: {info['description']}")
```

---

## Reference

### Environment Variable: `MLOPS_PROFILE`

- **Type:** String
- **Options:** `local`, `development` (or `dev`), `staging`, `production` (or `prod`)
- **Default:** `development` (if not set)
- **Location:** Can be set in:
  - Environment variables
  - `.env` file
  - Docker build args
  - Kubernetes ConfigMap

### Profile Files

- **Profile definitions:** `app/core/config/profiles.py`
- **Profile registry:** `ProfileRegistry` class
- **Template files:**
  - `.env.local.template`
  - `.env.development.template`
  - `.env.staging.template`
  - `.env.production.template`

### Kubernetes Files

- **Development:** `k8s/config-dev.yaml`
- **Staging:** `k8s/config-staging.yaml`
- **Production:** `k8s/config-production.yaml`

---

## Additional Resources

- [Configuration Architecture](CONFIGURATION_ARCHITECTURE.md)
- [Environment Configurations](ENVIRONMENT_CONFIGURATIONS.md)
- [Deployment Guide](setup/DEPLOYMENT.md)
- [Security Best Practices](SECURITY.md)

---

**Last Updated:** 2025-11-14
**Maintained By:** KubeSentiment Team
