# KubeSentiment API Reference

> **Version:** 1.0.0
> **Last Updated:** 2025-11-19

## Table of Contents

1. [Overview](#overview)
2. [Base URL & Authentication](#base-url--authentication)
3. [Request/Response Format](#requestresponse-format)
4. [Error Handling](#error-handling)
5. [Prediction Endpoints](#prediction-endpoints)
6. [Batch Processing Endpoints](#batch-processing-endpoints)
7. [Health & Monitoring Endpoints](#health--monitoring-endpoints)
8. [Model Information Endpoints](#model-information-endpoints)
9. [Advanced Features](#advanced-features)
10. [Rate Limiting & Performance](#rate-limiting--performance)
11. [Common Use Cases](#common-use-cases)
12. [SDK & Client Libraries](#sdk--client-libraries)

---

## Overview

KubeSentiment is a production-grade sentiment analysis API built with FastAPI. It provides real-time and batch sentiment analysis with multiple model backends (ONNX and PyTorch), Redis caching, and comprehensive observability.

### Key Features

- **Real-time Inference**: Sub-200ms latency with result caching
- **Batch Processing**: 85% performance improvement over synchronous processing
- **Multiple Backends**: ONNX (production) and PyTorch (development)
- **Caching**: Redis-based distributed caching for frequently analyzed text
- **Async Processing**: Kafka-based high-throughput batch processing
- **Comprehensive Metrics**: Performance metrics, health checks, model information
- **Structured Logging**: Full request tracing with correlation IDs

---

## Base URL & Authentication

### Base URL

```
Development: http://localhost:8000
Production:  https://api.kubesentiment.com
```

### API Versioning

All endpoints are versioned with `/api/v1` prefix:

```
/api/v1/predict
/api/v1/batch/predict
/api/v1/health
```

In debug/local mode, the version prefix is omitted:

```
/predict
/batch/predict
/health
```

### Authentication

Currently, KubeSentiment does not require authentication for all endpoints. For production deployments, consider:

- **API Keys**: Implement via custom header middleware
- **OAuth 2.0**: For third-party integrations
- **Vault Integration**: For secret management (see ADR-006)

---

## Request/Response Format

### Content-Type

All requests and responses use `application/json`:

```
Content-Type: application/json
```

### Request Structure

```json
{
  "text": "I love this product! It's amazing."
}
```

### Response Structure

```json
{
  "label": "POSITIVE",
  "score": 0.95,
  "inference_time_ms": 150.0,
  "model_name": "distilbert-base-uncased-finetuned-sst-2-english",
  "text_length": 38,
  "backend": "onnx",
  "cached": false,
  "features": null
}
```

### Response Headers

Key custom headers are included in API responses:

| Header | Example | Description |
|--------|---------|-------------|
| `X-Inference-Time-MS` | `150.0` | Model inference time in milliseconds |
| `X-Model-Backend` | `onnx` | Backend used for inference (onnx/pytorch) |
| `X-Correlation-ID` | `uuid-string` | Request correlation ID for tracing |
| `X-Request-ID` | `uuid-string` | Unique request identifier |

---

## Error Handling

### Error Response Format

All errors follow a standardized format:

```json
{
  "error_code": "E2001",
  "error_message": "Model is not loaded",
  "status_code": 503,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-11-19T10:30:00Z",
  "context": {
    "detail": "Additional error information"
  }
}
```

### Error Code Ranges

| Range | Category | Examples |
|-------|----------|----------|
| E1000-1099 | Input Validation | E1001: Invalid text input |
| E2000-2099 | Model Errors | E2001: Model not loaded, E2002: Inference failed |
| E3000-3099 | Security/Auth | E3001: Unauthorized, E3002: Invalid API key |
| E4000-4099 | System/Service | E4001: Service unavailable, E4002: Database connection error |
| E5000-5099 | Configuration | E5001: Invalid configuration, E5002: Missing required setting |
| E6000-6099 | Feature Processing | E6001: Feature extraction failed |

### Common HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Prediction completed successfully |
| 400 | Bad Request | Invalid input text format |
| 404 | Not Found | Batch job ID not found |
| 503 | Service Unavailable | Model not loaded or Kafka unavailable |
| 500 | Internal Error | Unexpected server error |

---

## Prediction Endpoints

### Single Text Prediction

**POST** `/api/v1/predict`

Analyzes sentiment of a single text with real-time inference.

#### Request

```json
{
  "text": "I absolutely love this product! Best purchase ever."
}
```

#### Request Schema

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-----------|-------------|
| `text` | string | Yes | Min: 1 char, Max: 10000 chars | Text to analyze for sentiment |

#### Response

```json
{
  "label": "POSITIVE",
  "score": 0.9823,
  "inference_time_ms": 145.2,
  "model_name": "distilbert-base-uncased-finetuned-sst-2-english",
  "text_length": 48,
  "backend": "onnx",
  "cached": false,
  "features": null
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Sentiment label: POSITIVE, NEGATIVE, NEUTRAL |
| `score` | float | Confidence score (0.0 to 1.0) |
| `inference_time_ms` | float | Model inference time in milliseconds |
| `model_name` | string | Name of the model used |
| `text_length` | integer | Length of the analyzed text |
| `backend` | string | Backend used: onnx or pytorch |
| `cached` | boolean | Whether result was served from cache |
| `features` | object | Optional advanced text features (null if not computed) |

#### Error Cases

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | E1001 | Empty or invalid text input |
| 400 | E1002 | Text exceeds maximum length |
| 503 | E2001 | Model not loaded or unavailable |
| 500 | E2002 | Inference failed during processing |

#### Example Request (cURL)

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I absolutely love this product! Best purchase ever."
  }'
```

#### Example Request (Python)

```python
import requests

url = "http://localhost:8000/api/v1/predict"
payload = {"text": "I absolutely love this product!"}

response = requests.post(url, json=payload)
result = response.json()

print(f"Sentiment: {result['label']}")
print(f"Confidence: {result['score']:.2%}")
print(f"Inference Time: {result['inference_time_ms']:.1f}ms")
```

#### Example Request (JavaScript)

```javascript
const url = "http://localhost:8000/api/v1/predict";
const payload = { text: "I absolutely love this product!" };

fetch(url, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload)
})
  .then(response => response.json())
  .then(data => {
    console.log(`Sentiment: ${data.label}`);
    console.log(`Confidence: ${(data.score * 100).toFixed(2)}%`);
    console.log(`Inference Time: ${data.inference_time_ms.toFixed(1)}ms`);
  });
```

#### Performance Notes

- **Latency**: Typically 100-300ms for first request, <50ms for cached responses
- **Throughput**: ~10 requests/second on single instance
- **Caching**: Results are cached based on text hash (Redis LRU policy)

---

## Batch Processing Endpoints

### Submit Batch Prediction Job

**POST** `/api/v1/batch/predict`

Submits multiple texts for asynchronous sentiment analysis. Returns immediately with job status.

#### Request

```json
{
  "texts": [
    "I love this product!",
    "This is terrible.",
    "It's okay, nothing special."
  ],
  "priority": "medium",
  "max_batch_size": 100,
  "timeout_seconds": 300
}
```

#### Request Schema

| Field | Type | Required | Constraints | Default | Description |
|-------|------|----------|-----------|---------|-------------|
| `texts` | array | Yes | 1-1000 items, each 1-10000 chars | - | Array of texts to analyze |
| `priority` | string | No | low, medium, high | medium | Processing priority level |
| `max_batch_size` | integer | No | 1-1000 | null | Max batch size for processing |
| `timeout_seconds` | integer | No | 10-3600 | 300 | Max time to wait for completion |

#### Response

```json
{
  "job_id": "job_550e8400e29b41d4a716446655440000",
  "status": "pending",
  "total_texts": 3,
  "estimated_completion_seconds": 45,
  "created_at": 1734596400.123,
  "priority": "medium",
  "progress_percentage": 0.0
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique identifier for the batch job |
| `status` | string | Job status: pending, processing, completed, failed |
| `total_texts` | integer | Number of texts in the batch |
| `estimated_completion_seconds` | integer | Estimated time to completion |
| `created_at` | float | Unix timestamp when job was created |
| `priority` | string | Processing priority: low, medium, high |
| `progress_percentage` | float | Processing progress (0-100%) |

#### Error Cases

| Status | Error Code | Description |
|--------|-----------|-------------|
| 400 | E1001 | Empty batch or invalid text items |
| 400 | E1003 | Batch size exceeds maximum |
| 503 | E4001 | Batch service unavailable |
| 500 | E4002 | Failed to submit batch job |

#### Example Request (Python)

```python
import requests
import time

# Submit batch job
url = "http://localhost:8000/api/v1/batch/predict"
payload = {
    "texts": [
        "I love this product!",
        "This is terrible.",
        "It's okay, nothing special."
    ],
    "priority": "high",
    "timeout_seconds": 300
}

response = requests.post(url, json=payload)
job = response.json()
job_id = job["job_id"]

print(f"Batch Job ID: {job_id}")
print(f"Status: {job['status']}")
print(f"Estimated Time: {job['estimated_completion_seconds']}s")

# Poll for completion
while True:
    status_response = requests.get(
        f"http://localhost:8000/api/v1/batch/status/{job_id}"
    )
    status = status_response.json()

    if status["status"] == "completed":
        break

    print(f"Progress: {status['progress_percentage']:.1f}%")
    time.sleep(1)
```

### Get Batch Job Status

**GET** `/api/v1/batch/status/{job_id}`

Retrieves the current status and progress of an async batch job.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Unique batch job identifier |

#### Response

```json
{
  "job_id": "job_550e8400e29b41d4a716446655440000",
  "status": "processing",
  "total_texts": 3,
  "processed_texts": 2,
  "failed_texts": 0,
  "progress_percentage": 66.7,
  "created_at": 1734596400.123,
  "started_at": 1734596405.456,
  "completed_at": null,
  "estimated_completion_seconds": 15,
  "priority": "medium",
  "error": null
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique batch job identifier |
| `status` | string | Current status: pending, processing, completed, failed |
| `total_texts` | integer | Total number of texts in batch |
| `processed_texts` | integer | Number of texts processed so far |
| `failed_texts` | integer | Number of texts that failed processing |
| `progress_percentage` | float | Processing progress (0-100%) |
| `created_at` | float | Unix timestamp when created |
| `started_at` | float | Unix timestamp when processing started |
| `completed_at` | float | Unix timestamp when completed (null if not done) |
| `estimated_completion_seconds` | integer | Estimated time to completion |
| `priority` | string | Processing priority |
| `error` | string | Error message if job failed (null if successful) |

#### Example Request

```bash
curl -X GET http://localhost:8000/api/v1/batch/status/job_550e8400e29b41d4a716446655440000
```

### Get Batch Prediction Results

**GET** `/api/v1/batch/results/{job_id}`

Retrieves paginated results from a completed batch job.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Unique batch job identifier |

#### Query Parameters

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-----------|-------------|
| `page` | integer | 1 | ≥1 | Page number (1-based) |
| `page_size` | integer | 100 | 1-1000 | Results per page |

#### Response

```json
{
  "job_id": "job_550e8400e29b41d4a716446655440000",
  "results": [
    {
      "label": "POSITIVE",
      "score": 0.98,
      "inference_time_ms": 145.2,
      "model_name": "distilbert-base-uncased-finetuned-sst-2-english",
      "text_length": 21,
      "backend": "onnx",
      "cached": false,
      "features": null
    },
    {
      "label": "NEGATIVE",
      "score": 0.97,
      "inference_time_ms": 142.8,
      "model_name": "distilbert-base-uncased-finetuned-sst-2-english",
      "text_length": 17,
      "backend": "onnx",
      "cached": false,
      "features": null
    }
  ],
  "total_results": 3,
  "page": 1,
  "page_size": 100,
  "has_more": false,
  "summary": {
    "positive_count": 2,
    "negative_count": 1,
    "neutral_count": 0,
    "average_score": 0.95,
    "total_processing_time_ms": 288.0
  }
}
```

#### Error Cases

| Status | Error Code | Description |
|--------|-----------|-------------|
| 404 | E4003 | Batch job not found or not completed |
| 500 | E4002 | Failed to retrieve batch results |

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/batch/results/job_550e8400e29b41d4a716446655440000?page=1&page_size=100"
```

### Cancel Batch Job

**DELETE** `/api/v1/batch/jobs/{job_id}`

Cancels a pending or processing batch job. Completed or failed jobs cannot be cancelled.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Unique batch job identifier |

#### Response

```json
{
  "message": "Batch job job_550e8400e29b41d4a716446655440000 cancelled successfully",
  "job_id": "job_550e8400e29b41d4a716446655440000",
  "status": "cancelled"
}
```

#### Error Cases

| Status | Error Code | Description |
|--------|-----------|-------------|
| 404 | E4003 | Batch job not found |
| 400 | E1004 | Job cannot be cancelled (already completed) |
| 500 | E4002 | Failed to cancel batch job |

#### Example Request

```bash
curl -X DELETE http://localhost:8000/api/v1/batch/jobs/job_550e8400e29b41d4a716446655440000
```

### Get Batch Metrics

**GET** `/api/v1/batch/metrics`

Retrieves comprehensive performance metrics for the async batch processing service.

#### Response

```json
{
  "total_jobs": 1250,
  "active_jobs": 12,
  "completed_jobs": 1200,
  "failed_jobs": 38,
  "average_processing_time_seconds": 52.3,
  "average_throughput_tps": 45.8,
  "queue_size": 87,
  "average_batch_size": 85.5,
  "processing_efficiency": 94.2
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_jobs` | integer | Total batch jobs created |
| `active_jobs` | integer | Currently active jobs |
| `completed_jobs` | integer | Successfully completed jobs |
| `failed_jobs` | integer | Failed jobs |
| `average_processing_time_seconds` | float | Average time per job |
| `average_throughput_tps` | float | Average throughput (texts/second) |
| `queue_size` | integer | Current batch processing queue size |
| `average_batch_size` | float | Average batch size |
| `processing_efficiency` | float | Processing efficiency percentage |

### Get Batch Queue Status

**GET** `/api/v1/batch/queue/status`

Retrieves the current status of all priority queues for batch processing.

#### Response

```json
{
  "queues": {
    "high_priority": 3,
    "medium_priority": 12,
    "low_priority": 8,
    "total": 23
  },
  "timestamp": 1734596400.123,
  "service_status": "active"
}
```

---

## Health & Monitoring Endpoints

### Basic Health Check

**GET** `/api/v1/health`

Provides a quick health status of the service and its main dependencies.

#### Response

```json
{
  "status": "healthy",
  "model_status": "loaded",
  "version": "1.0.0",
  "backend": "onnx",
  "timestamp": 1734596400.123,
  "kafka_status": "connected",
  "async_batch_status": "operational"
}
```

#### Health Status Values

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| `healthy` | All systems operational | None |
| `degraded` | Some non-critical systems down | Monitor |
| `unhealthy` | Critical systems down | Investigate |

### Detailed Health Check

**GET** `/api/v1/health/details`

Provides detailed health information for all components and dependencies.

#### Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": 1734596400.123,
  "dependencies": [
    {
      "component_name": "model",
      "details": {
        "status": "healthy",
        "error": null
      }
    },
    {
      "component_name": "redis",
      "details": {
        "status": "healthy",
        "error": null
      }
    },
    {
      "component_name": "kafka",
      "details": {
        "status": "healthy",
        "error": null
      }
    }
  ]
}
```

### Metrics Endpoint

**GET** `/api/v1/metrics`

Provides performance metrics about the API and model inference.

#### Response

```json
{
  "torch_version": "2.1.0",
  "cuda_available": true,
  "cuda_memory_allocated_mb": 1024.5,
  "cuda_memory_reserved_mb": 2048.0,
  "cuda_device_count": 1
}
```

---

## Model Information Endpoints

### Get Model Information

**GET** `/api/v1/model-info`

Retrieves detailed metadata about the currently loaded machine learning model.

#### Response

```json
{
  "model_name": "distilbert-base-uncased-finetuned-sst-2-english",
  "model_type": "transformer",
  "backend": "onnx",
  "is_loaded": true,
  "is_ready": true,
  "cache_size": 450,
  "cache_max_size": 1000
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `model_name` | string | Name of the loaded model |
| `model_type` | string | Type of model (transformer, etc.) |
| `backend` | string | Backend: onnx or pytorch |
| `is_loaded` | boolean | Whether model is loaded in memory |
| `is_ready` | boolean | Whether model is ready for inference |
| `cache_size` | integer | Current number of cached predictions |
| `cache_max_size` | integer | Maximum cache capacity |

---

## Advanced Features

### Kafka Integration

KubeSentiment includes Kafka integration for high-throughput async message processing.

#### Kafka Metrics Endpoint

**GET** `/api/v1/kafka/metrics`

Retrieves detailed metrics about Kafka consumer performance.

#### Response

```json
{
  "messages_consumed": 50000,
  "messages_processed": 49750,
  "messages_failed": 250,
  "messages_retried": 150,
  "messages_sent_to_dlq": 100,
  "total_processing_time_ms": 2500000.0,
  "avg_processing_time_ms": 50.1,
  "throughput_tps": 250.5,
  "consumer_group_lag": 45,
  "running": true,
  "consumer_threads": 4,
  "pending_batches": 12,
  "batch_queue_size": 450
}
```

### Caching Strategy

- **Cache Type**: Redis distributed cache
- **Eviction Policy**: LRU (Least Recently Used)
- **TTL**: Configurable per deployment
- **Hit Rate**: Typically 40-60% for production workloads

---

## Rate Limiting & Performance

### Recommendations

- **Single Predictions**: 10-50 requests/second per instance
- **Batch Processing**: Submit batches of 10-1000 items for optimal throughput
- **Batch Size**: Use 100-500 items per batch for best performance
- **Concurrency**: Handle 100+ concurrent requests with proper load balancing

### Performance Characteristics

| Operation | Latency | Throughput |
|-----------|---------|-----------|
| Single Prediction (cached) | <50ms | ~100 req/s |
| Single Prediction (uncached) | 100-300ms | ~10 req/s |
| Batch Submit | <100ms | N/A |
| Batch Processing | 10s-5m | Depends on batch size |

---

## Common Use Cases

### Use Case 1: Real-time Product Reviews Analysis

Analyze customer reviews as they come in, with immediate sentiment feedback.

```python
import requests

def analyze_review(review_text):
    """Analyze a single product review."""
    response = requests.post(
        "http://localhost:8000/api/v1/predict",
        json={"text": review_text}
    )
    return response.json()

# Example
review = "This product is amazing! Exceeded all expectations."
result = analyze_review(review)

if result["score"] > 0.8 and result["label"] == "POSITIVE":
    print("Positive review detected - feature for marketing")
elif result["score"] < 0.3 and result["label"] == "NEGATIVE":
    print("Negative review detected - escalate to support")
```

### Use Case 2: Batch Processing Historical Data

Process large volumes of historical data with async batch jobs.

```python
import requests
import time

def process_historical_reviews(reviews, wait_for_completion=True):
    """Process multiple historical reviews."""

    # Submit batch job
    response = requests.post(
        "http://localhost:8000/api/v1/batch/predict",
        json={
            "texts": reviews,
            "priority": "low",  # Historical data doesn't need high priority
            "timeout_seconds": 3600  # 1 hour timeout
        }
    )

    job = response.json()
    job_id = job["job_id"]

    if not wait_for_completion:
        return job_id

    # Wait for completion
    while True:
        status_response = requests.get(
            f"http://localhost:8000/api/v1/batch/status/{job_id}"
        )
        status = status_response.json()

        if status["status"] == "completed":
            break

        print(f"Progress: {status['progress_percentage']:.1f}%")
        time.sleep(5)

    # Get results
    results_response = requests.get(
        f"http://localhost:8000/api/v1/batch/results/{job_id}"
    )

    return results_response.json()
```

### Use Case 3: Monitoring Service Health

Set up health checks for monitoring and alerting.

```python
import requests
from datetime import datetime

def check_service_health():
    """Check service health for monitoring."""

    response = requests.get("http://localhost:8000/api/v1/health/details")

    if response.status_code != 200:
        print(f"Service unhealthy: {response.status_code}")
        return False

    health = response.json()

    for component in health["dependencies"]:
        if component["details"]["status"] != "healthy":
            print(f"Component {component['component_name']} is unhealthy")
            return False

    print(f"All systems healthy at {datetime.now()}")
    return True
```

---

## SDK & Client Libraries

### Python SDK

Install with pip:

```bash
pip install kubesentiment-sdk
```

Usage:

```python
from kubesentiment import KubeSentimentClient

client = KubeSentimentClient(base_url="http://localhost:8000")

# Single prediction
result = client.predict("I love this product!")
print(f"Sentiment: {result.label} ({result.score:.2%})")

# Batch processing
job = client.batch_predict([
    "I love this!",
    "I hate this!",
    "It's okay."
])

# Wait for completion and get results
results = client.wait_for_batch_results(job.job_id)
for result in results:
    print(f"{result.label}: {result.score:.2%}")
```

### JavaScript SDK

Install with npm:

```bash
npm install @kubesentiment/client
```

Usage:

```javascript
import { KubeSentimentClient } from '@kubesentiment/client';

const client = new KubeSentimentClient({
  baseUrl: 'http://localhost:8000'
});

// Single prediction
const result = await client.predict('I love this product!');
console.log(`Sentiment: ${result.label} (${(result.score * 100).toFixed(2)}%)`);

// Batch processing
const job = await client.batchPredict([
  'I love this!',
  'I hate this!',
  'It\'s okay.'
]);

// Wait for results
const results = await client.waitForBatchResults(job.jobId);
results.forEach(r => {
  console.log(`${r.label}: ${(r.score * 100).toFixed(2)}%`);
});
```

---

## See Also

- [API Versioning Strategy](./API_VERSIONING.md)
- [Error Handling Guide](./ERROR_HANDLING.md)
- [Configuration Guide](./CONFIGURATION_PROFILES.md)
- [Architecture Decisions](./architecture/decisions/)
- [Code Standards](./CODE_STANDARDS.md)

---

**Last Updated:** 2025-11-19
**Maintainer:** AI Engineering Team
