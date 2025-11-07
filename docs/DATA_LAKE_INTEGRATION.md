# Data Lake Integration

## Overview

KubeSentiment now supports streaming all predictions to cloud storage (S3, GCS, Azure Blob) in Parquet format for long-term analytics and ML research. This enables integration with query engines like AWS Athena, Google BigQuery, and Azure Synapse for powerful data analysis.

## Features

- **Multi-cloud Support**: Works with AWS S3, Google Cloud Storage, and Azure Blob Storage
- **Efficient Storage**: Uses Parquet format with configurable compression (snappy, gzip, lz4, zstd)
- **Async Streaming**: Non-blocking writes that don't impact prediction latency
- **Batch Optimization**: Configurable batching for optimal write performance
- **Partitioning**: Automatic data partitioning by date, hour, or model
- **Query Integration**: Compatible with Athena, BigQuery, and Synapse

## Configuration

### Environment Variables

Enable data lake integration by setting these environment variables:

```bash
# Enable data lake
MLOPS_DATA_LAKE_ENABLED=true

# Choose provider: s3, gcs, or azure
MLOPS_DATA_LAKE_PROVIDER=s3

# Storage bucket/container name
MLOPS_DATA_LAKE_BUCKET=my-predictions-bucket

# Optional: Path prefix (default: predictions)
MLOPS_DATA_LAKE_PREFIX=predictions

# Optional: Batch settings
MLOPS_DATA_LAKE_BATCH_SIZE=100
MLOPS_DATA_LAKE_BATCH_TIMEOUT_SECONDS=30

# Optional: Compression (default: snappy)
MLOPS_DATA_LAKE_COMPRESSION=snappy

# Optional: Partition strategy (default: date)
MLOPS_DATA_LAKE_PARTITION_BY=date
```

### AWS S3 Configuration

```bash
MLOPS_DATA_LAKE_PROVIDER=s3
MLOPS_DATA_LAKE_BUCKET=my-ml-predictions
MLOPS_DATA_LAKE_S3_REGION=us-east-1

# Optional: For S3-compatible storage (e.g., MinIO)
MLOPS_DATA_LAKE_S3_ENDPOINT_URL=http://minio:9000

# Enable Athena compatibility
MLOPS_DATA_LAKE_ENABLE_ATHENA=true
```

**AWS Credentials**: Use IAM roles (recommended) or AWS credentials file.

### Google Cloud Storage Configuration

```bash
MLOPS_DATA_LAKE_PROVIDER=gcs
MLOPS_DATA_LAKE_BUCKET=my-ml-predictions
MLOPS_DATA_LAKE_GCS_PROJECT=my-gcp-project

# Optional: Service account credentials
MLOPS_DATA_LAKE_GCS_CREDENTIALS_PATH=/path/to/service-account.json

# Enable BigQuery compatibility
MLOPS_DATA_LAKE_ENABLE_BIGQUERY=true
```

**GCP Credentials**: Use service account JSON or Application Default Credentials.

### Azure Blob Storage Configuration

```bash
MLOPS_DATA_LAKE_PROVIDER=azure
MLOPS_DATA_LAKE_BUCKET=my-ml-predictions

# Option 1: Connection string
MLOPS_DATA_LAKE_AZURE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...

# Option 2: Account name + key
MLOPS_DATA_LAKE_AZURE_ACCOUNT_NAME=mystorageaccount
MLOPS_DATA_LAKE_AZURE_ACCOUNT_KEY=your-account-key

# Enable Synapse compatibility
MLOPS_DATA_LAKE_ENABLE_SYNAPSE=true
```

## Data Schema

Each prediction is stored with the following schema:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | timestamp(us, UTC) | Prediction timestamp |
| `year` | int32 | Year (for partitioning) |
| `month` | int32 | Month (for partitioning) |
| `day` | int32 | Day (for partitioning) |
| `hour` | int32 | Hour (for partitioning) |
| `text` | string | Input text |
| `label` | string | Predicted sentiment label |
| `score` | float64 | Confidence score |
| `inference_time_ms` | float64 | Inference duration |
| `model_name` | string | Model identifier |
| `backend` | string | Backend used (pytorch/onnx) |
| `cached` | bool | Whether result was cached |
| `app_version` | string | Application version |
| `environment` | string | Deployment environment |
| `word_count` | int32 | Word count (if features enabled) |
| `avg_word_length` | float64 | Average word length |
| `sentiment_vader` | float64 | VADER sentiment score |
| `readability_score` | float64 | Text readability score |

