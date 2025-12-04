# Configuration Profiles

Profile-based configuration system with environment-specific defaults.

## Table of Contents

1. [Overview](#overview)
2. [Available Profiles](#available-profiles)
3. [Using Profiles](#using-profiles)
4. [Profile Defaults](#profile-defaults)
5. [Overriding Profiles](#overriding-profiles)
6. [Custom Profiles](#custom-profiles)
7. [Best Practices](#best-practices)

---

## Overview

Instead of manually setting 50+ environment variables for each environment, KubeSentiment provides **profiles** with sensible defaults.

**How it works:**
1. Set `MLOPS_PROFILE=production`
2. System automatically applies 50+ defaults for production
3. Override only what's different for your deployment

### Problem Solved

**Before (Manual):**
```bash
export MLOPS_DEBUG=false
export MLOPS_LOG_LEVEL=WARNING
export MLOPS_WORKERS=4
export MLOPS_ENVIRONMENT=production
export MLOPS_REDIS_ENABLED=true
export MLOPS_REDIS_MAX_CONNECTIONS=100
export MLOPS_KAFKA_ENABLED=true
export MLOPS_KAFKA_CONSUMER_THREADS=8
# ... 40+ more variables
```

**After (Profiles):**
```bash
export MLOPS_PROFILE=production
export MLOPS_REDIS_HOST=my-redis  # Only what's different
```

---

## Available Profiles

### 1. Local Profile

**When to use:** Quick testing without external services

**Key Features:**
- ❌ All external services disabled (Redis, Kafka, Vault)
- 🎯 Minimal configuration required
- ✨ Fast startup
- 🐛 Debug mode enabled

**Ideal For:**
- Quick local testing
- Development without Docker Compose
- CI/CD unit tests
- Verification that code compiles

**Setup:**
```bash
export MLOPS_PROFILE=local
python -m uvicorn app.main:app --reload
```

**Key Defaults:**
```bash
MLOPS_DEBUG=true
MLOPS_WORKERS=1
MLOPS_ENVIRONMENT=local
MLOPS_HOST=127.0.0.1
MLOPS_LOG_LEVEL=INFO

# All external services disabled
MLOPS_REDIS_ENABLED=false
MLOPS_KAFKA_ENABLED=false
MLOPS_VAULT_ENABLED=false
MLOPS_DATA_LAKE_ENABLED=false
MLOPS_MLFLOW_ENABLED=false

# Minimal caching
MLOPS_PREDICTION_CACHE_MAX_SIZE=100
MLOPS_PREDICTION_CACHE_ENABLED=true
MLOPS_PREDICTION_CACHE_ENABLED=true
```

---

### 2. Development Profile

**When to use:** Feature development with optional services

**Key Features:**
- 🐛 Debug mode enabled
- 📝 Verbose logging (DEBUG level)
- 🔌 External services disabled by default (enable as needed)
- 📦 Small cache sizes
- 🔓 Permissive CORS

**Ideal For:**
- Feature development
- Integration testing
- Debugging issues
- Local development with Docker Compose

**Setup:**
```bash
export MLOPS_PROFILE=development

# Enable services as needed
export MLOPS_REDIS_ENABLED=true
export MLOPS_KAFKA_ENABLED=true
```

**Key Defaults:**
```bash
MLOPS_DEBUG=true
MLOPS_WORKERS=1
MLOPS_ENVIRONMENT=development
MLOPS_LOG_LEVEL=DEBUG
MLOPS_ENABLE_METRICS=true
MLOPS_ENABLE_TRACING=false

# External services disabled by default
MLOPS_REDIS_ENABLED=false
MLOPS_KAFKA_ENABLED=false
MLOPS_VAULT_ENABLED=false
MLOPS_DATA_LAKE_ENABLED=false

# MLOps features disabled for faster startup
MLOPS_MLFLOW_ENABLED=false
MLOPS_DRIFT_DETECTION_ENABLED=false
MLOPS_EXPLAINABILITY_ENABLED=false

# Relaxed security
MLOPS_API_KEY=""
MLOPS_ALLOWED_ORIGINS="*"

# Small cache
MLOPS_PREDICTION_CACHE_MAX_SIZE=100
MLOPS_PREDICTION_CACHE_ENABLED=true
MLOPS_MAX_TEXT_LENGTH=512
```

---

### 3. Staging Profile

**When to use:** Pre-production testing and validation

**Key Features:**
- ✅ Production-like configuration
- 📊 Redis and Vault enabled
- 🚀 MLOps features enabled (MLflow, drift detection)
- 📈 Distributed tracing enabled
- ⚡ Moderate resource allocation

**Ideal For:**
- Pre-production validation
- Performance testing
- User acceptance testing (UAT)
- Integration testing in realistic environment

**Setup:**
```bash
export MLOPS_PROFILE=staging

# Override service endpoints
export MLOPS_REDIS_HOST=redis-staging
export MLOPS_VAULT_ADDR=https://vault-staging.example.com
```

**Key Defaults:**
```bash
MLOPS_DEBUG=false
MLOPS_WORKERS=2
MLOPS_ENVIRONMENT=staging
MLOPS_LOG_LEVEL=INFO
MLOPS_ENABLE_METRICS=true
MLOPS_ENABLE_TRACING=true
MLOPS_TRACING_BACKEND=jaeger

# External services enabled
MLOPS_REDIS_ENABLED=true
MLOPS_KAFKA_ENABLED=false  # Optional in staging
MLOPS_VAULT_ENABLED=true
MLOPS_DATA_LAKE_ENABLED=false

# MLOps features enabled
MLOPS_MLFLOW_ENABLED=true
MLOPS_DRIFT_DETECTION_ENABLED=true
MLOPS_EXPLAINABILITY_ENABLED=true

# Performance features
MLOPS_ASYNC_BATCH_ENABLED=true
MLOPS_ASYNC_BATCH_SIZE=50
MLOPS_ASYNC_BATCH_TIMEOUT=5.0

# Moderate caching
MLOPS_PREDICTION_CACHE_MAX_SIZE=100
MLOPS_PREDICTION_CACHE_ENABLED=true0
MLOPS_PREDICTION_CACHE_ENABLED=true  # Disable if hit rate <5%
MLOPS_REDIS_PREDICTION_CACHE_TTL=3600
```

---

### 4. Production Profile

**When to use:** Live production deployment

**Key Features:**
- ✅ All services enabled (Redis, Kafka, Vault, Data Lake)
- ✅ All MLOps features enabled
- ⚡ Optimized performance settings
- 🔒 Strict security
- 🔇 Minimal logging (WARNING level)
- 💾 Large cache sizes
- 📡 Full observability (metrics, logs, traces)

**Ideal For:**
- Production deployments
- Maximum reliability
- Optimal performance
- Mission-critical systems

**Setup:**
```bash
export MLOPS_PROFILE=production

# Override service endpoints
export MLOPS_REDIS_HOST=redis-prod.internal
export MLOPS_KAFKA_BOOTSTRAP_SERVERS=kafka-prod.internal:9092
export MLOPS_VAULT_ADDR=https://vault.example.com
```

**Key Defaults:**
```bash
MLOPS_DEBUG=false
MLOPS_WORKERS=4
MLOPS_ENVIRONMENT=production
MLOPS_LOG_LEVEL=WARNING
MLOPS_ENABLE_METRICS=true
MLOPS_ENABLE_TRACING=true
MLOPS_TRACING_BACKEND=otlp

# All external services enabled
MLOPS_REDIS_ENABLED=true
MLOPS_KAFKA_ENABLED=true
MLOPS_VAULT_ENABLED=true
MLOPS_DATA_LAKE_ENABLED=true

# All MLOps features enabled
MLOPS_MLFLOW_ENABLED=true
MLOPS_DRIFT_DETECTION_ENABLED=true
MLOPS_EXPLAINABILITY_ENABLED=true

# Production-optimized performance
MLOPS_ASYNC_BATCH_ENABLED=true
MLOPS_ASYNC_BATCH_SIZE=100
MLOPS_ASYNC_BATCH_TIMEOUT=2.0
MLOPS_ASYNC_MAX_WORKERS=10

# Large caching
MLOPS_PREDICTION_CACHE_MAX_SIZE=100
MLOPS_PREDICTION_CACHE_ENABLED=true00
MLOPS_REDIS_MAX_CONNECTIONS=100
MLOPS_REDIS_PREDICTION_CACHE_TTL=7200

# Kafka optimized for production
MLOPS_KAFKA_CONSUMER_THREADS=8
MLOPS_KAFKA_BATCH_SIZE=200
MLOPS_KAFKA_MAX_POLL_RECORDS=1000
```

---

## Using Profiles

### Method 1: Environment Variable (Simplest)

```bash
export MLOPS_PROFILE=production
python -m uvicorn app.main:app
```

### Method 2: .env File

Create a `.env` file from templates:

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

Then edit and use:

```bash
export $(cat .env | xargs)
python -m uvicorn app.main:app
```

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
  MLOPS_REDIS_HOST: "redis-prod"  # Override if needed
```

### Method 5: Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    environment:
      - MLOPS_PROFILE=development
      - MLOPS_REDIS_ENABLED=true
      - MLOPS_REDIS_HOST=redis
```

---

## Overriding Profiles

Profile defaults are applied **only if the environment variable is not already set**. This allows:

1. Use profile defaults for most settings
2. Override specific settings as needed

### Example 1: Development with Redis Enabled

```bash
# .env file
MLOPS_PROFILE=development

# Override the default (Redis disabled in dev profile)
MLOPS_REDIS_ENABLED=true
MLOPS_REDIS_HOST=localhost
MLOPS_REDIS_PORT=6379
```

### Example 2: Production with Custom Cache Size

```bash
# .env file
MLOPS_PROFILE=production

# Override the default cache size (10000 in prod profile)
MLOPS_PREDICTION_CACHE_MAX_SIZE=50000
```

### Example 3: Staging with Custom Tracing Backend

```bash
# Kubernetes ConfigMap
MLOPS_PROFILE: "staging"
MLOPS_TRACING_BACKEND: "zipkin"  # Override jaeger default
MLOPS_ZIPKIN_ENDPOINT: "http://zipkin:9411"
```

---

## Priority Order

Configuration values are loaded in this order (highest priority first):

1. **Explicitly set environment variables** (highest priority)
2. **`.env` file values**
3. **Profile defaults**
4. **Pydantic field defaults** (lowest priority)

**Example:**

```bash
# Scenario: What port does the app use?

# .env file
MLOPS_PROFILE=production
MLOPS_PORT=8080

# System defaults production profile PORT to 8000
# But .env sets it to 8080
# Result: PORT = 8080 (from .env, overrides profile)

# If you then run:
export MLOPS_PORT=9000
# Result: PORT = 9000 (environment variable overrides .env)
```

---

## Profile Comparison

| Feature | Local | Development | Staging | Production |
|---------|-------|-------------|---------|------------|
| **Best For** | Quick test | Development | Pre-prod | Live traffic |
| **Services** | ❌ None | 🔌 Optional | ✅ All | ✅ All |
| **Debug Mode** | ✅ On | ✅ On | ❌ Off | ❌ Off |
| **Log Level** | INFO | DEBUG | INFO | WARNING |
| **Workers** | 1 | 1 | 2 | 4 |
| **Redis** | ❌ | ❌ | ✅ | ✅ |
| **Kafka** | ❌ | ❌ | ❌ | ✅ |
| **Vault** | ❌ | ❌ | ✅ | ✅ |
| **Metrics** | ❌ | ✅ | ✅ | ✅ |
| **Tracing** | ❌ | ❌ | ✅ | ✅ |
| **MLflow** | ❌ | ❌ | ✅ | ✅ |
| **Drift Detection** | ❌ | ❌ | ✅ | ✅ |
| **Cache Size** | 100 | 100 | 1000 | 10000 |
| **Cache TTL** | N/A | N/A | 1hr | 2hr |

---

## Custom Profiles

You can create custom profiles for specific use cases.

### Example: CI/CD Profile

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

**Usage:**
```bash
export MLOPS_PROFILE=cicd
pytest tests/
```

---

## Best Practices

### 1. Use Profiles for Environment Defaults

Don't repeat configuration across environments. Let profiles handle defaults.

❌ **Bad:**
```bash
# Repeating 50+ environment variables in each ConfigMap
```

✅ **Good:**
```bash
# Just set the profile and environment-specific overrides
MLOPS_PROFILE=production
MLOPS_REDIS_HOST=redis-prod
```

---

### 2. Override Only What's Necessary

Only set environment variables that differ from profile defaults.

❌ **Bad:**
```bash
MLOPS_PROFILE=production
MLOPS_DEBUG=false              # Redundant - already false in prod
MLOPS_LOG_LEVEL=WARNING        # Redundant
MLOPS_WORKERS=4                # Redundant
```

✅ **Good:**
```bash
MLOPS_PROFILE=production
MLOPS_REDIS_HOST=my-custom-redis  # Only override what's specific
```

---

### 3. Keep Secrets in Vault

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

---

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

---

### 5. Test Each Profile

When adding or modifying profiles, test all affected environments.

```bash
# Test each profile
MLOPS_PROFILE=local pytest
MLOPS_PROFILE=development pytest
MLOPS_PROFILE=staging pytest
MLOPS_PROFILE=production pytest
```

---

### 6. Keep Staging Close to Production

Staging should be as similar to production as possible to catch issues early.

```bash
# ✅ Good: Staging matches production
MLOPS_PROFILE=staging        # Same as production
MLOPS_REDIS_HOST=redis-staging  # Just different endpoint

# ❌ Bad: Staging is too different
MLOPS_PROFILE=staging
MLOPS_REDIS_ENABLED=false    # Disabled in staging but enabled in prod
```

---

## Troubleshooting

### Profile Not Loading

**Problem:** Settings don't match expected profile defaults

**Solution:**
```python
from app.core.config import get_settings

settings = get_settings()
print(f"Active profile: {settings.environment}")
print(f"Debug mode: {settings.server.debug}")
```

Check that:
1. `MLOPS_PROFILE` is set correctly
2. Profile name is exact (case-sensitive)
3. Check `app/core/config/profiles.py` for available profiles

### Verify Profile Defaults

```bash
# See what defaults a profile provides
python -c "
from app.core.config.profiles import load_profile
overrides = load_profile('production')
for key, value in sorted(overrides.items()):
    print(f'{key}={value}')
"
```

### List Available Profiles

```python
from app.core.config import Settings

profiles = Settings.get_available_profiles()
for name, info in profiles.items():
    print(f'{name}: {info[\"description\"]}')
```

---

## Related Documentation

- **[Quick Start](QUICK_START.md)** - 5-minute setup guide
- **[Architecture](ARCHITECTURE.md)** - Understanding the design
- **[Environment Variables](ENVIRONMENT_VARIABLES.md)** - Complete settings reference
- **[Deployment](DEPLOYMENT.md)** - Environment-specific configurations
- **[Migration Guide](MIGRATION.md)** - Upgrading to new system
- **ADR-009** - Architecture decision for profile-based configuration

---

**Last Updated:** 2025-11-25
**Maintained By:** KubeSentiment Team
