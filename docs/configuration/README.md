# Configuration Documentation

Complete guide to KubeSentiment's configuration system, including setup, architecture, profiles, and deployment.

## Quick Navigation

**Getting Started?**
- **[Quick Start](QUICK_START.md)** - 5-minute setup guide for local development

**Understanding the System?**
- **[Architecture](ARCHITECTURE.md)** - Domain-driven configuration design (10 min read)
- **[Profiles](PROFILES.md)** - Profile-based configuration defaults for different environments

**Setting Up an Environment?**
- **[Deployment](DEPLOYMENT.md)** - Environment-specific configurations (dev/staging/prod)
- **[Environment Variables](ENVIRONMENT_VARIABLES.md)** - Complete reference of all settings

**Upgrading or Migrating?**
- **[Migration Guide](MIGRATION.md)** - Upgrading to new configuration architecture
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

**Examples?**
- **[examples/](examples/)** - Copy-paste ready configuration files for all environments

---

## Table of Contents

1. [Overview](#overview)
2. [Document Map](#document-map)
3. [Quick Start](#quick-start)
4. [Configuration Profiles](#configuration-profiles)
5. [Environment Setup](#environment-setup)
6. [Key Concepts](#key-concepts)

---

## Overview

KubeSentiment uses a **profile-based configuration system** with **domain-driven architecture**. This means:

- **Profiles** provide environment-specific defaults (local, development, staging, production)
- **Domains** organize settings by functionality (server, model, kafka, redis, etc.)
- **Environment variables** override defaults as needed
- **100% backward compatible** - existing code works without changes

### Key Features

✅ Minimal configuration needed (just set `MLOPS_PROFILE`)
✅ Environment-specific defaults (no repetition)
✅ Domain-separated settings (easier to understand)
✅ Type-safe configuration with validation
✅ Full backward compatibility

---

## Document Map

### By Use Case

| Need | Document | Read Time |
|------|----------|-----------|
| Set up locally in 5 minutes | [Quick Start](QUICK_START.md) | 5 min |
| Understand the design | [Architecture](ARCHITECTURE.md) | 10 min |
| Deploy to dev/staging/prod | [Deployment](DEPLOYMENT.md) | 15 min |
| Find a specific setting | [Environment Variables](ENVIRONMENT_VARIABLES.md) | 5 min |
| Upgrade from old system | [Migration Guide](MIGRATION.md) | 10 min |
| Fix a problem | [Troubleshooting](TROUBLESHOOTING.md) | varies |
| Copy example configs | [examples/](examples/) | 2 min |

### By Role

| Role | Key Documents |
|------|---|
| **Developer** | Quick Start → Architecture → Deployment |
| **DevOps/SRE** | Deployment → Environment Variables → Troubleshooting |
| **Platform Engineer** | Architecture → Profiles → Environment Variables |
| **Upgrading Users** | Migration Guide |

---

## Quick Start

### Local Development (Fastest)

```bash
# 1. Set profile
export MLOPS_PROFILE=local

# 2. Run the app
python -m uvicorn app.main:app --reload

# That's it! All defaults are applied automatically
```

### With Services (Redis, Kafka)

```bash
# Copy a template
cp .env.development.template .env

# Edit as needed
export $(cat .env | xargs)

# Run with Docker Compose
docker-compose up
```

### Kubernetes

```bash
# Deploy to dev
kubectl apply -f docs/configuration/examples/kubernetes-dev.yaml

# Deploy to staging
kubectl apply -f docs/configuration/examples/kubernetes-staging.yaml
```

See **[Quick Start](QUICK_START.md)** for complete setup instructions.

---

## Configuration Profiles

KubeSentiment includes 4 built-in profiles optimized for different environments:

### Local Profile
- **When:** Quick local testing without external services
- **Services:** All disabled (no Redis, Kafka, Vault)
- **Debug:** Enabled (verbose output)
- **Setup:** `export MLOPS_PROFILE=local`

### Development Profile
- **When:** Feature development with optional services
- **Services:** Disabled by default (can enable individually)
- **Debug:** Enabled
- **Setup:** `export MLOPS_PROFILE=development`

### Staging Profile
- **When:** Pre-production testing
- **Services:** All enabled (Redis, Vault, tracing)
- **Debug:** Disabled
- **Setup:** `export MLOPS_PROFILE=staging`

### Production Profile
- **When:** Live production deployment
- **Services:** All enabled (Redis, Kafka, Vault, Data Lake)
- **Performance:** Optimized
- **Security:** Strict
- **Setup:** `export MLOPS_PROFILE=production`

See **[Profiles](PROFILES.md)** for complete defaults for each profile.

---

## Environment Setup

Configure each environment with appropriate settings:

### Development Environment
- 1 replica, debug mode on
- FastAPI hot-reload enabled
- Minimal monitoring
- No authentication required

### Staging Environment
- 2 replicas, HA enabled
- Production-like configuration
- Full monitoring and tracing
- Authentication enabled
- Pre-production testing

### Production Environment
- 3+ replicas, auto-scaling enabled
- Maximum reliability and performance
- All MLOps features enabled
- Security hardened
- Full observability stack

See **[Deployment](DEPLOYMENT.md)** for complete environment-specific configurations including Helm values, resource limits, and deployment commands.

---

## Key Concepts

### Profiles
Environment-specific sets of default values. Set once with `MLOPS_PROFILE`, apply to all settings automatically.

```bash
MLOPS_PROFILE=production  # Automatically sets 50+ defaults
MLOPS_REDIS_HOST=custom   # Override just what's different
```

### Domains
Logical groupings of configuration settings by functionality:

- **Server:** App name, port, host, debug mode
- **Model:** Model name, cache settings, max text length
- **Kafka:** Bootstrap servers, consumer groups, DLQ settings
- **Redis:** Host, port, connection pool, cache TTL
- **Security:** API keys, CORS origins, authentication
- **Monitoring:** Metrics, logging, tracing configuration
- ... and 4 more (vault, performance, data_lake, mlops)

Access domain settings:
```python
settings.model.model_name        # New style (recommended)
settings.model_name              # Old style (still works)
```

### Configuration Loading Order
1. Profile defaults (lowest priority)
2. `.env` file values
3. Environment variables
4. Pydantic field defaults (highest priority)

This allows:
- Profiles provide sensible defaults
- Environment variables override for specific deployments
- Secrets stay in vault/env, not in code

### Backward Compatibility
The new domain-driven architecture is **100% backward compatible** with existing code. All old property names still work via delegation to domain objects:

```python
settings.model_name      # → settings.model.model_name
settings.kafka_enabled   # → settings.kafka.kafka_enabled
```

---

## Configuration Files

### Complete File Inventory

#### Core Documentation (This Directory)

| File | Purpose | Read Time | Audience |
|------|---------|-----------|----------|
| `README.md` (this file) | Navigation and overview | 5 min | Everyone |
| `QUICK_START.md` | 5-minute setup guide | 5 min | Developers |
| `ARCHITECTURE.md` | Detailed architecture and design | 15 min | Architects, Developers |
| `PROFILES.md` | Profile defaults and overrides | 10 min | DevOps, Developers |
| `DEPLOYMENT.md` | Environment-specific configurations | 20 min | DevOps, SREs |
| `ENVIRONMENT_VARIABLES.md` | Complete settings reference | 10 min | Everyone |
| `MIGRATION.md` | Upgrade guide from old system | 15 min | Upgrading users |
| `TROUBLESHOOTING.md` | Common issues and solutions | varies | Everyone |
| `examples/` | Copy-paste ready configuration files | 2 min | Developers |

#### Example Files (`examples/`)

| File | Purpose |
|------|---------|
| `.env.local` | Local development environment template |
| `.env.development` | Development environment template |
| `docker-compose-dev.yml` | Docker Compose for development |
| `kubernetes-dev.yaml` | Kubernetes manifests for dev |
| `kubernetes-staging.yaml` | Kubernetes manifests for staging |
| `kubernetes-prod.yaml` | Kubernetes manifests for production |
| `README.md` | Examples documentation |

### In Application Code

| File | Purpose |
|------|---------|
| `app/core/config/__init__.py` | Package exports |
| `app/core/config/settings.py` | Root Settings class |
| `app/core/config/server.py` | ServerConfig domain |
| `app/core/config/model.py` | ModelConfig domain |
| `app/core/config/kafka.py` | KafkaConfig domain (30+ settings) |
| `app/core/config/redis.py` | RedisConfig domain |
| `app/core/config/vault.py` | VaultConfig domain |
| `app/core/config/security.py` | SecurityConfig domain |
| `app/core/config/performance.py` | PerformanceConfig domain |
| `app/core/config/data_lake.py` | DataLakeConfig domain |
| `app/core/config/monitoring.py` | MonitoringConfig domain |
| `app/core/config/mlops.py` | MLOpsConfig domain |

### Environment Templates

| File | Purpose |
|------|---------|
| `.env.local.template` | Local development |
| `.env.development.template` | Development with services |
| `.env.staging.template` | Staging environment |
| `.env.production.template` | Production environment |

---

## Common Tasks

### Setting Up Local Development

See **[Quick Start](QUICK_START.md)** for step-by-step instructions.

### Deploying to an Environment

See **[Deployment](DEPLOYMENT.md)** for:
- Helm values for dev/staging/prod
- Kubernetes manifests
- Deployment commands
- Promotion procedures

### Finding a Specific Setting

See **[Environment Variables](ENVIRONMENT_VARIABLES.md)** for:
- Complete reference of all settings
- Default values by profile
- Validation rules
- Use cases

### Understanding the Configuration Design

See **[Architecture](ARCHITECTURE.md)** for:
- Domain-driven design overview
- Each of 10 configuration domains
- Why the architecture was chosen
- Usage patterns and examples

### Upgrading from Old System

See **[Migration Guide](MIGRATION.md)** for:
- What changed
- Required code updates (if any)
- Migration examples
- FAQ and troubleshooting

### Fixing Configuration Issues

See **[Troubleshooting](TROUBLESHOOTING.md)** for:
- Profile not loading
- Environment variable not taking effect
- Validation errors
- Configuration conflicts

---

## Examples

Pre-built configuration examples for common scenarios:

```bash
# Copy example for your use case
cp docs/configuration/examples/docker-compose.yml .
cp docs/configuration/examples/.env.development.example .env

# Edit as needed and run
docker-compose up
```

See **[examples/](examples/)** directory for:
- `.env.local` - Local development setup
- `.env.development` - Development with services
- `docker-compose.yml` - Docker Compose for dev
- `kubernetes-dev.yaml` - Kubernetes dev environment
- `kubernetes-staging.yaml` - Kubernetes staging
- `kubernetes-prod.yaml` - Kubernetes production

---

## Environment Variables Quick Reference

All settings use the `MLOPS_` prefix and can be set via:

```bash
export MLOPS_PROFILE=production
export MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
export MLOPS_REDIS_ENABLED=true
```

See **[Environment Variables](ENVIRONMENT_VARIABLES.md)** for complete reference.

---

## Best Practices

### For Configuration

1. **Use profiles for environment defaults**
   ```bash
   MLOPS_PROFILE=production  # Sets 50+ sensible defaults
   ```

2. **Override only what's different**
   ```bash
   MLOPS_PROFILE=production
   MLOPS_REDIS_HOST=custom-redis  # Only override this
   ```

3. **Keep secrets in Vault, not environment variables**
   ```bash
   # Don't do this:
   MLOPS_API_KEY=secret-key  # ❌

   # Do this:
   MLOPS_VAULT_ENABLED=true  # ✅
   ```

4. **Document custom overrides**
   ```yaml
   # ConfigMap - document why non-standard values are used
   MLOPS_PROFILE: "production"
   MLOPS_PREDICTION_CACHE_MAX_SIZE: "50000"  # Custom: High-traffic load
   ```

5. **Test with each profile**
   ```bash
   MLOPS_PROFILE=local pytest
   MLOPS_PROFILE=development pytest
   MLOPS_PROFILE=staging pytest
   MLOPS_PROFILE=production pytest
   ```

### For Development

1. Start with `MLOPS_PROFILE=local` for minimal setup
2. Enable services individually as needed
3. Use `.env` files, not environment variables
4. Never commit `.env` files to git

### For Deployment

1. Always use profiles (dev/staging/prod)
2. Keep environment-specific values in ConfigMaps/Secrets
3. Use Vault for sensitive data
4. Test in staging before production
5. Monitor configuration in production dashboards

---

## Getting Help

**Where to look:**

| Issue | Document |
|-------|----------|
| "How do I...?" | [Quick Start](QUICK_START.md) or [Deployment](DEPLOYMENT.md) |
| "What setting controls...?" | [Environment Variables](ENVIRONMENT_VARIABLES.md) |
| "Why is it configured this way?" | [Architecture](ARCHITECTURE.md) |
| "I'm getting an error" | [Troubleshooting](TROUBLESHOOTING.md) |
| "I upgraded and something broke" | [Migration Guide](MIGRATION.md) |

**Additional resources:**

- Application code: `app/core/config/` modules
- CLAUDE.md: Project-level configuration instructions
- ADR-009: Architecture decision for profile-based configuration

---

## Documentation Consolidation Status

### Consolidated Files (Single Source of Truth)

All configuration documentation is now consolidated in `docs/configuration/`:

- ✅ **Architecture** - `ARCHITECTURE.md` (consolidated from `CONFIGURATION_ARCHITECTURE.md`)
- ✅ **Profiles** - `PROFILES.md` (consolidated from `CONFIGURATION_PROFILES.md`)
- ✅ **Deployment** - `DEPLOYMENT.md` (consolidated from `ENVIRONMENT_CONFIGURATIONS.md`)
- ✅ **Migration** - `MIGRATION.md` (consolidated from `CONFIGURATION_MIGRATION.md`)
- ✅ **Troubleshooting** - `TROUBLESHOOTING.md` (merged config troubleshooting from root `TROUBLESHOOTING.md`)

### Deprecated Files (Removed)

The following deprecated files have been removed and replaced with references to consolidated docs:

- ❌ `docs/CONFIGURATION_ARCHITECTURE.md` → See `docs/configuration/ARCHITECTURE.md`
- ❌ `docs/CONFIGURATION_PROFILES.md` → See `docs/configuration/PROFILES.md`
- ❌ `docs/ENVIRONMENT_CONFIGURATIONS.md` → See `docs/configuration/DEPLOYMENT.md`
- ❌ `docs/CONFIGURATION_MIGRATION.md` → See `docs/configuration/MIGRATION.md`

### Updated References

The following files have been updated to reference consolidated configuration docs:

- ✅ `README.md` - Updated configuration section
- ✅ `CLAUDE.md` - Already references `docs/configuration/`
- ✅ `docs/DEVELOPER_SETUP.md` - References consolidated config docs
- ✅ `docs/QUICK_REFERENCE.md` - References consolidated config docs
- ✅ `docs/TROUBLESHOOTING.md` - References config troubleshooting
- ✅ `docs/setup/deployment-guide.md` - References consolidated deployment docs

## Version History

| Date | Changes |
|------|---------|
| 2025-11-25 | Consolidated configuration documentation into unified `docs/configuration/` directory |
| 2025-11-25 | Removed deprecated root-level configuration docs and updated all cross-references |
| Previous | Individual configuration docs spread across docs/ directory |

---

**Last Updated:** 2025-11-25
**Maintained By:** KubeSentiment Team

For detailed information on any topic, see the linked documents above.