## Partitioning Strategies

### Date Partitioning (Default)

```
predictions/
├── year=2025/
│   ├── month=01/
│   │   ├── day=15/
│   │   │   ├── predictions_20250115_143022_123456.parquet
│   │   │   └── predictions_20250115_143052_234567.parquet
```

### Hour Partitioning

```
predictions/
├── year=2025/
│   ├── month=01/
│   │   ├── day=15/
│   │   │   ├── hour=14/
│   │   │   │   └── predictions_20250115_143022_123456.parquet
```

### Model Partitioning

```
predictions/
├── model=distilbert-base-uncased-finetuned-sst-2-english/
│   ├── year=2025/
│   │   ├── month=01/
│   │   │   ├── day=15/
│   │   │   │   └── predictions_20250115_143022_123456.parquet
```

## Query Integration

### AWS Athena

1. Create an external table:

```sql
CREATE EXTERNAL TABLE predictions (
  timestamp TIMESTAMP,
  text STRING,
  label STRING,
  score DOUBLE,
  inference_time_ms DOUBLE,
  model_name STRING,
  backend STRING,
  cached BOOLEAN,
  app_version STRING,
  environment STRING,
  word_count INT,
  avg_word_length DOUBLE,
  sentiment_vader DOUBLE,
  readability_score DOUBLE
)
PARTITIONED BY (
  year INT,
  month INT,
  day INT
)
STORED AS PARQUET
LOCATION 's3://my-ml-predictions/predictions/';
```

2. Discover partitions:

```sql
MSCK REPAIR TABLE predictions;
```

3. Query your predictions:

```sql
SELECT
  DATE_TRUNC('hour', timestamp) as hour,
  label,
  COUNT(*) as count,
  AVG(score) as avg_confidence,
  AVG(inference_time_ms) as avg_latency_ms
FROM predictions
WHERE year = 2025 AND month = 1 AND day = 15
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Google BigQuery

1. Create an external table:

```sql
CREATE EXTERNAL TABLE `my-project.ml_analytics.predictions`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://my-ml-predictions/predictions/*/*.parquet'],
  hive_partition_uri_prefix = 'gs://my-ml-predictions/predictions/',
  require_hive_partition_filter = false
);
```

2. Query your predictions:

```sql
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) as hour,
  label,
  COUNT(*) as count,
  AVG(score) as avg_confidence,
  AVG(inference_time_ms) as avg_latency_ms
FROM `my-project.ml_analytics.predictions`
WHERE DATE(timestamp) = '2025-01-15'
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Azure Synapse

1. Create an external table:

```sql
CREATE EXTERNAL DATA SOURCE predictions_storage
WITH (
    LOCATION = 'https://mystorageaccount.blob.core.windows.net/my-ml-predictions',
    CREDENTIAL = storage_credential
);

CREATE EXTERNAL TABLE predictions (
    timestamp DATETIME2,
    text NVARCHAR(MAX),
    label NVARCHAR(50),
    score FLOAT,
    inference_time_ms FLOAT,
    model_name NVARCHAR(200),
    backend NVARCHAR(50),
    cached BIT,
    app_version NVARCHAR(50),
    environment NVARCHAR(50),
    word_count INT,
    avg_word_length FLOAT,
    sentiment_vader FLOAT,
    readability_score FLOAT,
    year INT,
    month INT,
    day INT
)
WITH (
    LOCATION = '/predictions/',
    DATA_SOURCE = predictions_storage,
    FILE_FORMAT = parquet_format
);
```

2. Query your predictions:

```sql
SELECT
  DATEPART(HOUR, timestamp) as hour,
  label,
  COUNT(*) as count,
  AVG(score) as avg_confidence,
  AVG(inference_time_ms) as avg_latency_ms
FROM predictions
WHERE year = 2025 AND month = 1 AND day = 15
GROUP BY DATEPART(HOUR, timestamp), label
ORDER BY hour, label;
```

## Performance Tuning

### Batch Size

- **Small batches (10-50)**: Lower latency, more frequent writes
- **Medium batches (100-200)**: Balanced performance (default: 100)
- **Large batches (500-1000)**: Higher throughput, less frequent writes

