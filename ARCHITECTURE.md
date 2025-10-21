# MLOps Sentiment Analysis - System Architecture

**Version:** 1.0.0  
**Last Updated:** October 21, 2025  
**Status:** Production-Ready

## Table of Contents

- [Executive Summary](#executive-summary)
- [System Overview](#system-overview)
- [Architecture Patterns](#architecture-patterns)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Deployment Topology](#deployment-topology)
- [Technology Stack](#technology-stack)
- [Security Architecture](#security-architecture)
- [Scalability & Performance](#scalability--performance)
- [Observability & Monitoring](#observability--monitoring)
- [Disaster Recovery](#disaster-recovery)

---

## Executive Summary

The MLOps Sentiment Analysis Microservice is a production-grade, cloud-native AI service built on modern MLOps principles. It provides real-time sentiment analysis with <100ms response times, horizontal scalability, and comprehensive observability.

### Key Characteristics

- **Architecture Style**: Microservices, Cloud-Native, Event-Driven
- **Deployment Model**: Kubernetes-native with multi-environment support
- **API Pattern**: RESTful with OpenAPI 3.0 specification
- **Data Processing**: Real-time inference with intelligent caching
- **Observability**: Three pillars (Metrics, Logs, Traces)
- **Security**: Zero-trust model with mTLS and secret management

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
│  (Web Apps, Mobile Apps, Batch Processes, External APIs)        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway / Ingress                         │
│        (Authentication, Rate Limiting, Load Balancing)           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Service Pod 1  │ │  Service Pod 2  │ │  Service Pod N  │
│                 │ │                 │ │                 │
│  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │
│  │   API     │  │ │  │   API     │  │ │  │   API     │  │
│  │  Router   │  │ │  │  Router   │  │ │  │  Router   │  │
│  └─────┬─────┘  │ │  └─────┬─────┘  │ │  └─────┬─────┘  │
│        │        │ │        │        │ │        │        │
│  ┌─────▼─────┐  │ │  ┌─────▼─────┐  │ │  ┌─────▼─────┐  │
│  │  Service  │  │ │  │  Service  │  │ │  │  Service  │  │
│  │   Layer   │  │ │  │   Layer   │  │ │  │   Layer   │  │
│  └─────┬─────┘  │ │  └─────┬─────┘  │ │  └─────┬─────┘  │
│        │        │ │        │        │ │        │        │
│  ┌─────▼─────┐  │ │  ┌─────▼─────┐  │ │  ┌─────▼─────┐  │
│  │   Model   │  │ │  │   Model   │  │ │  │   Model   │  │
│  │  Factory  │  │ │  │  Factory  │  │ │  │  Factory  │  │
│  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
                ▼            ▼            ▼
┌────────────────────┐ ┌──────────┐ ┌──────────────┐
│  Model Cache       │ │  Vault   │ │  Monitoring  │
│  (Persistent Vol)  │ │ (Secrets)│ │ (Prometheus) │
└────────────────────┘ └──────────┘ └──────────────┘
```

### Core Principles

1. **Separation of Concerns**: Clear boundaries between API, business logic, and ML models
2. **Dependency Injection**: Loose coupling through FastAPI's DI system
3. **Factory Pattern**: Flexible model instantiation and backend selection
4. **Strategy Pattern**: Interchangeable ML backends (PyTorch, ONNX)
5. **Service Layer**: Business logic isolated from presentation and data layers
6. **Stateless Design**: Horizontal scalability without session affinity

---

## Architecture Patterns

### 1. Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Presentation Layer                      │
│  (API Routes, Middleware, Request/Response Schemas)      │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   Service Layer                          │
│      (Business Logic, Orchestration, Validation)         │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   Domain Layer                           │
│        (ML Models, Strategies, Core Algorithms)          │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│              Infrastructure Layer                        │
│  (Configuration, Logging, Metrics, External Services)    │
└─────────────────────────────────────────────────────────┘
```

### 2. Strategy Pattern (Model Backends)

```python
# Protocol Definition
class ModelStrategy(Protocol):
    def is_ready(self) -> bool: ...
    def predict(self, text: str) -> Dict[str, Any]: ...
    def get_model_info(self) -> Dict[str, Any]: ...
    def get_performance_metrics(self) -> Dict[str, Any]: ...

# Concrete Implementations
- PyTorchSentimentAnalyzer (app/ml/sentiment.py)
- ONNXSentimentAnalyzer (app/ml/onnx_optimizer.py)
- [Future: TensorRTAnalyzer, TFServingAnalyzer]
```

### 3. Factory Pattern (Model Creation)

```python
class ModelFactory:
    @staticmethod
    def create_model(backend: ModelBackend) -> ModelStrategy:
        if backend == ModelBackend.PYTORCH:
            return get_pytorch_analyzer()
        elif backend == ModelBackend.ONNX:
            return get_onnx_analyzer()
        # Extensible for future backends
```

### 4. Dependency Injection

```python
# Dependencies flow from outer to inner layers
Route Handler → depends on → Prediction Service
     ↓                              ↓
Dependencies              depends on Model (via Factory)
     ↓                              ↓
Configuration            depends on Settings
```

---

## Component Architecture

### Directory Structure

```
app/
├── core/                       # Core Infrastructure
│   ├── config.py               # Pydantic settings management
│   ├── logging.py              # Structured logging with correlation IDs
│   ├── dependencies.py         # FastAPI dependency injection
│   ├── events.py               # Application lifecycle (startup/shutdown)
│   └── secrets.py              # HashiCorp Vault integration
│
├── api/                        # API Layer (Presentation)
│   ├── routes/                 # HTTP endpoints
│   │   ├── health.py           # Health & readiness probes
│   │   ├── predictions.py      # Prediction endpoints
│   │   ├── metrics.py          # Metrics export
│   │   └── model_info.py       # Model metadata
│   ├── middleware/             # Cross-cutting concerns
│   │   ├── correlation.py      # Request correlation tracking
│   │   ├── auth.py             # API key authentication
│   │   ├── logging.py          # Request/response logging
│   │   └── metrics.py          # Automatic metrics collection
│   └── schemas/                # Pydantic models
│       ├── requests.py         # Input validation
│       └── responses.py        # Output serialization
│
├── services/                   # Service Layer (Business Logic)
│   └── prediction.py           # Prediction orchestration
│
├── ml/                         # Domain Layer (ML Models)
│   ├── model_strategy.py       # Model protocol definition
│   ├── sentiment.py            # PyTorch implementation
│   └── onnx_optimizer.py       # ONNX Runtime implementation
│
├── monitoring/                 # Observability
│   ├── prometheus.py           # Metrics collection
│   ├── health.py               # Health check utilities
│   └── vault_health.py         # Vault connectivity monitoring
│
└── utils/                      # Shared Utilities
    ├── exceptions.py           # Custom exception hierarchy
    ├── error_codes.py          # Standardized error codes
    └── error_handlers.py       # Global error handlers
```

### Module Responsibilities

#### Core Module (`app/core/`)

**Purpose**: Foundation for the entire application

- **Configuration Management**: Environment-based settings with validation
- **Logging**: Structured JSON logs with correlation IDs
- **Dependency Injection**: Provide dependencies to routes and services
- **Lifecycle Management**: Startup/shutdown event handlers
- **Secret Management**: Secure access to Vault-stored secrets

#### API Module (`app/api/`)

**Purpose**: HTTP interface and request handling

- **Routes**: RESTful endpoints with OpenAPI documentation
- **Middleware**: Cross-cutting concerns (auth, logging, metrics, CORS)
- **Schemas**: Request/response validation and serialization
- **Error Handling**: Consistent error responses with proper HTTP codes

#### Service Layer (`app/services/`)

**Purpose**: Business logic and orchestration

- **Prediction Service**: Coordinates between API and ML models
- **Validation Logic**: Business rules enforcement
- **Caching Strategy**: Result caching and invalidation
- **Metrics Recording**: Business metrics collection

#### ML Module (`app/ml/`)

**Purpose**: Machine learning model management

- **Model Strategy**: Protocol defining model interface
- **PyTorch Analyzer**: Standard transformer-based sentiment analysis
- **ONNX Analyzer**: Optimized inference with ONNX Runtime
- **Model Loading**: Lazy loading with error recovery
- **Prediction Caching**: LRU cache with BLAKE2b hashing

#### Monitoring Module (`app/monitoring/`)

**Purpose**: Observability and health monitoring

- **Prometheus Metrics**: Request counts, latencies, error rates
- **Health Checks**: Liveness and readiness probes
- **Vault Monitoring**: Secret management system health
- **Custom Business Metrics**: Model-specific KPIs

---

## Data Flow

### Request Lifecycle

```
1. Client Request
   ↓
2. Ingress/LoadBalancer (TLS termination, routing)
   ↓
3. Correlation Middleware (add correlation ID)
   ↓
4. Authentication Middleware (validate API key)
   ↓
5. Logging Middleware (log request details)
   ↓
6. Metrics Middleware (record request metrics)
   ↓
7. Route Handler (endpoint logic)
   ↓
8. Service Layer (business logic orchestration)
   ↓
9. Cache Check (check for cached prediction)
   ↓ (cache miss)
10. Model Strategy (select backend: PyTorch/ONNX)
   ↓
11. Model Inference (run prediction)
   ↓
12. Cache Update (store result with LRU eviction)
   ↓
13. Metrics Recording (record inference time, confidence)
   ↓
14. Response Serialization (Pydantic model)
   ↓
15. Response Middleware (add headers: correlation ID, process time)
   ↓
16. Client Response
```

### Prediction Flow (Detailed)

```python
# 1. API Route receives request
POST /api/v1/predict
{
  "text": "I love this product!",
  "backend": "onnx"  # optional
}

# 2. Schema validation (automatic via Pydantic)
PredictionRequest.validate(request_body)

# 3. Dependency injection provides dependencies
prediction_service = get_prediction_service()  # From DI container

# 4. Service layer orchestration
result = prediction_service.predict(
    text=request.text,
    backend=request.backend or auto_select_backend()
)

# 5. Model strategy execution
model = ModelFactory.create_model(backend)

# 6. Cache check
cache_key = blake2b_hash(text + backend)
if cache_key in cache:
    return cached_result

# 7. Model inference
prediction = model.predict(text)

# 8. Cache update (LRU eviction if full)
cache[cache_key] = prediction

# 9. Response
{
  "label": "POSITIVE",
  "score": 0.9998,
  "inference_time_ms": 23.45,
  "backend": "onnx",
  "cached": false
}
```

---

## Deployment Topology

### Multi-Environment Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Development Environment                    │
│  Branch: develop  │  Namespace: mlops-sentiment-dev          │
│  Replicas: 1      │  Resources: 250m CPU, 256Mi RAM          │
│  HPA: Disabled    │  Monitoring: Basic                       │
└──────────────────────────────────────────────────────────────┘
                             ↓ (merge to main)
┌──────────────────────────────────────────────────────────────┐
│                    Staging Environment                        │
│  Branch: main     │  Namespace: mlops-sentiment-staging      │
│  Replicas: 2      │  Resources: 500m CPU, 512Mi RAM          │
│  HPA: 2-10 pods   │  Monitoring: Full stack                  │
└──────────────────────────────────────────────────────────────┘
                             ↓ (tag v*.*.*)
┌──────────────────────────────────────────────────────────────┐
│                   Production Environment                      │
│  Tag: v*.*.*      │  Namespace: mlops-sentiment              │
│  Replicas: 3      │  Resources: 1000m CPU, 1Gi RAM           │
│  HPA: 3-20 pods   │  Monitoring: Enterprise + Alerting       │
│  PDB: minAvailable=2  │  Multi-AZ: 3 availability zones      │
└──────────────────────────────────────────────────────────────┘
```

### Kubernetes Resource Architecture

```yaml
# Core Resources
- Namespace         # Isolation boundary
- Deployment        # Application pods
- Service           # Internal load balancing
- Ingress           # External access
- ConfigMap         # Configuration data
- Secret            # Sensitive data (from Vault)
- HPA               # Horizontal autoscaling
- PDB               # Pod disruption budget
- NetworkPolicy     # Network segmentation

# Monitoring Stack
- ServiceMonitor    # Prometheus scraping
- PrometheusRule    # Alerting rules
- Grafana Dashboard # Visualization

# Security
- ServiceAccount    # Pod identity
- Role/RoleBinding  # RBAC permissions
- PodSecurityPolicy # Security constraints
```

---

## Technology Stack

### Core Technologies

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Language** | Python | 3.11+ | Runtime environment |
| **Web Framework** | FastAPI | 0.104+ | Async API with OpenAPI |
| **ASGI Server** | Uvicorn | 0.24+ | Production ASGI server |
| **ML Framework** | Transformers | 4.35+ | Hugging Face models |
| **Deep Learning** | PyTorch | 2.1+ | Model training/inference |
| **Optimization** | ONNX Runtime | 1.16+ | Optimized inference |
| **Validation** | Pydantic | 2.4+ | Data validation |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Containerization** | Docker | Application packaging |
| **Orchestration** | Kubernetes | Container management |
| **Service Mesh** | Linkerd/Istio | Service-to-service communication |
| **Ingress** | NGINX/Traefik | HTTP routing |
| **Registry** | ghcr.io | Container image storage |

### Observability

| Pillar | Technology | Purpose |
|--------|-----------|---------|
| **Metrics** | Prometheus | Time-series metrics |
| **Visualization** | Grafana | Dashboards |
| **Logging** | Loki/ELK | Centralized logs |
| **Tracing** | Jaeger/Zipkin | Distributed tracing |
| **Alerting** | Alertmanager | Alert routing |

### Security

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Secrets** | HashiCorp Vault | Secret management |
| **TLS** | cert-manager | Certificate management |
| **Scanning** | Trivy | Vulnerability scanning |
| **SAST** | CodeQL | Code analysis |
| **Network** | Cilium/Calico | Network policies |

---

## Security Architecture

### Defense in Depth

```
┌────────────────────────────────────────────────────────┐
│  Layer 1: Network Security                             │
│  - Ingress TLS termination                             │
│  - Network policies (pod-to-pod restrictions)          │
│  - Private subnets for worker nodes                    │
└────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────┐
│  Layer 2: Application Security                         │
│  - API key authentication                              │
│  - Rate limiting (1000 req/min per client)             │
│  - Input validation (Pydantic schemas)                 │
│  - CORS configuration (explicit origins)               │
└────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────┐
│  Layer 3: Container Security                           │
│  - Non-root user (UID 1000)                            │
│  - Read-only root filesystem                           │
│  - Dropped capabilities                                │
│  - Resource limits                                     │
└────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────┐
│  Layer 4: Data Security                                │
│  - Secrets in Vault (not env vars)                     │
│  - Encryption at rest (PV encryption)                  │
│  - Encryption in transit (mTLS)                        │
│  - PII masking in logs                                 │
└────────────────────────────────────────────────────────┘
```

### Secret Management

```
Vault Architecture:
┌──────────────────┐
│  Kubernetes Auth │
│  (Service Acc)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐       ┌───────────────────┐
│  Vault Server    │──────▶│  Secrets Engine   │
│  (HA Cluster)    │       │  - KV v2          │
└────────┬─────────┘       │  - Transit        │
         │                 └───────────────────┘
         ▼
┌──────────────────┐
│  App Pod         │
│  - Init container│
│  - Vault Agent   │
│  - Sidecar       │
└──────────────────┘
```

---

## Scalability & Performance

### Horizontal Pod Autoscaling

```yaml
# Production HPA Configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

### Caching Strategy

```python
# Multi-Level Caching

Level 1: In-Memory LRU Cache (FastAPI Process)
- Size: 1000 predictions
- TTL: No expiration (LRU eviction)
- Hit Rate: ~80-85%
- Latency: ~1ms

Level 2: Redis (Shared Across Pods) [Optional Future]
- Size: 100k predictions
- TTL: 1 hour
- Hit Rate: ~60-70%
- Latency: ~5-10ms

Level 3: Model Cache (Persistent Volume)
- Size: Model weights (~268MB PyTorch, ~67MB ONNX)
- Warm on startup
- Shared across pods via ReadOnlyMany PV
```

### Performance Benchmarks

| Metric | PyTorch | ONNX | Target |
|--------|---------|------|--------|
| **p50 Latency** | 42ms | 18ms | <50ms |
| **p95 Latency** | 85ms | 32ms | <100ms |
| **p99 Latency** | 145ms | 58ms | <150ms |
| **Throughput** | 1200 req/s | 2400 req/s | >1000 req/s |
| **Memory/Pod** | 800MB | 400MB | <1GB |
| **CPU/Pod** | 0.8 cores | 0.4 cores | <1 core |
| **Cold Start** | 2.8s | 1.2s | <3s |

---

## Observability & Monitoring

### Three Pillars Implementation

#### 1. Metrics (Prometheus)

```python
# Custom Metrics Collection
ml_predictions_total           # Counter - Total predictions
ml_prediction_duration_seconds # Histogram - Latency distribution
ml_model_accuracy              # Gauge - Model performance
ml_data_drift_score            # Gauge - Data quality
ml_cache_hit_ratio             # Gauge - Cache effectiveness
ml_prediction_errors_total     # Counter - Error tracking
ml_model_memory_bytes          # Gauge - Resource usage
```

#### 2. Logs (Structured JSON)

```json
{
  "timestamp": "2025-10-21T14:53:42.123Z",
  "level": "INFO",
  "correlation_id": "abc123-def456-ghi789",
  "service": "mlops-sentiment",
  "version": "1.0.0",
  "component": "prediction_service",
  "message": "Prediction completed",
  "context": {
    "text_length": 42,
    "backend": "onnx",
    "inference_time_ms": 23.45,
    "cached": false,
    "label": "POSITIVE",
    "score": 0.9998
  }
}
```

#### 3. Traces (OpenTelemetry) [Future]

```
Trace: POST /api/v1/predict
├─ Span: http.request (102ms)
│  ├─ Span: authentication (5ms)
│  ├─ Span: cache.lookup (2ms)
│  ├─ Span: model.inference (85ms)
│  │  ├─ Span: tokenization (12ms)
│  │  ├─ Span: forward_pass (65ms)
│  │  └─ Span: postprocessing (8ms)
│  └─ Span: cache.update (3ms)
└─ Span: response.serialize (7ms)
```

### Alerting Rules

```yaml
# Critical Alerts (PagerDuty)
- High error rate (>1% for 5 min)
- Service unavailable (0 healthy pods)
- p99 latency >500ms for 10 min
- Model accuracy drop >10%
- Vault connectivity lost

# Warning Alerts (Slack)
- High memory usage (>85%)
- High CPU usage (>80%)
- Cache hit rate <70%
- Slow inference (p95 >100ms)
- Pod restarts >3 in 1 hour
```

---

## Disaster Recovery

### Backup Strategy

```
Component          Backup Method           Frequency    Retention
─────────────────  ──────────────────────  ───────────  ─────────
Model Weights      S3 versioning           On update    Forever
Configuration      Git + Vault             On change    Forever
Metrics            Prometheus snapshots    Daily        30 days
Logs               Archive to S3           Daily        90 days
Secrets            Vault snapshots         Daily        90 days (encrypted)
```

### Recovery Objectives

- **RPO (Recovery Point Objective)**: 5 minutes
- **RTO (Recovery Time Objective)**: 15 minutes
- **MTTR (Mean Time To Recovery)**: <30 minutes
- **Availability Target**: 99.9% (43 minutes downtime/month)

### Failover Procedures

1. **Pod Failure**: Automatic (Kubernetes liveness probes + HPA)
2. **Node Failure**: Automatic (pod rescheduling to healthy nodes)
3. **Zone Failure**: Automatic (multi-AZ deployment)
4. **Region Failure**: Manual (requires DNS failover)

---

## Future Enhancements

### Short Term (Q1 2026)

- [ ] MLflow Model Registry integration
- [ ] Advanced A/B testing framework
- [ ] Redis distributed caching layer
- [ ] GraphQL API support
- [ ] Enhanced data drift detection

### Medium Term (Q2 2026)

- [ ] Multi-model ensemble serving
- [ ] Real-time model retraining pipeline
- [ ] Advanced anomaly detection
- [ ] Cost optimization with spot instances
- [ ] Multi-region deployment

### Long Term (Q3+ 2026)

- [ ] AutoML model selection
- [ ] Federated learning support
- [ ] Edge deployment (K3s/KubeEdge)
- [ ] gRPC API for high-performance clients
- [ ] Advanced security (SPIFFE/SPIRE)

---

## Related Documentation

- [Development Guide](docs/setup/DEVELOPMENT.md) - Local development setup
- [Deployment Guide](DEPLOYMENT.md) - Production deployment
- [Kubernetes Guide](docs/KUBERNETES.md) - K8s-specific documentation
- [Monitoring Guide](docs/MONITORING.md) - Observability setup
- [CI/CD Guide](CICD.md) - Pipeline configuration
- [Code Quality](CODE_QUALITY_SETUP.md) - Linting and testing
- [API Reference](openapi-specs/sentiment-api.yaml) - OpenAPI specification

---

**Document Maintainer**: MLOps Team  
**Review Cycle**: Quarterly  
**Next Review**: January 2026
