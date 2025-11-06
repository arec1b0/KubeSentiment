# Quick Wins Features - Implementation Guide

This document describes the five major "Quick Win" features implemented to enhance KubeSentiment's production capabilities.

## Table of Contents

1. [MLflow Model Registry Integration](#1-mlflow-model-registry-integration)
2. [Model Drift Detection](#2-model-drift-detection)
3. [Explainability & Interpretability](#3-explainability--interpretability)
4. [Advanced Metrics & KPIs](#4-advanced-metrics--kpis)
5. [SDK & Client Libraries](#5-sdk--client-libraries)
6. [Configuration](#configuration)
7. [API Reference](#api-reference)

---

## 1. MLflow Model Registry Integration

### Overview
MLflow Model Registry integration enables production-grade model lifecycle management, versioning, and A/B testing capabilities.

### Features
- **Model Versioning**: Track all model versions with metadata
- **Stage Management**: Promote models through None → Staging → Production → Archived
- **A/B Testing**: Run multiple production models simultaneously
- **Performance Tracking**: Log prediction metrics per model version
- **Model Lineage**: Track model origins, training runs, and deployments

### Configuration

```bash
# Enable MLflow
export MLOPS_MLFLOW_ENABLED=true
export MLOPS_MLFLOW_TRACKING_URI=http://mlflow:5000
export MLOPS_MLFLOW_MODEL_NAME=sentiment-model
```

### API Endpoints

#### List Registered Models
```bash
GET /api/v1/monitoring/models
```

Response:
```json
{
  "enabled": true,
  "count": 2,
  "models": [
    {
      "name": "sentiment-model",
      "creation_timestamp": 1234567890,
      "latest_versions": [
        {"version": 3, "stage": "Production"},
        {"version": 2, "stage": "Staging"}
      ]
    }
  ]
}
```

#### Get Production Model
```bash
GET /api/v1/monitoring/models/sentiment-model/production
```

Response:
```json
{
  "name": "sentiment-model",
  "version": 3,
  "stage": "Production",
  "source": "s3://models/sentiment/v3",
  "run_id": "abc123",
  "tags": {"accuracy": "0.95"}
}
```

### Python Usage

```python
from app.services.mlflow_registry import get_model_registry

registry = get_model_registry()

# Register a new model
registry.register_model(
    model_name="sentiment-model",
    model_uri="s3://models/sentiment/v4",
    tags={"accuracy": "0.96", "framework": "pytorch"},
    description="Improved model with fine-tuning"
)

# Promote to production
registry.promote_to_production("sentiment-model", version=4, archive_existing=True)

# Log metrics
registry.log_prediction_metrics(
    "sentiment-model",
    version=4,
    metrics={"latency_p95_ms": 25.5, "accuracy": 0.96}
)
```

---

## 2. Model Drift Detection

### Overview
Comprehensive drift detection system that monitors both data drift (input changes) and prediction drift (output changes) using statistical tests.

### Features
- **Data Drift Detection**: Monitor input distribution changes
- **Prediction Drift Detection**: Track output distribution shifts
- **Statistical Tests**:
  - PSI (Population Stability Index): 0.1 = minor drift, 0.25 = major drift
  - KS Test (Kolmogorov-Smirnov): Continuous distribution comparison
  - Chi-Squared Test: Categorical distribution comparison
- **Real-time Monitoring**: Automatic drift checks on predictions
- **Prometheus Integration**: Drift metrics exposed for alerting
- **HTML Reports**: Detailed Evidently-based drift reports

### Configuration

```bash
# Enable drift detection
export MLOPS_DRIFT_DETECTION_ENABLED=true
export MLOPS_DRIFT_WINDOW_SIZE=1000
export MLOPS_DRIFT_PSI_THRESHOLD=0.1
export MLOPS_DRIFT_KS_THRESHOLD=0.05
```

### API Endpoints

#### Get Drift Summary
```bash
GET /api/v1/monitoring/drift
```

Response:
```json
{
  "enabled": true,
  "baseline_established": true,
  "baseline_size": 1000,
  "current_window_size": 857,
  "last_check": "2025-01-15T10:30:00Z",
  "drifts_last_24h": 2,
  "latest_drift_score": 0.08,
  "thresholds": {
    "psi": 0.1,
    "ks_pvalue": 0.05
  }
}
```

#### Check for Current Drift
```bash
GET /api/v1/monitoring/drift/check
```

Response:
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "data_drift_detected": false,
  "prediction_drift_detected": false,
  "drift_score": 0.08,
  "statistical_tests": {
    "confidence_psi": 0.07,
    "confidence_ks_pvalue": 0.12,
    "text_length_psi": 0.09,
    "prediction_chi2_pvalue": 0.45
  },
  "feature_drifts": {
    "confidence": 0.07,
    "text_length": 0.09
  }
}
```

#### Export Drift Report (HTML)
```bash
GET /api/v1/monitoring/drift/report
```

Returns interactive HTML report with:
- Data quality metrics
- Drift detection results
- Statistical test details
- Distribution visualizations

#### Reset Drift Window
```bash
POST /api/v1/monitoring/drift/reset
```

#### Update Baseline
```bash
POST /api/v1/monitoring/drift/update-baseline
```

### Python Usage

```python
from app.services.drift_detection import get_drift_detector

detector = get_drift_detector()

# Add predictions to detector
detector.add_prediction(
    text="This is great!",
    confidence=0.95,
    prediction="POSITIVE",
    is_reference=False  # False for current data, True for baseline
)

# Check for drift
drift_metrics = detector.check_drift()
if drift_metrics and drift_metrics.data_drift_detected:
    print(f"⚠️  Data drift detected! Score: {drift_metrics.drift_score}")
    print(f"Tests: {drift_metrics.statistical_tests}")

# Update baseline after deploying new model
detector.update_baseline()
```

---

## 3. Explainability & Interpretability

### Overview
Model explainability engine providing multiple interpretation methods to build user trust and debug model behavior.

### Features
- **Attention Weights**: Visualize transformer attention patterns
- **Word-level Importance**: Identify contributing words/phrases
- **Integrated Gradients**: Gradient-based feature attribution (optional)
- **Confidence Calibration**: Human-readable confidence interpretation
- **Text Features**: Extract interpretable linguistic features
- **HTML Visualization**: Interactive explanation display

### Configuration

```bash
# Enable explainability
export MLOPS_EXPLAINABILITY_ENABLED=true
export MLOPS_EXPLAINABILITY_USE_ATTENTION=true
export MLOPS_EXPLAINABILITY_USE_GRADIENTS=false  # Slower but more detailed
```

### API Endpoints

#### Explain Prediction
```bash
POST /api/v1/monitoring/explain
Content-Type: application/json

{
  "text": "This movie was absolutely amazing!",
  "prediction": "POSITIVE",
  "confidence": 0.9876,
  "use_attention": true,
  "use_gradients": false
}
```

Response:
```json
{
  "text": "This movie was absolutely amazing!",
  "prediction": "POSITIVE",
  "confidence": 0.9876,
  "explanation_methods": ["attention"],
  "attention": {
    "word_importance": [
      {"word": "absolutely", "importance": 0.25, "position": 3},
      {"word": "amazing", "importance": 0.23, "position": 4},
      {"word": "movie", "importance": 0.12, "position": 1}
    ]
  },
  "top_contributing_words": ["absolutely", "amazing", "movie"],
  "confidence_interpretation": "Very high confidence - strong signal",
  "text_features": {
    "length": 38,
    "word_count": 6,
    "positive_word_count": 2,
    "negative_word_count": 0,
    "has_exclamation": true
  }
}
```

#### Get HTML Explanation
```bash
POST /api/v1/monitoring/explain/html
```

Returns interactive HTML visualization with highlighted words colored by importance.

### Python Usage

```python
from app.services.explainability import get_explainability_engine

explainer = get_explainability_engine()

# Generate explanation
explanation = explainer.explain_prediction(
    text="This movie was absolutely amazing!",
    prediction="POSITIVE",
    confidence=0.9876,
    use_attention=True,
    use_gradients=False
)

print(f"Top words: {explanation['top_contributing_words']}")
print(f"Interpretation: {explanation['confidence_interpretation']}")

# Generate HTML report
html = explainer.generate_html_explanation(explanation)
```

---

## 4. Advanced Metrics & KPIs

### Overview
Comprehensive metrics collection beyond basic observability, providing business insights, quality tracking, cost optimization, and SLO compliance monitoring.

### Features
- **Business Metrics**: Prediction quality, label distribution, confidence trends
- **Quality Metrics**: Low-confidence rate, confidence distribution, percentiles
- **Cost Metrics**: Per-prediction cost, monthly estimates, cache savings
- **Performance Metrics**: Detailed latency breakdown, throughput, backend comparison
- **SLO Compliance**: Availability, latency targets, compliance tracking
- **Prometheus Integration**: All metrics exposed for alerting

### Configuration

```bash
# Enable advanced metrics
export MLOPS_ADVANCED_METRICS_ENABLED=true
export MLOPS_ADVANCED_METRICS_DETAILED_TRACKING=true
export MLOPS_ADVANCED_METRICS_COST_PER_1K=0.01  # USD per 1000 predictions
```

### API Endpoints

#### Business KPIs
```bash
GET /api/v1/monitoring/kpis/business
```

Response:
```json
{
  "total_predictions": 15234,
  "positive_ratio": 0.6543,
  "negative_ratio": 0.3457,
  "avg_confidence": 0.8756,
  "high_quality_ratio": 0.7823,
  "predictions_by_label": {
    "POSITIVE": 9968,
    "NEGATIVE": 5266
  },
  "predictions_by_confidence": {
    "very_high": 8234,
    "high": 5123,
    "medium": 1654,
    "low": 223
  }
}
```

#### Quality Metrics
```bash
GET /api/v1/monitoring/kpis/quality
```

Response:
```json
{
  "total_predictions": 15234,
  "low_confidence_rate": 0.0146,
  "low_confidence_count": 223,
  "confidence_std": 0.1234,
  "confidence_p50": 0.8945,
  "confidence_p95": 0.9876,
  "confidence_p99": 0.9954
}
```

#### Cost Metrics
```bash
GET /api/v1/monitoring/kpis/cost
```

Response:
```json
{
  "total_cost_usd": 0.152340,
  "cost_per_prediction_usd": 0.000010,
  "monthly_estimate_usd": 4.57,
  "total_predictions": 15234,
  "cached_predictions": 3456,
  "cache_savings_percent": 22.68,
  "cost_by_day": {
    "2025-01-14": 0.045620,
    "2025-01-15": 0.106720
  }
}
```

#### Performance Metrics
```bash
GET /api/v1/monitoring/kpis/performance
```

Response:
```json
{
  "total_predictions": 15234,
  "latency_avg_ms": 28.45,
  "latency_p50_ms": 25.12,
  "latency_p95_ms": 45.67,
  "latency_p99_ms": 78.90,
  "latency_by_backend": {
    "onnx": {"avg": 22.34, "p95": 38.56, "count": 12000},
    "pytorch": {"avg": 52.78, "p95": 89.12, "count": 3234}
  },
  "throughput_rps": 5.67
}
```

#### SLO Compliance
```bash
GET /api/v1/monitoring/kpis/slo?availability_target=99.9&latency_p95_target_ms=100&latency_p99_target_ms=250
```

Response:
```json
{
  "compliant": true,
  "availability": {
    "current": 99.95,
    "target": 99.9,
    "ok": true
  },
  "latency_p95": {
    "current_ms": 45.67,
    "target_ms": 100,
    "ok": true
  },
  "latency_p99": {
    "current_ms": 78.90,
    "target_ms": 250,
    "ok": true
  }
}
```

### Prometheus Metrics

New metrics exposed at `/api/v1/metrics`:

```prometheus
# Business Metrics
sentiment_business_predictions_total{label="POSITIVE",confidence_bucket="very_high"} 8234
sentiment_business_confidence_distribution_bucket{le="0.95"} 12000

# Quality Metrics
sentiment_quality_low_confidence_total{label="POSITIVE"} 156
sentiment_quality_rejection_rate 1.46

# Cost Metrics
sentiment_cost_total_usd 0.152340
sentiment_cost_per_prediction_usd 0.000010
sentiment_cost_monthly_burn_rate_usd 4.57

# Performance Metrics
sentiment_performance_latency_detailed_ms_bucket{backend="onnx",cached="false",le="25"} 6000
sentiment_performance_throughput_rps 5.67

# SLO Metrics
sentiment_slo_availability_percent 99.95
sentiment_slo_latency_p95_ms 45.67
sentiment_slo_latency_p99_ms 78.90
```

---

## 5. SDK & Client Libraries

### Overview
Official client libraries for Python and JavaScript/TypeScript to simplify integration with KubeSentiment API.

### Features
- **Type-Safe**: Full TypeScript types and Python type hints
- **Auto-Retry**: Built-in retry logic for transient failures
- **Async Support**: Batch predictions with wait/poll capabilities
- **Error Handling**: Comprehensive error types
- **Examples**: Rich documentation and examples

---

### Python SDK

#### Installation

```bash
pip install requests  # Dependency
cp sdk/python/kubesentiment_sdk.py /path/to/your/project/
```

#### Quick Start

```python
from kubesentiment_sdk import KubeSentimentClient

# Create client
client = KubeSentimentClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"  # Optional
)

# Single prediction
result = client.predict("This is amazing!")
print(f"{result.label}: {result.confidence:.2%}")
# Output: POSITIVE: 98.76%

# Check confidence
if result.is_confident(threshold=0.8):
    print("High confidence prediction")

# Batch prediction (wait for completion)
texts = ["Great product!", "Terrible service", "It's okay"]
job = client.batch_predict(texts, priority="high", wait=True)

for result in job.results:
    print(f"{result.label}: {result.confidence:.2%}")

# Batch prediction (async)
job = client.batch_predict(texts, wait=False)
print(f"Job ID: {job.job_id}")

# Poll for status
import time
while True:
    status = client.get_batch_status(job.job_id)
    if status.status == "completed":
        results = client.get_batch_results(job.job_id)
        break
    time.sleep(2)

# Get model info
info = client.get_model_info()
print(info)

# Health check
health = client.health_check()
print(health["status"])

# Get drift summary
drift = client.get_drift_summary()
print(f"Drift detected: {drift['drifts_last_24h']}")

# Get business KPIs
kpis = client.get_business_kpis()
print(f"Total predictions: {kpis['total_predictions']}")
```

#### Context Manager

```python
with KubeSentimentClient(base_url="http://localhost:8000") as client:
    result = client.predict("Hello world")
    print(result.label)
```

#### Convenience Function

```python
from kubesentiment_sdk import predict

result = predict("I love this!", base_url="http://localhost:8000")
print(result.label)
```

---

### JavaScript/TypeScript SDK

#### Installation

```bash
cp sdk/javascript/kubesentiment-sdk.ts /path/to/your/project/src/
```

#### Quick Start

```typescript
import { KubeSentimentClient, Priority } from './kubesentiment-sdk';

// Create client
const client = new KubeSentimentClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key',  // Optional
  timeout: 30000  // Optional, default 30s
});

// Single prediction
const result = await client.predict('This is amazing!');
console.log(`${result.label}: ${(result.confidence * 100).toFixed(2)}%`);
// Output: POSITIVE: 98.76%

// With explanation
const explainedResult = await client.predict('This is great!', {
  explain: true
});
console.log(explainedResult.explanation);

// Batch prediction (wait for completion)
const texts = ['Great product!', 'Terrible service', "It's okay"];
const job = await client.batchPredict(texts, {
  priority: Priority.HIGH,
  wait: true,
  pollInterval: 2000
});

job.results?.forEach(result => {
  console.log(`${result.label}: ${(result.confidence * 100).toFixed(2)}%`);
});

// Batch prediction (async)
const asyncJob = await client.batchPredict(texts, {
  priority: Priority.MEDIUM,
  wait: false
});
console.log(`Job ID: ${asyncJob.jobId}`);

// Poll for status
const finalJob = await client.waitForJob(asyncJob.jobId, 2000, 300000);
console.log('Job completed!', finalJob.results);

// Get model info
const modelInfo = await client.getModelInfo();
console.log(modelInfo);

// Health check
const health = await client.healthCheck();
console.log(health.status);

// Get drift summary
const drift = await client.getDriftSummary();
console.log(`Drift checks: ${drift.total_drift_checks}`);

// Get business KPIs
const kpis = await client.getBusinessKPIs();
console.log(`Total predictions: ${kpis.total_predictions}`);
```

#### Convenience Function

```typescript
import { predict } from './kubesentiment-sdk';

const result = await predict('I love this!', 'http://localhost:8000');
console.log(result.label);
```

#### Error Handling

```typescript
import { KubeSentimentClient, APIError, KubeSentimentError } from './kubesentiment-sdk';

try {
  const result = await client.predict('Hello');
} catch (error) {
  if (error instanceof APIError) {
    console.error(`API Error ${error.statusCode}: ${error.message}`);
  } else if (error instanceof KubeSentimentError) {
    console.error(`SDK Error: ${error.message}`);
  } else {
    console.error('Unknown error:', error);
  }
}
```

---

## Configuration

### Environment Variables

All new features can be configured via environment variables with the `MLOPS_` prefix:

```bash
# MLflow Model Registry
MLOPS_MLFLOW_ENABLED=true
MLOPS_MLFLOW_TRACKING_URI=http://mlflow:5000
MLOPS_MLFLOW_REGISTRY_URI=http://mlflow:5000  # Optional, defaults to tracking URI
MLOPS_MLFLOW_EXPERIMENT_NAME=sentiment-analysis
MLOPS_MLFLOW_MODEL_NAME=sentiment-model

# Drift Detection
MLOPS_DRIFT_DETECTION_ENABLED=true
MLOPS_DRIFT_WINDOW_SIZE=1000  # Number of samples
MLOPS_DRIFT_PSI_THRESHOLD=0.1  # 0.1=minor, 0.25=major
MLOPS_DRIFT_KS_THRESHOLD=0.05  # p-value threshold
MLOPS_DRIFT_MIN_SAMPLES=100  # Min samples before checking

# Explainability
MLOPS_EXPLAINABILITY_ENABLED=true
MLOPS_EXPLAINABILITY_USE_ATTENTION=true
MLOPS_EXPLAINABILITY_USE_GRADIENTS=false  # Slower

# Advanced Metrics
MLOPS_ADVANCED_METRICS_ENABLED=true
MLOPS_ADVANCED_METRICS_DETAILED_TRACKING=true
MLOPS_ADVANCED_METRICS_HISTORY_HOURS=24
MLOPS_ADVANCED_METRICS_COST_PER_1K=0.01  # USD
```

### Helm Values

In `helm/mlops-sentiment/values.yaml`:

```yaml
config:
  # MLflow
  mlflowEnabled: true
  mlflowTrackingUri: "http://mlflow:5000"
  mlflowModelName: "sentiment-model"

  # Drift Detection
  driftDetectionEnabled: true
  driftWindowSize: 1000
  driftPsiThreshold: 0.1

  # Explainability
  explainabilityEnabled: true
  explainabilityUseAttention: true

  # Advanced Metrics
  advancedMetricsEnabled: true
  advancedMetricsCostPer1k: 0.01
```

---

## API Reference

### Complete Endpoint List

#### MLflow Model Registry
- `GET /api/v1/monitoring/models` - List registered models
- `GET /api/v1/monitoring/models/{name}/production` - Get production model
- `GET /api/v1/monitoring/models/{name}/versions` - Get all production versions

#### Drift Detection
- `GET /api/v1/monitoring/drift` - Get drift summary
- `GET /api/v1/monitoring/drift/check` - Check current drift
- `POST /api/v1/monitoring/drift/reset` - Reset drift window
- `POST /api/v1/monitoring/drift/update-baseline` - Update baseline
- `GET /api/v1/monitoring/drift/report` - Export HTML report

#### Explainability
- `POST /api/v1/monitoring/explain` - Explain prediction (JSON)
- `POST /api/v1/monitoring/explain/html` - Explain prediction (HTML)

#### Advanced KPIs
- `GET /api/v1/monitoring/kpis/business` - Business metrics
- `GET /api/v1/monitoring/kpis/quality` - Quality metrics
- `GET /api/v1/monitoring/kpis/cost` - Cost metrics
- `GET /api/v1/monitoring/kpis/performance` - Performance metrics
- `GET /api/v1/monitoring/kpis/slo` - SLO compliance

#### Monitoring Health
- `GET /api/v1/monitoring/health` - Health of monitoring components

---

## Next Steps

1. **Deploy MLflow Server**: Set up MLflow tracking server for model registry
2. **Configure Alerts**: Set up Prometheus alerts for drift detection and SLO violations
3. **Integrate SDKs**: Use Python/JS SDKs in your applications
4. **Monitor Dashboards**: Create Grafana dashboards for advanced KPIs
5. **Enable Explainability**: Test explanation endpoints for model debugging

For more information, see the main [Architecture Documentation](architecture.md).
