# Configuration Architecture

Deep dive into KubeSentiment's domain-driven configuration system.

## Table of Contents

1. [Overview](#overview)
2. [Evolution: Before vs After](#evolution-before-vs-after)
3. [Architecture Principles](#architecture-principles)
4. [Configuration Domains](#configuration-domains)
5. [Root Settings Class](#root-settings-class)
6. [Usage Patterns](#usage-patterns)
7. [Testing Strategy](#testing-strategy)
8. [Best Practices](#best-practices)

---

## Overview

KubeSentiment uses a **domain-driven configuration architecture** that:

- **Separates concerns** - Each domain (Kafka, Redis, Model, etc.) has its own config class
- **Maintains compatibility** - 100% backward compatible with existing code via delegation properties
- **Improves testability** - Mock only the specific domain you need to test
- **Scales better** - Adding new settings doesn't impact existing code
- **Clarifies intent** - It's obvious which configuration domain a component depends on

---

## Evolution: Before vs After

### Before: Monolithic Settings

```
app/core/config.py
└── Settings class (917 lines, 90+ fields)
    ├── Server settings
    ├── Model settings
    ├── Kafka settings (30+ fields)
    ├── Redis settings
    ├── Vault settings
    ├── Data lake settings
    ├── Monitoring settings
    └── ... (mixed responsibilities)
```

**Problems:**
- ❌ God Object anti-pattern
- ❌ Hard to navigate (917 lines to search through)
- ❌ Difficult to test (mock entire Settings for one field)
- ❌ Violates Single Responsibility Principle
- ❌ High cognitive load for new developers
- ❌ Hard to add new settings (where do they go?)

### After: Domain-Driven Configuration

```
app/core/config/
├── __init__.py              (exports)
├── settings.py              (Root Settings - composition)
├── server.py                (ServerConfig - 62 lines)
├── model.py                 (ModelConfig - 118 lines)
├── security.py              (SecurityConfig - 99 lines)
├── performance.py           (PerformanceConfig - 116 lines)
├── kafka.py                 (KafkaConfig - 191 lines)
├── redis.py                 (RedisConfig - 94 lines)
├── vault.py                 (VaultConfig - 57 lines)
├── data_lake.py             (DataLakeConfig - 132 lines)
├── monitoring.py            (MonitoringConfig - 116 lines)
└── mlops.py                 (MLOpsConfig - 99 lines)
```

**Benefits:**
- ✅ Single Responsibility (one domain per config)
- ✅ Easier navigation (find settings in focused 100-line files)
- ✅ Better testing (mock only needed domains)
- ✅ Clearer dependencies (obvious which config a component needs)
- ✅ Type safety (explicit types per domain)
- ✅ 100% backward compatible

---

## Architecture Principles

### 1. Domain-Driven Design

Each configuration domain represents a functional area:

```
ServerConfig      → Application metadata and server settings
ModelConfig       → Machine learning model configuration
SecurityConfig    → Authentication and CORS
PerformanceConfig → Async processing, caching, batching
KafkaConfig       → Message streaming (30+ settings)
RedisConfig       → Distributed caching
VaultConfig       → Secrets management
DataLakeConfig    → Cloud storage (S3/GCS/Azure)
MonitoringConfig  → Metrics, logging, tracing
MLOpsConfig       → Model lifecycle (MLflow, drift detection)
```

### 2. Composition Over Inheritance

The root Settings class **composes** all domains:

```python
class Settings(BaseSettings):
    server: ServerConfig = ServerConfig()
    model: ModelConfig = ModelConfig()
    kafka: KafkaConfig = KafkaConfig()
    redis: RedisConfig = RedisConfig()
    # ... other domains
```

**Why composition?**
- Clear separation of concerns
- Easy to mock individual domains
- No inheritance complexity
- Easy to understand dependencies

### 3. Backward Compatibility Layer

Properties delegate to domain objects for old code:

```python
@property
def model_name(self) -> str:
    """Model name (backward compatibility)."""
    return self.model.model_name

@property
def kafka_enabled(self) -> bool:
    """Kafka enabled (backward compatibility)."""
    return self.kafka.kafka_enabled
```

**Result:** All existing code works without changes!

### 4. Validation at Multiple Levels

**Domain-level validation:**
- Each config validates its own fields
- Example: API key must be 8+ characters

**Root-level validation:**
- Cross-domain constraints
- Example: Debug mode incompatible with multiple workers
- Example: Model must be in allowed_models list

---

## Configuration Domains

### 1. ServerConfig

**Purpose:** Application metadata and server settings

**Settings:**
- `app_name` - Application name
- `app_version` - Semantic version
- `debug` - Debug mode flag
- `environment` - Deployment environment (dev/staging/prod)
- `host` - Server bind address
- `port` - Server port (1024-65535)
- `workers` - Worker process count (1-16)

**Example:**
```python
from app.core.config import get_settings

settings = get_settings()
print(f"{settings.server.app_name} v{settings.server.app_version}")
print(f"Running on {settings.server.host}:{settings.server.port}")
```

**Environment Variables:**
```bash
MLOPS_APP_NAME="My Service"
MLOPS_PORT=8080
MLOPS_WORKERS=4
MLOPS_DEBUG=true
```

---

### 2. ModelConfig

**Purpose:** Machine learning model configuration

**Settings:**
- `model_name` - HuggingFace model identifier
- `allowed_models` - Whitelist of permitted models
- `model_cache_dir` - Model cache directory path
- `onnx_model_path` - ONNX model directory
- `max_text_length` - Maximum input length (1-10000)
- `prediction_cache_max_size` - LRU cache size (10-100000)
- `enable_feature_engineering` - Advanced features flag

**Validators:**
- Model name format validation
- Model name in allowed list check
- Cache directory path validation

**Example:**
```python
from app.core.config import get_settings

settings = get_settings()
model = settings.model
print(f"Model: {model.model_name}")
print(f"Allowed: {model.allowed_models}")
print(f"Cache size: {model.prediction_cache_max_size}")
```

---

### 3. SecurityConfig

**Purpose:** Authentication and CORS configuration

**Settings:**
- `api_key` - API key for authentication (min 8 chars)
- `allowed_origins` - CORS whitelist (no wildcards)
- `max_request_timeout` - Request timeout in seconds (1-300)

**Validators:**
- API key strength (min 8 chars, letters + numbers)
- CORS URL format validation
- Wildcard origin blocked for security

**Example:**
```python
from app.core.config import get_settings

settings = get_settings()
if settings.security.api_key:
    print("API key authentication enabled")
print(f"CORS origins: {settings.security.allowed_origins}")
```

---

### 4. PerformanceConfig

**Purpose:** Async processing and performance tuning

**Async Batch Settings:**
- `async_batch_enabled` - Enable async batch processing
- `async_batch_max_jobs` - Max concurrent jobs (10-10000)
- `async_batch_max_batch_size` - Max batch size (10-10000)
- `async_batch_default_timeout_seconds` - Job timeout (30-3600)
- `async_batch_priority_*_limit` - Priority queue limits
- `async_batch_cleanup_interval_seconds` - Cleanup interval
- `async_batch_cache_ttl_seconds` - Result cache TTL
- `async_batch_result_cache_max_size` - Result cache size

**Anomaly Buffer Settings:**
- `anomaly_buffer_enabled` - Enable anomaly detection
- `anomaly_buffer_max_size` - Max anomalies to store
- `anomaly_buffer_default_ttl` - TTL for anomalies
- `anomaly_buffer_cleanup_interval` - Cleanup interval

---

### 5. KafkaConfig

**Purpose:** Kafka streaming and messaging (30+ settings)

**Basic Settings:**
- `kafka_enabled` - Enable Kafka streaming
- `kafka_bootstrap_servers` - Kafka broker list
- `kafka_consumer_group` - Consumer group ID
- `kafka_topic` - Topic to consume from

**Consumer Settings:**
- `kafka_auto_offset_reset` - earliest/latest/none
- `kafka_max_poll_records` - Records per poll (1-10000)
- `kafka_session_timeout_ms` - Session timeout
- `kafka_heartbeat_interval_ms` - Heartbeat interval
- `kafka_max_poll_interval_ms` - Max poll interval
- `kafka_enable_auto_commit` - Auto commit flag
- `kafka_auto_commit_interval_ms` - Auto commit interval

**High-Throughput Settings:**
- `kafka_consumer_threads` - Parallel threads (1-32)
- `kafka_batch_size` - Batch processing size
- `kafka_processing_timeout_ms` - Batch timeout
- `kafka_buffer_size` - Message queue buffer

**Dead Letter Queue:**
- `kafka_dlq_topic` - DLQ topic name
- `kafka_dlq_enabled` - Enable DLQ
- `kafka_max_retries` - Max retries before DLQ

**Producer Settings:**
- `kafka_producer_acks` - Acknowledgment level (0/1/all)
- `kafka_producer_retries` - Retry count
- `kafka_producer_batch_size` - Batch size in bytes
- `kafka_producer_compression_type` - Compression type

---

### 6. RedisConfig

**Purpose:** Redis distributed caching

**Settings:**
- `redis_enabled` - Enable Redis
- `redis_host` - Redis server host
- `redis_port` - Redis server port (1-65535)
- `redis_db` - Database number (0-15)
- `redis_password` - Authentication password
- `redis_max_connections` - Connection pool size (10-1000)
- `redis_socket_timeout` - Socket timeout (1-60)
- `redis_socket_connect_timeout` - Connection timeout
- `redis_namespace` - Key prefix namespace
- `redis_prediction_cache_ttl` - Prediction cache TTL
- `redis_feature_cache_ttl` - Feature cache TTL

---

### 7. VaultConfig

**Purpose:** HashiCorp Vault secrets management

**Settings:**
- `vault_enabled` - Enable Vault integration
- `vault_addr` - Vault server address
- `vault_namespace` - Vault namespace (Enterprise)
- `vault_role` - Kubernetes service account role
- `vault_mount_point` - KV v2 secrets engine mount
- `vault_secrets_path` - Base secrets path
- `vault_token` - Direct auth token

---

### 8. DataLakeConfig

**Purpose:** Cloud storage integration (AWS/GCP/Azure)

**Core Settings:**
- `data_lake_enabled` - Enable data lake
- `data_lake_provider` - s3/gcs/azure
- `data_lake_bucket` - Bucket/container name
- `data_lake_prefix` - Path prefix
- `data_lake_batch_size` - Predictions per batch
- `data_lake_batch_timeout_seconds` - Flush timeout
- `data_lake_compression` - Compression format
- `data_lake_partition_by` - Partition strategy (date/hour/model)

**Cloud-Specific Settings:**
- **AWS S3:** `data_lake_s3_region`, `data_lake_s3_endpoint_url`
- **GCP:** `data_lake_gcs_project`, `data_lake_gcs_credentials_path`
- **Azure:** `data_lake_azure_account_name`, `data_lake_azure_account_key`

**Query Engines:**
- `data_lake_enable_athena` - AWS Athena compatibility
- `data_lake_enable_bigquery` - BigQuery compatibility
- `data_lake_enable_synapse` - Azure Synapse compatibility

---

### 9. MonitoringConfig

**Purpose:** Metrics, logging, and distributed tracing

**Metrics:**
- `enable_metrics` - Enable Prometheus metrics
- `log_level` - DEBUG/INFO/WARNING/ERROR/CRITICAL
- `metrics_cache_ttl` - Metrics cache TTL (1-300)

**Advanced Metrics:**
- `advanced_metrics_enabled` - Enable advanced KPIs
- `advanced_metrics_detailed_tracking` - Per-prediction tracking
- `advanced_metrics_history_hours` - History retention
- `advanced_metrics_cost_per_1k` - Cost per 1k predictions

**Distributed Tracing:**
- `enable_tracing` - Enable tracing
- `tracing_backend` - jaeger/zipkin/otlp/console
- `service_name` - Service name for traces

**Tracing Backends:**
- **Jaeger:** `jaeger_agent_host`, `jaeger_agent_port`
- **Zipkin:** `zipkin_endpoint`
- **OTLP:** `otlp_endpoint`

**Exclusions:**
- `tracing_excluded_urls` - Comma-separated URL list to skip

---

### 10. MLOpsConfig

**Purpose:** Model lifecycle management

**MLflow:**
- `mlflow_enabled` - Enable MLflow registry
- `mlflow_tracking_uri` - Tracking server URI
- `mlflow_registry_uri` - Registry URI
- `mlflow_experiment_name` - Experiment name
- `mlflow_model_name` - Registered model name

**Drift Detection:**
- `drift_detection_enabled` - Enable drift detection
- `drift_window_size` - Sample window size (100-10000)
- `drift_psi_threshold` - PSI threshold (0.0-1.0)
- `drift_ks_threshold` - KS test p-value
- `drift_min_samples` - Min samples before check

**Explainability:**
- `explainability_enabled` - Enable explainability
- `explainability_use_attention` - Use attention weights
- `explainability_use_gradients` - Use gradients (slower)

---

## Root Settings Class

The root `Settings` class in `settings.py` composes all domains:

```python
class Settings(BaseSettings):
    """Main settings class composing all domain-specific configurations."""

    # Domain-specific configuration objects
    server: ServerConfig = ServerConfig()
    model: ModelConfig = ModelConfig()
    security: SecurityConfig = SecurityConfig()
    performance: PerformanceConfig = PerformanceConfig()
    kafka: KafkaConfig = KafkaConfig()
    redis: RedisConfig = RedisConfig()
    vault: VaultConfig = VaultConfig()
    data_lake: DataLakeConfig = DataLakeConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    mlops: MLOpsConfig = MLOpsConfig()

    # 50+ backward compatibility properties
    @property
    def model_name(self) -> str:
        """Model name (backward compatibility)."""
        return self.model.model_name
```

### Backward Compatibility

The Settings class provides **50+ @property methods** for backward compatibility with existing code:

```python
# These all work (backward compatible):
settings.model_name           → settings.model.model_name
settings.kafka_enabled        → settings.kafka.kafka_enabled
settings.redis_host           → settings.redis.redis_host
settings.port                 → settings.server.port
```

**Result:** All existing code continues to work without modifications!

### Cross-Field Validation

The Settings class maintains cross-field validators:

```python
@model_validator(mode="after")
def validate_configuration_consistency(self):
    self._validate_model_in_allowed_list()
    self._validate_worker_count_consistency()
    self._validate_cache_memory_usage()
    return self
```

**Validators:**
- Model name must be in allowed_models list
- Debug mode incompatible with multiple workers
- Cache memory usage check (< 1GB)

---

## Usage Patterns

### Pattern 1: Domain-Specific Access (Recommended for New Code)

```python
from app.core.config import Settings, get_settings

settings = get_settings()

# Access through domain objects - clear and explicit
print(f"Server: {settings.server.host}:{settings.server.port}")
print(f"Model: {settings.model.model_name}")
print(f"Kafka: {settings.kafka.kafka_bootstrap_servers}")
print(f"Redis: {settings.redis.redis_enabled}")
```

**Benefits:**
- ✅ Clear domain separation
- ✅ IDE autocomplete works better
- ✅ Easy to mock specific domains in tests
- ✅ Obvious which configuration domain is used

---

### Pattern 2: Backward-Compatible Access (Existing Code)

```python
from app.core.config import Settings, get_settings

settings = get_settings()

# Access through root properties (backward compatible)
print(f"Server: {settings.host}:{settings.port}")
print(f"Model: {settings.model_name}")
print(f"Kafka: {settings.kafka_bootstrap_servers}")
print(f"Redis: {settings.redis_enabled}")
```

**Benefits:**
- ✅ No code changes needed
- ✅ Existing imports work
- ✅ Seamless transition

---

### Pattern 3: Domain-Specific Dependency Injection

```python
from fastapi import Depends
from app.core.config import get_settings, Settings, KafkaConfig

def get_kafka_config(settings: Settings = Depends(get_settings)) -> KafkaConfig:
    """Get Kafka configuration."""
    return settings.kafka

@app.post("/kafka/ingest")
async def ingest_kafka(kafka_config = Depends(get_kafka_config)):
    if not kafka_config.kafka_enabled:
        raise HTTPException(status_code=503, detail="Kafka not enabled")
    # Use kafka_config...
```

**Benefits:**
- ✅ Clear what configuration the endpoint needs
- ✅ Easier to mock in tests (just mock KafkaConfig)
- ✅ Better separation of concerns

---

### Pattern 4: Testing with Mocks

```python
from unittest.mock import Mock
from app.core.config import Settings, ModelConfig

def test_prediction_service():
    # Mock only the domain you need
    mock_model_config = Mock(spec=ModelConfig)
    mock_model_config.model_name = "test-model"
    mock_model_config.max_text_length = 512

    settings = Settings()
    settings.model = mock_model_config

    # Test with mocked config
    service = PredictionService(settings=settings)
    assert service.settings.model.model_name == "test-model"
```

**Benefits:**
- ✅ Only mock what you test
- ✅ Clearer test intent
- ✅ Less boilerplate

---

## Testing Strategy

### Unit Testing Individual Domains

```python
from app.core.config.model import ModelConfig

def test_model_config():
    config = ModelConfig(
        model_name="test-model",
        max_text_length=256,
        prediction_cache_max_size=500
    )
    assert config.model_name == "test-model"
    assert config.max_text_length == 256
```

### Testing with Environment Variables

```python
import os
from app.core.config import Settings

def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("MLOPS_MODEL_NAME", "custom-model")
    monkeypatch.setenv("MLOPS_PORT", "9000")

    settings = Settings()
    assert settings.model.model_name == "custom-model"
    assert settings.server.port == 9000
```

### Testing with Mocks

```python
from unittest.mock import Mock, patch
from app.core.config import Settings, ModelConfig

def test_with_mock():
    mock_model = Mock(spec=ModelConfig)
    mock_model.model_name = "mock-model"

    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value.model = mock_model
        # Test code here
```

---

## Best Practices

### DO ✅

1. **Access domain configs for new code:**
   ```python
   model_name = settings.model.model_name  # Clear and explicit
   ```

2. **Use dependency injection:**
   ```python
   def get_config(settings: Settings = Depends(get_settings)):
       return settings.kafka
   ```

3. **Mock only what you need:**
   ```python
   mock_config = Mock(spec=KafkaConfig)
   ```

4. **Use environment variables for deployment:**
   ```bash
   export MLOPS_KAFKA_ENABLED=true
   ```

5. **Validate sensitive settings:**
   ```python
   if not settings.security.api_key:
       raise ValueError("API key required in production")
   ```

### DON'T ❌

1. **Don't instantiate Settings directly in most cases:**
   ```python
   settings = Settings()  # ❌ Use get_settings() instead
   ```

2. **Don't modify settings at runtime:**
   ```python
   settings.model.model_name = "new-model"  # ❌ Settings should be immutable
   ```

3. **Don't bypass validators:**
   ```python
   # ❌ Don't try to skip validation
   ```

4. **Don't hardcode values that should be configurable:**
   ```python
   max_length = 512  # ❌ Use settings.model.max_text_length
   ```

---

## Architecture Benefits Summary

### 1. Single Responsibility Principle
Each configuration module has one clear purpose:
- `server.py` → Server settings only
- `kafka.py` → Kafka settings only
- etc.

### 2. Easier Testing
Mock only the domain you're testing:
```python
mock_kafka = Mock(spec=KafkaConfig)
# Don't need to mock entire Settings object
```

### 3. Better IDE Support
Domain separation provides better autocomplete:
```python
settings.kafka.  # IDE shows only Kafka settings
settings.model.  # IDE shows only model settings
```

### 4. Clearer Dependencies
It's obvious which settings a component needs:
```python
def kafka_consumer(kafka_config: KafkaConfig):
    # Clearly depends only on Kafka config
```

### 5. Type Safety
Each domain has explicit types:
```python
kafka_port: int = Field(ge=1, le=65535)  # Type + validation
```

### 6. Maintainability
Finding settings is faster:
- 917 lines → Ctrl+F struggle
- 10 focused files → Open relevant module

### 7. Extensibility
Adding new settings is isolated:
- Add to appropriate domain config
- No impact on other domains
- Clear where new settings belong

---

## Migration Path

**For existing code:** No changes needed! All old property names still work.

**For new code:** Use domain-specific access for clarity:

```python
# Before (still works)
model_name = settings.model_name

# After (recommended for new code)
model_name = settings.model.model_name
```

See **[Migration Guide](MIGRATION.md)** for detailed upgrade instructions.

---

## Related Documentation

- **[Profiles](PROFILES.md)** - Profile-based configuration defaults
- **[Environment Variables](ENVIRONMENT_VARIABLES.md)** - Complete settings reference
- **[Deployment](DEPLOYMENT.md)** - Environment-specific configurations
- **[Migration Guide](MIGRATION.md)** - Upgrade from old system
- **[CLAUDE.md](/CLAUDE.md)** - Project-level configuration instructions
- **ADR-009** - Architecture decision for profile-based configuration

---

**Last Updated:** 2025-11-25
**Maintained By:** KubeSentiment Team
