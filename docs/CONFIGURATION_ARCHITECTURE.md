# Configuration Architecture Documentation

## Overview

The KubeSentiment configuration system has been refactored from a monolithic 917-line Settings class into a modular, domain-driven architecture. This document describes the new structure, benefits, and usage patterns.

## Architecture

### Before: Monolithic Configuration
```
app/core/config.py (917 lines)
└── Settings class (90+ fields)
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
- ❌ Difficult to test (must mock entire Settings)
- ❌ High cognitive load (917 lines)
- ❌ Violates Single Responsibility Principle
- ❌ Hard to maintain and extend

### After: Domain-Driven Configuration
```
app/core/config/
├── __init__.py              (33 lines)   - Package exports
├── settings.py              (412 lines)  - Root Settings (composition)
├── server.py                (62 lines)   - Server & app config
├── model.py                 (118 lines)  - ML model config
├── security.py              (99 lines)   - Auth & CORS
├── performance.py           (116 lines)  - Async & performance
├── kafka.py                 (191 lines)  - Kafka streaming
├── redis.py                 (94 lines)   - Redis caching
├── vault.py                 (57 lines)   - Secrets management
├── data_lake.py             (132 lines)  - Cloud storage
├── monitoring.py            (116 lines)  - Metrics & tracing
└── mlops.py                 (99 lines)   - Model lifecycle
```

**Benefits:**
- ✅ Single Responsibility (one domain per config)
- ✅ Easier testing (mock only needed domains)
- ✅ Better documentation (focused docstrings)
- ✅ Maintainability (find settings faster)
- ✅ Type safety (explicit types per domain)
- ✅ 100% backward compatible

---

## Configuration Modules

### 1. ServerConfig (`server.py`)
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
from app.core.config import ServerConfig

server = ServerConfig()
print(f"{server.app_name} v{server.app_version}")
print(f"Running on {server.host}:{server.port}")
```

**Environment Variables:**
```bash
export MLOPS_APP_NAME="My ML Service"
export MLOPS_APP_VERSION="2.0.0"
export MLOPS_DEBUG=true
export MLOPS_HOST="0.0.0.0"
export MLOPS_PORT=8080
export MLOPS_WORKERS=4
```

---

### 2. ModelConfig (`model.py`)
**Purpose:** Machine learning model configuration

**Settings:**
- `model_name` - HuggingFace model identifier
- `allowed_models` - Whitelist of permitted models (security)
- `model_cache_dir` - Model cache directory path
- `onnx_model_path` - ONNX model directory (optional)
- `onnx_model_path_default` - Default ONNX path fallback
- `max_text_length` - Maximum input length (1-10000)
- `prediction_cache_max_size` - LRU cache size (10-100000)
- `enable_feature_engineering` - Advanced features flag

**Validators:**
- Model name format validation (alphanumeric, /, -, _)
- Model name in allowed list check
- Cache directory absolute path validation

**Example:**
```python
from app.core.config import ModelConfig

model = ModelConfig()
print(f"Model: {model.model_name}")
print(f"Allowed: {model.allowed_models}")
print(f"Cache size: {model.prediction_cache_max_size}")
```

---

### 3. SecurityConfig (`security.py`)
**Purpose:** Authentication and CORS configuration

**Settings:**
- `api_key` - API key for authentication (min 8 chars, alphanumeric)
- `allowed_origins` - CORS whitelist (no wildcards)
- `max_request_timeout` - Request timeout in seconds (1-300)