```bash
MLOPS_DATA_LAKE_BATCH_SIZE=200
```

### Batch Timeout

Controls maximum time to wait before flushing:

```bash
MLOPS_DATA_LAKE_BATCH_TIMEOUT_SECONDS=30  # Default
```

### Compression

- **snappy** (default): Fast compression, good balance
- **gzip**: Higher compression ratio, slower
- **lz4**: Very fast, lower compression
- **zstd**: Best compression, moderate speed
- **none**: No compression, fastest writes

```bash
MLOPS_DATA_LAKE_COMPRESSION=snappy
```

## Monitoring

Check data writer status via the `/health` endpoint:

```bash
curl http://localhost:8000/health
```

The response includes data writer statistics if enabled.

You can also check application logs for data lake events:

```
Data lake writer started successfully provider=s3 bucket=my-predictions-bucket
Flushed 100 predictions to data lake
```

## Use Cases

### ML Research

Analyze historical predictions to understand model behavior:

```sql
-- Find predictions with low confidence
SELECT text, label, score
FROM predictions
WHERE score < 0.7
ORDER BY score
LIMIT 100;
```

### Performance Analysis

Track inference latency over time:

```sql
SELECT
  DATE_TRUNC('day', timestamp) as day,
  backend,
  AVG(inference_time_ms) as avg_latency,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY inference_time_ms) as p95_latency
FROM predictions
GROUP BY 1, 2
ORDER BY 1, 2;
```

### A/B Testing

Compare model versions:

```sql
SELECT
  model_name,
  COUNT(*) as predictions,
  AVG(score) as avg_confidence,
  SUM(CASE WHEN label = 'POSITIVE' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as positive_rate
FROM predictions
WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '7' DAY
GROUP BY model_name;
```

### Cost Analysis

Track prediction volumes and costs:

```sql
SELECT
  DATE_TRUNC('day', timestamp) as day,
  environment,
  COUNT(*) as predictions,
  COUNT(*) * 0.00001 as estimated_cost_usd
FROM predictions
GROUP BY 1, 2
ORDER BY 1, 2;
```

## Security Best Practices

1. **Use IAM Roles**: Prefer instance/pod IAM roles over static credentials
2. **Encrypt at Rest**: Enable bucket encryption (S3: SSE, GCS: CMEK, Azure: ADE)
3. **Encrypt in Transit**: Always use HTTPS endpoints
4. **Least Privilege**: Grant only necessary permissions (write to specific prefix)
5. **Network Security**: Use VPC endpoints/private links when possible
6. **Audit Logging**: Enable CloudTrail/Cloud Audit Logs/Azure Monitor

## Troubleshooting

### Predictions not appearing in storage

1. Check if data lake is enabled:
   ```bash
   echo $MLOPS_DATA_LAKE_ENABLED
   ```

2. Verify credentials are configured correctly

3. Check application logs for errors:
   ```bash
   kubectl logs -f deployment/kubesentiment | grep "data lake"
   ```

### High latency

The data writer uses async operations and should not impact latency. If you see issues:

1. Increase batch timeout to reduce write frequency
2. Check network connectivity to storage
3. Monitor storage performance metrics

### Storage costs

To optimize costs:

1. Use appropriate compression (snappy is good default)
2. Enable lifecycle policies to archive old data
3. Consider partitioning strategy (date vs hour)
4. Use tiered storage for older data

## Example Deployment

Kubernetes deployment with data lake enabled:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kubesentiment
spec:
  template:
    spec:
      serviceAccountName: kubesentiment-sa  # With IAM role
      containers:
      - name: api
        image: kubesentiment:latest
        env:
        - name: MLOPS_DATA_LAKE_ENABLED
          value: "true"
        - name: MLOPS_DATA_LAKE_PROVIDER
          value: "s3"
        - name: MLOPS_DATA_LAKE_BUCKET
          value: "ml-predictions-prod"
        - name: MLOPS_DATA_LAKE_S3_REGION
          value: "us-east-1"
        - name: MLOPS_DATA_LAKE_ENABLE_ATHENA
          value: "true"
```

## Future Enhancements

Planned features for data lake integration:

- Real-time streaming with Apache Iceberg/Delta Lake
- Automatic schema evolution
- Data quality validation before writes
- Integration with Apache Airflow for ETL pipelines
- Support for Apache Druid for real-time analytics
- Automatic table creation in query engines
