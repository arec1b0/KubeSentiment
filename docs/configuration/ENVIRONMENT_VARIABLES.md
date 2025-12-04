# Environment Variables Reference

Complete reference of all KubeSentiment configuration settings.

**Quick Links:** [Server](#server) | [Model](#model) | [Security](#security) | [Performance](#performance) | [Kafka](#kafka) | [Redis](#redis) | [Vault](#vault) | [Data Lake](#data-lake) | [Monitoring](#monitoring) | [MLOps](#mlops)

All variables use the `MLOPS_` prefix and can be set via environment variables, `.env` files, or Kubernetes ConfigMaps.

---

## Server Configuration

Server and application settings.

| Variable            | Type | Default                | Min/Max                | Profile Defaults                       | Description                                    |
| ------------------- | ---- | ---------------------- | ---------------------- | -------------------------------------- | ---------------------------------------------- |
| `MLOPS_APP_NAME`    | str  | "ML Model Serving API" | -                      | local/dev/staging/prod                 | Application name displayed in UI/logs          |
| `MLOPS_APP_VERSION` | str  | "1.0.0"                | -                      | -                                      | Semantic version (e.g., "1.2.3")               |
| `MLOPS_DEBUG`       | bool | false                  | -                      | local/dev: true<br>staging/prod: false | Enable debug mode (verbose output, hot-reload) |
| `MLOPS_ENVIRONMENT` | str  | "development"          | local/dev/staging/prod | Set by profile                         | Environment name (use `MLOPS_PROFILE` instead) |
| `MLOPS_HOST`        | str  | "0.0.0.0"              | -                      | local: 127.0.0.1<br>others: 0.0.0.0    | Server bind address                            |
| `MLOPS_PORT`        | int  | 8000                   | 1024-65535             | -                                      | Server port                                    |
| `MLOPS_WORKERS`     | int  | 1                      | 1-16                   | local/dev: 1<br>staging: 2<br>prod: 4  | Number of worker processes                     |
| `MLOPS_PROFILE`     | str  | "development"          | local/dev/staging/prod | -                                      | Configuration profile (sets many defaults)     |

**Examples:**

```bash
export MLOPS_PROFILE=production    # Sets 50+ defaults
export MLOPS_HOST=0.0.0.0
export MLOPS_PORT=8000
export MLOPS_WORKERS=4
```

---

## Model Configuration

Machine learning model settings.

| Variable                           | Type | Default                                           | Min/Max           | Description                                                |
| ---------------------------------- | ---- | ------------------------------------------------- | ----------------- | ---------------------------------------------------------- |
| `MLOPS_MODEL_NAME`                 | str  | "distilbert-base-uncased-finetuned-sst-2-english" | -                 | HuggingFace model identifier                               |
| `MLOPS_ALLOWED_MODELS`             | str  | comma-separated                                   | -                 | Whitelist of allowed models (security)                     |
| `MLOPS_MODEL_CACHE_DIR`            | str  | "./models"                                        | -                 | Directory to cache downloaded models                       |
| `MLOPS_ONNX_MODEL_PATH`            | str  | optional                                          | -                 | Path to ONNX model directory                               |
| `MLOPS_ONNX_MODEL_PATH_DEFAULT`    | str  | "./models/onnx"                                   | -                 | Default ONNX path fallback                                 |
| `MLOPS_MAX_TEXT_LENGTH`            | int  | 512                                               | 1-10000           | Maximum input text length (characters)                     |
| `MLOPS_PREDICTION_CACHE_MAX_SIZE`  | int  | 1000                                              | 10-100000         | LRU cache size for predictions                             |
| `MLOPS_PREDICTION_CACHE_ENABLED`   | bool | true                                              | -                 | Enable LRU cache for predictions (disable if hit rate <5%) |
| `MLOPS_ENABLE_FEATURE_ENGINEERING` | bool | false                                             | -                 | Enable advanced feature engineering                        |
| `MLOPS_MODEL_BACKEND`              | str  | "onnx"                                            | onnx/pytorch/mock | Model inference backend                                    |

**Validation Rules:**

- Model name must match: `[a-zA-Z0-9/_\-]+`
- Model must be in `MLOPS_ALLOWED_MODELS` list
- Cache directory must be absolute path

**Examples:**

```bash
export MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
export MLOPS_MAX_TEXT_LENGTH=512
export MLOPS_PREDICTION_CACHE_MAX_SIZE=1000
export MLOPS_PREDICTION_CACHE_ENABLED=true  # Set to false if cache hit rate <5%
export MLOPS_MODEL_BACKEND=onnx
```

---

## Security Configuration

Authentication and CORS settings.

| Variable                    | Type | Default | Min/Max  | Description                                          |
| --------------------------- | ---- | ------- | -------- | ---------------------------------------------------- |
| `MLOPS_API_KEY`             | str  | ""      | 8+ chars | API key for authentication (min 8 characters)        |
| `MLOPS_ALLOWED_ORIGINS`     | str  | "\*"    | -        | CORS allowed origins (comma-separated, no wildcards) |
| `MLOPS_MAX_REQUEST_TIMEOUT` | int  | 300     | 1-300    | Request timeout in seconds                           |

**Validation Rules:**

- API key: minimum 8 characters if provided
- CORS origins: must be valid URLs (https://... or http://...)
- Wildcard origins blocked for security in production

**Environment-Specific Defaults:**

- **Development:** MLOPS_API_KEY="" (disabled)
- **Production:** MLOPS_API_KEY required

**Examples:**

```bash
export MLOPS_API_KEY=my-secure-api-key-12345
export MLOPS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
export MLOPS_MAX_REQUEST_TIMEOUT=300
```

---

## Performance Configuration

Async processing and performance tuning.

### Async Batch Settings

| Variable                                     | Type | Default | Min/Max   | Description                   |
| -------------------------------------------- | ---- | ------- | --------- | ----------------------------- |
| `MLOPS_ASYNC_BATCH_ENABLED`                  | bool | false   | -         | Enable async batch processing |
| `MLOPS_ASYNC_BATCH_MAX_JOBS`                 | int  | 1000    | 10-10000  | Maximum concurrent jobs       |
| `MLOPS_ASYNC_BATCH_MAX_BATCH_SIZE`           | int  | 100     | 10-10000  | Maximum batch size            |
| `MLOPS_ASYNC_BATCH_DEFAULT_TIMEOUT_SECONDS`  | int  | 300     | 30-3600   | Job timeout (seconds)         |
| `MLOPS_ASYNC_BATCH_PRIORITY_HIGH_LIMIT`      | int  | 200     | -         | High priority queue size      |
| `MLOPS_ASYNC_BATCH_PRIORITY_MEDIUM_LIMIT`    | int  | 300     | -         | Medium priority queue size    |
| `MLOPS_ASYNC_BATCH_PRIORITY_LOW_LIMIT`       | int  | 500     | -         | Low priority queue size       |
| `MLOPS_ASYNC_BATCH_CLEANUP_INTERVAL_SECONDS` | int  | 300     | 10-3600   | Cleanup interval              |
| `MLOPS_ASYNC_BATCH_CACHE_TTL_SECONDS`        | int  | 3600    | 300-86400 | Result cache TTL              |
| `MLOPS_ASYNC_BATCH_RESULT_CACHE_MAX_SIZE`    | int  | 1000    | 100-10000 | Result cache size             |

### Anomaly Buffer Settings

| Variable                                | Type | Default | Min/Max    | Description                     |
| --------------------------------------- | ---- | ------- | ---------- | ------------------------------- |
| `MLOPS_ANOMALY_BUFFER_ENABLED`          | bool | false   | -          | Enable anomaly detection buffer |
| `MLOPS_ANOMALY_BUFFER_MAX_SIZE`         | int  | 1000    | 100-100000 | Max anomalies to store          |
| `MLOPS_ANOMALY_BUFFER_DEFAULT_TTL`      | int  | 3600    | 300-86400  | TTL for anomalies               |
| `MLOPS_ANOMALY_BUFFER_CLEANUP_INTERVAL` | int  | 300     | 60-3600    | Cleanup interval                |

**Examples:**

```bash
export MLOPS_ASYNC_BATCH_ENABLED=true
export MLOPS_ASYNC_BATCH_MAX_JOBS=1000
export MLOPS_ASYNC_BATCH_MAX_BATCH_SIZE=100
export MLOPS_ASYNC_BATCH_DEFAULT_TIMEOUT_SECONDS=300
```

---

## Kafka Configuration

Message streaming and async processing (30+ settings).

### Basic Settings

| Variable                        | Type | Default              | Min/Max | Description                     |
| ------------------------------- | ---- | -------------------- | ------- | ------------------------------- |
| `MLOPS_KAFKA_ENABLED`           | bool | false                | -       | Enable Kafka streaming          |
| `MLOPS_KAFKA_BOOTSTRAP_SERVERS` | str  | "localhost:9092"     | -       | Kafka brokers (comma-separated) |
| `MLOPS_KAFKA_CONSUMER_GROUP`    | str  | "mlops-sentiment"    | -       | Consumer group ID               |
| `MLOPS_KAFKA_TOPIC`             | str  | "sentiment-requests" | -       | Topic to consume from           |

### Consumer Settings

| Variable                              | Type | Default    | Min/Max              | Description               |
| ------------------------------------- | ---- | ---------- | -------------------- | ------------------------- |
| `MLOPS_KAFKA_AUTO_OFFSET_RESET`       | str  | "earliest" | earliest/latest/none | Offset reset strategy     |
| `MLOPS_KAFKA_MAX_POLL_RECORDS`        | int  | 500        | 1-10000              | Records per poll          |
| `MLOPS_KAFKA_SESSION_TIMEOUT_MS`      | int  | 30000      | 1000-300000          | Session timeout (ms)      |
| `MLOPS_KAFKA_HEARTBEAT_INTERVAL_MS`   | int  | 10000      | 1000-30000           | Heartbeat interval (ms)   |
| `MLOPS_KAFKA_MAX_POLL_INTERVAL_MS`    | int  | 300000     | 10000-2147483647     | Max poll interval (ms)    |
| `MLOPS_KAFKA_ENABLE_AUTO_COMMIT`      | bool | true       | -                    | Auto commit flag          |
| `MLOPS_KAFKA_AUTO_COMMIT_INTERVAL_MS` | int  | 5000       | 1000-60000           | Auto commit interval (ms) |

### High-Throughput Settings

| Variable                            | Type | Default | Min/Max     | Description               |
| ----------------------------------- | ---- | ------- | ----------- | ------------------------- |
| `MLOPS_KAFKA_CONSUMER_THREADS`      | int  | 1       | 1-32        | Parallel consumer threads |
| `MLOPS_KAFKA_BATCH_SIZE`            | int  | 10      | 1-1000      | Batch processing size     |
| `MLOPS_KAFKA_PROCESSING_TIMEOUT_MS` | int  | 5000    | 1000-300000 | Batch timeout (ms)        |
| `MLOPS_KAFKA_BUFFER_SIZE`           | int  | 10000   | 1000-100000 | Message queue buffer      |

### Dead Letter Queue

| Variable                  | Type | Default         | Min/Max | Description             |
| ------------------------- | ---- | --------------- | ------- | ----------------------- |
| `MLOPS_KAFKA_DLQ_TOPIC`   | str  | "sentiment-dlq" | -       | Dead letter queue topic |
| `MLOPS_KAFKA_DLQ_ENABLED` | bool | false           | -       | Enable DLQ              |
| `MLOPS_KAFKA_MAX_RETRIES` | int  | 3               | 1-10    | Max retries before DLQ  |

### Producer Settings

| Variable                                 | Type | Default  | Min/Max                   | Description                     |
| ---------------------------------------- | ---- | -------- | ------------------------- | ------------------------------- |
| `MLOPS_KAFKA_PRODUCER_BOOTSTRAP_SERVERS` | str  | ""       | -                         | Producer brokers (if different) |
| `MLOPS_KAFKA_PRODUCER_ACKS`              | str  | "all"    | 0/1/all                   | Acknowledgment level            |
| `MLOPS_KAFKA_PRODUCER_RETRIES`           | int  | 3        | 0-10                      | Producer retry count            |
| `MLOPS_KAFKA_PRODUCER_BATCH_SIZE`        | int  | 16384    | 0-1048576                 | Batch size (bytes)              |
| `MLOPS_KAFKA_PRODUCER_LINGER_MS`         | int  | 10       | 0-100                     | Linger time (ms)                |
| `MLOPS_KAFKA_PRODUCER_COMPRESSION_TYPE`  | str  | "snappy" | none/gzip/snappy/lz4/zstd | Compression                     |

### Advanced

| Variable                                    | Type | Default | Min/Max                 | Description         |
| ------------------------------------------- | ---- | ------- | ----------------------- | ------------------- |
| `MLOPS_KAFKA_PARTITION_ASSIGNMENT_STRATEGY` | str  | "range" | range/roundrobin/sticky | Assignment strategy |

**Examples:**

```bash
export MLOPS_KAFKA_ENABLED=true
export MLOPS_KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092
export MLOPS_KAFKA_CONSUMER_GROUP=my-group
export MLOPS_KAFKA_TOPIC=sentiment-requests
export MLOPS_KAFKA_CONSUMER_THREADS=8
```

---

## Redis Configuration

Distributed caching.

| Variable                             | Type | Default     | Min/Max  | Description                    |
| ------------------------------------ | ---- | ----------- | -------- | ------------------------------ |
| `MLOPS_REDIS_ENABLED`                | bool | false       | -        | Enable Redis caching           |
| `MLOPS_REDIS_HOST`                   | str  | "localhost" | -        | Redis server host              |
| `MLOPS_REDIS_PORT`                   | int  | 6379        | 1-65535  | Redis server port              |
| `MLOPS_REDIS_DB`                     | int  | 0           | 0-15     | Database number                |
| `MLOPS_REDIS_PASSWORD`               | str  | ""          | -        | Authentication password        |
| `MLOPS_REDIS_MAX_CONNECTIONS`        | int  | 50          | 10-1000  | Connection pool size           |
| `MLOPS_REDIS_SOCKET_TIMEOUT`         | int  | 5           | 1-60     | Socket timeout (seconds)       |
| `MLOPS_REDIS_SOCKET_CONNECT_TIMEOUT` | int  | 5           | 1-60     | Connection timeout (seconds)   |
| `MLOPS_REDIS_NAMESPACE`              | str  | "mlops"     | -        | Key prefix namespace           |
| `MLOPS_REDIS_PREDICTION_CACHE_TTL`   | int  | 3600        | 60-86400 | Prediction cache TTL (seconds) |
| `MLOPS_REDIS_FEATURE_CACHE_TTL`      | int  | 1800        | 60-86400 | Feature cache TTL (seconds)    |

**Profile Defaults:**

- **Local/Dev:** Disabled
- **Staging/Prod:** Enabled

**Examples:**

```bash
export MLOPS_REDIS_ENABLED=true
export MLOPS_REDIS_HOST=redis.example.com
export MLOPS_REDIS_PORT=6379
export MLOPS_REDIS_PASSWORD=my-password
export MLOPS_REDIS_MAX_CONNECTIONS=100
```

---

## Vault Configuration

HashiCorp Vault secrets management.

| Variable                   | Type | Default             | Min/Max | Description                            |
| -------------------------- | ---- | ------------------- | ------- | -------------------------------------- |
| `MLOPS_VAULT_ENABLED`      | bool | false               | -       | Enable Vault integration               |
| `MLOPS_VAULT_ADDR`         | str  | "http://vault:8200" | -       | Vault server address                   |
| `MLOPS_VAULT_NAMESPACE`    | str  | ""                  | -       | Vault namespace (Enterprise)           |
| `MLOPS_VAULT_ROLE`         | str  | "mlops-sentiment"   | -       | Kubernetes service account role        |
| `MLOPS_VAULT_MOUNT_POINT`  | str  | "secret"            | -       | KV v2 secrets engine mount             |
| `MLOPS_VAULT_SECRETS_PATH` | str  | "mlops-sentiment"   | -       | Base secrets path                      |
| `MLOPS_VAULT_TOKEN`        | str  | ""                  | -       | Direct auth token (not for production) |

**Profile Defaults:**

- **Local/Dev:** Disabled
- **Staging/Prod:** Enabled

**Examples:**

```bash
export MLOPS_VAULT_ENABLED=true
export MLOPS_VAULT_ADDR=https://vault.example.com
export MLOPS_VAULT_ROLE=mlops-sentiment-prod
```

---

## Data Lake Configuration

Cloud storage integration (AWS/GCP/Azure).

### Core Settings

| Variable                                | Type | Default       | Min/Max                   | Description           |
| --------------------------------------- | ---- | ------------- | ------------------------- | --------------------- |
| `MLOPS_DATA_LAKE_ENABLED`               | bool | false         | -                         | Enable data lake      |
| `MLOPS_DATA_LAKE_PROVIDER`              | str  | "s3"          | s3/gcs/azure              | Cloud provider        |
| `MLOPS_DATA_LAKE_BUCKET`                | str  | ""            | -                         | Bucket/container name |
| `MLOPS_DATA_LAKE_PREFIX`                | str  | "predictions" | -                         | Path prefix           |
| `MLOPS_DATA_LAKE_BATCH_SIZE`            | int  | 100           | 1-1000                    | Predictions per batch |
| `MLOPS_DATA_LAKE_BATCH_TIMEOUT_SECONDS` | int  | 60            | 5-300                     | Flush timeout         |
| `MLOPS_DATA_LAKE_COMPRESSION`           | str  | "snappy"      | snappy/gzip/lz4/zstd/none | Compression format    |
| `MLOPS_DATA_LAKE_PARTITION_BY`          | str  | "date"        | date/hour/model           | Partition strategy    |

### AWS S3

| Variable                          | Type | Default     | Min/Max | Description                        |
| --------------------------------- | ---- | ----------- | ------- | ---------------------------------- |
| `MLOPS_DATA_LAKE_S3_REGION`       | str  | "us-east-1" | -       | AWS region                         |
| `MLOPS_DATA_LAKE_S3_ENDPOINT_URL` | str  | ""          | -       | Custom S3 endpoint (S3-compatible) |

### GCP

| Variable                               | Type | Default | Min/Max | Description               |
| -------------------------------------- | ---- | ------- | ------- | ------------------------- |
| `MLOPS_DATA_LAKE_GCS_PROJECT`          | str  | ""      | -       | GCP project ID            |
| `MLOPS_DATA_LAKE_GCS_CREDENTIALS_PATH` | str  | ""      | -       | Service account JSON path |

### Azure

| Variable                                  | Type | Default | Min/Max | Description          |
| ----------------------------------------- | ---- | ------- | ------- | -------------------- |
| `MLOPS_DATA_LAKE_AZURE_ACCOUNT_NAME`      | str  | ""      | -       | Storage account name |
| `MLOPS_DATA_LAKE_AZURE_ACCOUNT_KEY`       | str  | ""      | -       | Account key          |
| `MLOPS_DATA_LAKE_AZURE_CONNECTION_STRING` | str  | ""      | -       | Connection string    |

### Query Engines

| Variable                          | Type | Default | Min/Max | Description                 |
| --------------------------------- | ---- | ------- | ------- | --------------------------- |
| `MLOPS_DATA_LAKE_ENABLE_ATHENA`   | bool | false   | -       | AWS Athena compatibility    |
| `MLOPS_DATA_LAKE_ENABLE_BIGQUERY` | bool | false   | -       | BigQuery compatibility      |
| `MLOPS_DATA_LAKE_ENABLE_SYNAPSE`  | bool | false   | -       | Azure Synapse compatibility |

**Examples:**

```bash
# AWS S3
export MLOPS_DATA_LAKE_ENABLED=true
export MLOPS_DATA_LAKE_PROVIDER=s3
export MLOPS_DATA_LAKE_BUCKET=my-predictions
export MLOPS_DATA_LAKE_S3_REGION=us-west-2

# GCP
export MLOPS_DATA_LAKE_PROVIDER=gcs
export MLOPS_DATA_LAKE_GCS_PROJECT=my-project
```

---

## Monitoring Configuration

Metrics, logging, and distributed tracing.

### Basic Settings

| Variable                  | Type | Default | Min/Max                           | Description                 |
| ------------------------- | ---- | ------- | --------------------------------- | --------------------------- |
| `MLOPS_ENABLE_METRICS`    | bool | true    | -                                 | Enable Prometheus metrics   |
| `MLOPS_LOG_LEVEL`         | str  | "INFO"  | DEBUG/INFO/WARNING/ERROR/CRITICAL | Log verbosity               |
| `MLOPS_METRICS_CACHE_TTL` | int  | 60      | 1-300                             | Metrics cache TTL (seconds) |

### Advanced Metrics

| Variable                                   | Type  | Default | Min/Max | Description               |
| ------------------------------------------ | ----- | ------- | ------- | ------------------------- |
| `MLOPS_ADVANCED_METRICS_ENABLED`           | bool  | false   | -       | Enable advanced KPIs      |
| `MLOPS_ADVANCED_METRICS_DETAILED_TRACKING` | bool  | false   | -       | Per-prediction tracking   |
| `MLOPS_ADVANCED_METRICS_HISTORY_HOURS`     | int   | 24      | 1-168   | History retention (hours) |
| `MLOPS_ADVANCED_METRICS_COST_PER_1K`       | float | 0.0     | -       | Cost per 1k predictions   |

### Tracing

| Variable                | Type | Default           | Min/Max                    | Description                |
| ----------------------- | ---- | ----------------- | -------------------------- | -------------------------- |
| `MLOPS_ENABLE_TRACING`  | bool | false             | -                          | Enable distributed tracing |
| `MLOPS_TRACING_BACKEND` | str  | "jaeger"          | jaeger/zipkin/otlp/console | Tracing backend            |
| `MLOPS_SERVICE_NAME`    | str  | "mlops-sentiment" | -                          | Service name for traces    |

### Jaeger

| Variable                  | Type | Default     | Min/Max    | Description           |
| ------------------------- | ---- | ----------- | ---------- | --------------------- |
| `MLOPS_JAEGER_AGENT_HOST` | str  | "localhost" | -          | Jaeger agent hostname |
| `MLOPS_JAEGER_AGENT_PORT` | int  | 6831        | 1024-65535 | Jaeger agent port     |

### Zipkin

| Variable                | Type | Default                 | Min/Max | Description               |
| ----------------------- | ---- | ----------------------- | ------- | ------------------------- |
| `MLOPS_ZIPKIN_ENDPOINT` | str  | "http://localhost:9411" | -       | Zipkin collector endpoint |

### OTLP

| Variable              | Type | Default          | Min/Max | Description                 |
| --------------------- | ---- | ---------------- | ------- | --------------------------- |
| `MLOPS_OTLP_ENDPOINT` | str  | "localhost:4317" | -       | OpenTelemetry gRPC endpoint |

### Exclusions

| Variable                      | Type | Default            | Min/Max | Description                          |
| ----------------------------- | ---- | ------------------ | ------- | ------------------------------------ |
| `MLOPS_TRACING_EXCLUDED_URLS` | str  | "/health,/metrics" | -       | Comma-separated URLs to skip tracing |

**Examples:**

```bash
export MLOPS_ENABLE_METRICS=true
export MLOPS_LOG_LEVEL=INFO
export MLOPS_ENABLE_TRACING=true
export MLOPS_TRACING_BACKEND=jaeger
export MLOPS_JAEGER_AGENT_HOST=jaeger.example.com
```

---

## MLOps Configuration

Model lifecycle management.

### MLflow

| Variable                       | Type | Default              | Min/Max | Description                         |
| ------------------------------ | ---- | -------------------- | ------- | ----------------------------------- |
| `MLOPS_MLFLOW_ENABLED`         | bool | false                | -       | Enable MLflow registry              |
| `MLOPS_MLFLOW_TRACKING_URI`    | str  | "http://mlflow:5000" | -       | Tracking server URI                 |
| `MLOPS_MLFLOW_REGISTRY_URI`    | str  | ""                   | -       | Registry URI (defaults to tracking) |
| `MLOPS_MLFLOW_EXPERIMENT_NAME` | str  | "default"            | -       | Experiment name                     |
| `MLOPS_MLFLOW_MODEL_NAME`      | str  | "sentiment"          | -       | Registered model name               |

### Drift Detection

| Variable                        | Type  | Default | Min/Max   | Description                           |
| ------------------------------- | ----- | ------- | --------- | ------------------------------------- |
| `MLOPS_DRIFT_DETECTION_ENABLED` | bool  | false   | -         | Enable drift detection                |
| `MLOPS_DRIFT_WINDOW_SIZE`       | int   | 1000    | 100-10000 | Sample window size                    |
| `MLOPS_DRIFT_PSI_THRESHOLD`     | float | 0.25    | 0.0-1.0   | PSI threshold (0.1=minor, 0.25=major) |
| `MLOPS_DRIFT_KS_THRESHOLD`      | float | 0.05    | 0.0-1.0   | KS test p-value                       |
| `MLOPS_DRIFT_MIN_SAMPLES`       | int   | 100     | 10-1000   | Min samples before check              |

### Explainability

| Variable                             | Type | Default | Min/Max | Description            |
| ------------------------------------ | ---- | ------- | ------- | ---------------------- |
| `MLOPS_EXPLAINABILITY_ENABLED`       | bool | false   | -       | Enable explainability  |
| `MLOPS_EXPLAINABILITY_USE_ATTENTION` | bool | true    | -       | Use attention weights  |
| `MLOPS_EXPLAINABILITY_USE_GRADIENTS` | bool | false   | -       | Use gradients (slower) |

### Shadow Mode (Dark Launch)

Shadow mode enables running a candidate model alongside the production model for risk-free validation on live traffic.

| Variable                          | Type  | Default   | Min/Max      | Description                                   |
| --------------------------------- | ----- | --------- | ------------ | --------------------------------------------- |
| `MLOPS_SHADOW_MODE_ENABLED`       | bool  | false     | -            | Enable shadow mode                            |
| `MLOPS_SHADOW_MODEL_NAME`         | str   | ""        | -            | HuggingFace model identifier for shadow model |
| `MLOPS_SHADOW_MODEL_BACKEND`      | str   | "pytorch" | pytorch/onnx | Backend for shadow model                      |
| `MLOPS_SHADOW_TRAFFIC_PERCENTAGE` | float | 10.0      | 0-100        | Percentage of traffic to shadow               |
| `MLOPS_SHADOW_ASYNC_DISPATCH`     | bool  | true      | -            | Dispatch shadow predictions asynchronously    |
| `MLOPS_SHADOW_LOG_COMPARISONS`    | bool  | true      | -            | Log comparison results between models         |

**Use Cases:**

- **A/B Testing:** Compare accuracy of new model versions
- **Regression Detection:** Identify edge cases before rollout
- **Performance Benchmarking:** Compare latency between model versions

**Examples:**

```bash
export MLOPS_MLFLOW_ENABLED=true
export MLOPS_MLFLOW_TRACKING_URI=http://mlflow:5000
export MLOPS_DRIFT_DETECTION_ENABLED=true
export MLOPS_EXPLAINABILITY_ENABLED=true

# Shadow Mode for new model validation
export MLOPS_SHADOW_MODE_ENABLED=true
export MLOPS_SHADOW_MODEL_NAME=my-new-model-v2
export MLOPS_SHADOW_TRAFFIC_PERCENTAGE=20.0
```

---

## Setting Variables

### Method 1: Environment Variables

```bash
export MLOPS_PROFILE=production
export MLOPS_REDIS_ENABLED=true
python -m uvicorn app.main:app
```

### Method 2: .env File

Create a `.env` file:

```bash
MLOPS_PROFILE=production
MLOPS_REDIS_ENABLED=true
MLOPS_REDIS_HOST=redis.example.com
```

Then load it:

```bash
export $(cat .env | xargs)
```

### Method 3: Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mlops-sentiment-config
data:
  MLOPS_PROFILE: "production"
  MLOPS_REDIS_HOST: "redis-prod"
```

### Method 4: Docker

```bash
docker run -e MLOPS_PROFILE=production \
  -e MLOPS_REDIS_HOST=redis \
  kubesentiment:latest
```

---

## Default Values by Profile

| Setting              | Local | Dev   | Staging | Prod    |
| -------------------- | ----- | ----- | ------- | ------- |
| MLOPS_DEBUG          | true  | true  | false   | false   |
| MLOPS_LOG_LEVEL      | INFO  | DEBUG | INFO    | WARNING |
| MLOPS_WORKERS        | 1     | 1     | 2       | 4       |
| MLOPS_REDIS_ENABLED  | false | false | true    | true    |
| MLOPS_KAFKA_ENABLED  | false | false | false   | true    |
| MLOPS_VAULT_ENABLED  | false | false | true    | true    |
| MLOPS_MLFLOW_ENABLED | false | false | true    | true    |
| MLOPS_ENABLE_METRICS | false | true  | true    | true    |
| MLOPS_ENABLE_TRACING | false | false | true    | true    |

See **[Profiles](PROFILES.md)** for complete defaults for each profile.

---

## Related Documentation

- **[Quick Start](QUICK_START.md)** - 5-minute setup guide
- **[Profiles](PROFILES.md)** - Profile defaults and overrides
- **[Architecture](ARCHITECTURE.md)** - Configuration design
- **[Deployment](DEPLOYMENT.md)** - Environment-specific configurations

---

**Last Updated:** 2025-11-25
**Maintained By:** KubeSentiment Team