**Validators:**
- API key strength (min 8 chars, letters + numbers)
- CORS URL format validation (https?://...)
- Wildcard origin blocked for security

**Properties:**
- `cors_origins` - Alias for allowed_origins

**Example:**
```python
from app.core.config import SecurityConfig

security = SecurityConfig()
if security.api_key:
    print("API key authentication enabled")
print(f"CORS origins: {security.cors_origins}")
```

---

### 4. PerformanceConfig (`performance.py`)
**Purpose:** Async processing and performance tuning

**Async Batch Settings:**
- `async_batch_enabled` - Enable async batch processing
- `async_batch_max_jobs` - Max concurrent jobs (10-10000)
- `async_batch_max_batch_size` - Max batch size (10-10000)
- `async_batch_default_timeout_seconds` - Job timeout (30-3600)
- `async_batch_priority_high_limit` - High priority queue limit
- `async_batch_priority_medium_limit` - Medium priority queue limit
- `async_batch_priority_low_limit` - Low priority queue limit
- `async_batch_cleanup_interval_seconds` - Cleanup interval (10-3600)
- `async_batch_cache_ttl_seconds` - Result cache TTL (300-86400)
- `async_batch_result_cache_max_size` - Result cache size (100-10000)

**Anomaly Buffer Settings:**
- `anomaly_buffer_enabled` - Enable anomaly detection buffer
- `anomaly_buffer_max_size` - Max anomalies to store (100-100000)
- `anomaly_buffer_default_ttl` - TTL for anomalies (300-86400)
- `anomaly_buffer_cleanup_interval` - Cleanup interval (60-3600)

---

### 5. KafkaConfig (`kafka.py`)
**Purpose:** Kafka streaming and messaging (30+ settings)

**Basic Settings:**
- `kafka_enabled` - Enable Kafka streaming
- `kafka_bootstrap_servers` - Kafka broker list
- `kafka_consumer_group` - Consumer group ID
- `kafka_topic` - Topic to consume from

**Consumer Settings:**
- `kafka_auto_offset_reset` - earliest/latest/none
- `kafka_max_poll_records` - Records per poll (1-10000)
- `kafka_session_timeout_ms` - Session timeout (1000-300000)
- `kafka_heartbeat_interval_ms` - Heartbeat interval (1000-30000)
- `kafka_max_poll_interval_ms` - Max poll interval (10000-2147483647)
- `kafka_enable_auto_commit` - Auto commit flag
- `kafka_auto_commit_interval_ms` - Auto commit interval (1000-60000)

**High-Throughput Settings:**
- `kafka_consumer_threads` - Parallel consumer threads (1-32)
- `kafka_batch_size` - Batch processing size (1-1000)
- `kafka_processing_timeout_ms` - Batch timeout (1000-300000)
- `kafka_buffer_size` - Message queue buffer (1000-100000)

**Dead Letter Queue:**
- `kafka_dlq_topic` - DLQ topic name
- `kafka_dlq_enabled` - Enable DLQ
- `kafka_max_retries` - Max retries before DLQ (1-10)

**Producer Settings:**
- `kafka_producer_bootstrap_servers` - Producer brokers
- `kafka_producer_acks` - Acknowledgment level (0/1/all)
- `kafka_producer_retries` - Producer retry count (0-10)
- `kafka_producer_batch_size` - Batch size in bytes (0-1048576)
- `kafka_producer_linger_ms` - Linger time (0-100)
- `kafka_producer_compression_type` - none/gzip/snappy/lz4/zstd

**Advanced:**
- `kafka_partition_assignment_strategy` - range/roundrobin/sticky

---

### 6. RedisConfig (`redis.py`)
**Purpose:** Redis distributed caching

**Settings:**
- `redis_enabled` - Enable Redis
- `redis_host` - Redis server host
- `redis_port` - Redis server port (1-65535)
- `redis_db` - Database number (0-15)
- `redis_password` - Authentication password (excluded from API)
- `redis_max_connections` - Connection pool size (10-1000)
- `redis_socket_timeout` - Socket timeout (1-60)
- `redis_socket_connect_timeout` - Connection timeout (1-60)
- `redis_namespace` - Key prefix namespace
- `redis_prediction_cache_ttl` - Prediction cache TTL (60-86400)
- `redis_feature_cache_ttl` - Feature cache TTL (60-86400)

---

### 7. VaultConfig (`vault.py`)
**Purpose:** HashiCorp Vault secrets management

**Settings:**
- `vault_enabled` - Enable Vault integration
- `vault_addr` - Vault server address (e.g., http://vault:8200)
- `vault_namespace` - Vault namespace (Enterprise)
- `vault_role` - Kubernetes service account role
- `vault_mount_point` - KV v2 secrets engine mount
- `vault_secrets_path` - Base secrets path
- `vault_token` - Direct auth token (excluded from API, not for prod)

---

### 8. DataLakeConfig (`data_lake.py`)
**Purpose:** Cloud storage integration (AWS/GCP/Azure)

**Core Settings:**
- `data_lake_enabled` - Enable data lake
- `data_lake_provider` - s3/gcs/azure
- `data_lake_bucket` - Bucket/container name
- `data_lake_prefix` - Path prefix
- `data_lake_batch_size` - Predictions per batch (1-1000)
- `data_lake_batch_timeout_seconds` - Flush timeout (5-300)
- `data_lake_compression` - snappy/gzip/lz4/zstd/none
- `data_lake_partition_by` - date/hour/model

**AWS S3:**
- `data_lake_s3_region` - AWS region
- `data_lake_s3_endpoint_url` - Custom S3 endpoint (S3-compatible)

**GCP:**
- `data_lake_gcs_project` - GCP project ID
- `data_lake_gcs_credentials_path` - Service account JSON path

**Azure:**
- `data_lake_azure_account_name` - Storage account name
- `data_lake_azure_account_key` - Account key (excluded from API)
- `data_lake_azure_connection_string` - Connection string (excluded)

**Query Engines:**
- `data_lake_enable_athena` - AWS Athena compatibility
- `data_lake_enable_bigquery` - BigQuery compatibility
- `data_lake_enable_synapse` - Azure Synapse compatibility

---

### 9. MonitoringConfig (`monitoring.py`)
**Purpose:** Metrics, logging, and distributed tracing

**Metrics:**
- `enable_metrics` - Enable Prometheus metrics
- `log_level` - DEBUG/INFO/WARNING/ERROR/CRITICAL
- `metrics_cache_ttl` - Metrics cache TTL (1-300)

**Advanced Metrics:**
- `advanced_metrics_enabled` - Enable advanced KPIs
- `advanced_metrics_detailed_tracking` - Per-prediction tracking
- `advanced_metrics_history_hours` - History retention (1-168)
- `advanced_metrics_cost_per_1k` - Cost per 1k predictions

**Distributed Tracing:**
- `enable_tracing` - Enable tracing
- `tracing_backend` - jaeger/zipkin/otlp/console
- `service_name` - Service name for traces

**Jaeger:**
- `jaeger_agent_host` - Agent hostname
- `jaeger_agent_port` - Agent port (1024-65535)

**Zipkin:**
- `zipkin_endpoint` - Collector endpoint

**OTLP:**
- `otlp_endpoint` - gRPC endpoint

**Exclusions:**
- `tracing_excluded_urls` - Comma-separated URL list

---

### 10. MLOpsConfig (`mlops.py`)
**Purpose:** Model lifecycle management

**MLflow:**
- `mlflow_enabled` - Enable MLflow registry
- `mlflow_tracking_uri` - Tracking server URI
- `mlflow_registry_uri` - Registry URI (defaults to tracking)
- `mlflow_experiment_name` - Experiment name
- `mlflow_model_name` - Registered model name

**Drift Detection:**
- `drift_detection_enabled` - Enable drift detection
- `drift_window_size` - Sample window size (100-10000)
- `drift_psi_threshold` - PSI threshold (0.0-1.0, 0.1=minor, 0.25=major)
- `drift_ks_threshold` - KS test p-value (0.0-1.0)
- `drift_min_samples` - Min samples before check (10-1000)

**Explainability:**
- `explainability_enabled` - Enable explainability
- `explainability_use_attention` - Use attention weights
- `explainability_use_gradients` - Use gradients (slower)

---

## Root Settings Class

### Composition Architecture

The root `Settings` class in `settings.py` composes all domain configurations:

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
```

### Backward Compatibility

The Settings class provides **50+ @property methods** for backward compatibility:

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

### Pattern 1: Accessing Domain Configs (Recommended for New Code)

```python
from app.core.config import Settings, get_settings

settings = get_settings()

# Access through domain objects
print(f"Server: {settings.server.host}:{settings.server.port}")
print(f"Model: {settings.model.model_name}")
print(f"Kafka: {settings.kafka.kafka_bootstrap_servers}")
print(f"Redis: {settings.redis.redis_enabled}")
```

**Benefits:**
- ✅ Clear domain separation
- ✅ IDE autocomplete works better
- ✅ Easy to mock specific domains in tests

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

### Pattern 3: Domain-Specific Dependency Injection

```python
from fastapi import Depends
from app.core.config import get_settings, Settings

def get_kafka_config(settings: Settings = Depends(get_settings)):
    """Get Kafka configuration."""
    return settings.kafka

@app.post("/kafka/ingest")
async def ingest_kafka(kafka_config = Depends(get_kafka_config)):
    if not kafka_config.kafka_enabled:
        raise HTTPException(status_code=503, detail="Kafka not enabled")
    # Use kafka_config...
```

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

---

## Migration Guide

### For Existing Code

**Good news:** No changes required! All existing code continues to work.

```python
# This still works
from app.core.config import Settings, get_settings

settings = get_settings()
model_name = settings.model_name  # ✅ Works via @property
```

### For New Code

**Recommended:** Use domain-specific access for clarity:

```python
# New style (recommended)
from app.core.config import get_settings

settings = get_settings()
model_name = settings.model.model_name  # ✅ Clear domain separation
```

### Updating Imports

No import changes needed, but you can be more specific:

```python
# Before (still works)
from app.core.config import Settings, get_settings

# After (optional, more specific)
from app.core.config import Settings, get_settings, ModelConfig, KafkaConfig
```

---

## Environment Variables

All configuration values can be set via environment variables with the `MLOPS_` prefix:

```bash
# Server
export MLOPS_APP_NAME="My Service"
export MLOPS_PORT=8080
export MLOPS_WORKERS=4

# Model
export MLOPS_MODEL_NAME="distilbert-base-uncased-finetuned-sst-2-english"
export MLOPS_MAX_TEXT_LENGTH=512

# Kafka
export MLOPS_KAFKA_ENABLED=true
export MLOPS_KAFKA_BOOTSTRAP_SERVERS="kafka1:9092,kafka2:9092"
export MLOPS_KAFKA_TOPIC="sentiment_requests"

# Redis
export MLOPS_REDIS_ENABLED=true
export MLOPS_REDIS_HOST="redis"
export MLOPS_REDIS_PORT=6379

# Monitoring
export MLOPS_LOG_LEVEL="INFO"
export MLOPS_ENABLE_TRACING=true
export MLOPS_TRACING_BACKEND="jaeger"
```

### .env File Support

Create a `.env` file in the project root:

```ini
# .env
MLOPS_APP_NAME=KubeSentiment
MLOPS_APP_VERSION=1.0.0
MLOPS_DEBUG=false
MLOPS_PORT=8000
MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
MLOPS_KAFKA_ENABLED=true
MLOPS_REDIS_ENABLED=true
```

The configuration system automatically loads from `.env` files.

---

## Testing

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

### Mocking for Tests

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

## Architecture Benefits

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

## File Structure Reference

```
app/core/config/
├── __init__.py           # Package exports
├── settings.py           # Root Settings (composition + compatibility)
├── server.py             # ServerConfig
├── model.py              # ModelConfig
├── security.py           # SecurityConfig
├── performance.py        # PerformanceConfig
├── kafka.py              # KafkaConfig
├── redis.py              # RedisConfig
├── vault.py              # VaultConfig
├── data_lake.py          # DataLakeConfig
├── monitoring.py         # MonitoringConfig
└── mlops.py              # MLOpsConfig
```

**Backup Files:**
- `app/core/config_original.py.bak` - Original monolithic config
- `app/core/config_replaced.py.bak` - Replaced monolithic config

---

## Version History

### v1.0.0 (Original)
- Monolithic Settings class (917 lines)
- 90+ configuration fields in one class
- God Object anti-pattern

### v2.0.0 (Refactored - Current)
- Domain-driven configuration (12 modules)
- Composition-based Settings class
- 100% backward compatible
- Single Responsibility Principle
- Better testability and maintainability

---

## Support & Questions

For questions about the configuration system:
1. Check this documentation
2. Review the docstrings in each config module
3. See migration examples above
4. Contact the development team

## Related Documentation

- [Model Implementation Guide](../models/README.md)
- [Deployment Configuration Guide](../../docs/ENVIRONMENT_CONFIGURATIONS.md)
- [API Documentation](../../docs/API_VERSIONING.md)
- [Contributing Guide](../../CONTRIBUTING.md)
