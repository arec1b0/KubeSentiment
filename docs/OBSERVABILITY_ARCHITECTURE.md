# KubeSentiment Observability Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          KubeSentiment Application                       │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        FastAPI Application                        │  │
│  │                                                                    │  │
│  │  ├─ Sentiment Analysis Endpoints                                 │  │
│  │  ├─ Model Inference Pipeline                                     │  │
│  │  ├─ Async Batch Processing                                       │  │
│  │  ├─ Kafka Stream Processing                                      │  │
│  │  └─ Redis Caching Layer                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│         │                    │                    │                      │
│         │                    │                    │                      │
│  ┌──────▼────────┐   ┌──────▼────────┐   ┌──────▼────────┐           │
│  │  Prometheus   │   │  OpenTelemetry│   │   Structlog   │           │
│  │    Client     │   │    Tracing    │   │    Logging    │           │
│  │   (Metrics)   │   │   (Traces)    │   │    (Logs)     │           │
│  └───────────────┘   └───────────────┘   └───────────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Prometheus    │  │     Jaeger      │  │   Logstash      │
│   :9090         │  │    :16686       │  │    :5000        │
│                 │  │                 │  │                 │
│ • Scrapes /metrics│ • Receives spans │ • Processes JSON │
│ • Stores TSDB   │  │ • Trace storage │  │ • Enriches logs │
│ • Evaluates rules│ • Trace queries  │  │ • Adds tags     │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         │                    │                    │
         ▼                    │                    ▼
┌─────────────────┐           │           ┌─────────────────┐
│  AlertManager   │           │           │ Elasticsearch   │
│    :9093        │           │           │    :9200        │
│                 │           │           │                 │
│ • Routes alerts │           │           │ • Indexes logs  │
│ • Groups alerts │           │           │ • Full-text     │
│ • Sends notifs  │           │           │   search        │
└────────┬────────┘           │           └────────┬────────┘
         │                    │                    │
         │                    │                    │
         ▼                    │                    ▼
┌─────────────────┐           │           ┌─────────────────┐
│  Slack/Email/   │           │           │     Kibana      │
│   PagerDuty     │           │           │     :5601       │
│                 │           │           │                 │
│ • Critical: PD  │           │           │ • Log dashboards│
│ • Warning: Slack│           │           │ • Search UI     │
│ • Info: Email   │           │           │ • Visualizations│
└─────────────────┘           │           └─────────────────┘
                              │
                              │
         ┌────────────────────┴────────────────────┐
         │                                          │
         ▼                                          ▼
┌─────────────────┐                       ┌─────────────────┐
│    Grafana      │                       │      Loki       │
│    :3000        │                       │     :3100       │
│                 │                       │                 │
│ • 3 Dashboards  │◄──────────────────────┤ • Log storage   │
│   - Advanced    │                       │ • Label index   │
│   - Business    │                       │ • Lightweight   │
│   - Vault       │                       └─────────────────┘
│                 │                                ▲
│ • Prometheus DS │                                │
│ • Jaeger DS     │                                │
│ • Loki DS       │                       ┌────────┴────────┐
│ • Elasticsearch │                       │    Promtail     │
└─────────────────┘                       │                 │
                                          │ • Log shipping  │
                                          │ • Docker SD     │
                                          │ • Auto-labeling │
                                          └─────────────────┘
```

## Data Flow

### 1. Metrics Flow (Prometheus)

```
Application → Prometheus Client → /metrics endpoint
                                        ↓
                                   Prometheus
                                  (scrape every 15s)
                                        ↓
                              ┌─────────┴─────────┐
                              │                   │
                              ▼                   ▼
                         Recording Rules    Alerting Rules
                              ↓                   ↓
                           Grafana         AlertManager
                         (Dashboards)      (Notifications)
```

**Metrics Collected:**
- Request rate, latency, errors
- Model inference time, confidence
- Resource utilization (CPU, memory, GPU)
- Cache hit rates
- Kafka lag, throughput

### 2. Traces Flow (OpenTelemetry → Jaeger)

```
Application → OpenTelemetry SDK
                    ↓
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
      Jaeger     Zipkin      OTLP
    (Thrift)     (JSON)    (gRPC)
         │          │          │
         └──────────┼──────────┘
                    ↓
              Jaeger Storage
                    ↓
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
    Jaeger UI   Grafana   Trace Query API
```

**Traces Captured:**
- HTTP requests (FastAPI)
- External API calls (httpx, requests)
- Database operations (Redis)
- Model inference
- Feature engineering
- Batch processing

### 3. Logs Flow (Structured Logging → ELK/Loki)

```
Application → Structlog (JSON)
                    ↓
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
    Logstash    Promtail   Filebeat
         │          │          │
         │          │          │
         ▼          ▼          │
  Elasticsearch   Loki        │
         │          │          │
         ▼          ▼          ▼
     Kibana    Grafana   Elasticsearch
```

**Log Enrichment:**
- Correlation ID injection
- Trace ID linking
- Geoip lookup
- Tag categorization
- Metric extraction

## Component Responsibilities

### Application Layer

| Component | Responsibility | Output |
|-----------|---------------|--------|
| **Prometheus Client** | Expose metrics | HTTP /metrics endpoint |
| **OpenTelemetry SDK** | Create spans | Traces to Jaeger |
| **Structlog** | Format logs | JSON logs to Logstash/Loki |
| **Correlation Middleware** | Track requests | correlation_id in logs/traces |

### Collection Layer

| Component | Port | Purpose |
|-----------|------|---------|
| **Prometheus** | 9090 | Scrape and store metrics |
| **Jaeger Collector** | 14268, 4317 | Receive and store traces |
| **Logstash** | 5000, 5044 | Process and enrich logs |
| **Promtail** | 9080 | Ship logs to Loki |

### Storage Layer

| Component | Port | Storage Type |
|-----------|------|-------------|
| **Prometheus TSDB** | - | Time-series metrics |
| **Jaeger Storage** | - | Distributed traces |
| **Elasticsearch** | 9200 | Full-text logs |
| **Loki** | 3100 | Label-indexed logs |

### Visualization Layer

| Component | Port | Features |
|-----------|------|----------|
| **Grafana** | 3000 | Unified dashboards |
| **Jaeger UI** | 16686 | Trace exploration |
| **Kibana** | 5601 | Log analytics |
| **Prometheus UI** | 9090 | Metric queries |

### Alerting Layer

| Component | Port | Purpose |
|-----------|------|---------|
| **AlertManager** | 9093 | Route alerts to channels |
| **Prometheus Rules** | - | Define alert conditions |

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network: observability             │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │  sentiment-  │      │  prometheus  │      │  grafana  │ │
│  │     api      ├─────►│    :9090     ├─────►│   :3000   │ │
│  │   :8000      │      └──────────────┘      └───────────┘ │
│  └──────┬───────┘                                            │
│         │                                                     │
│         │              ┌──────────────┐                      │
│         ├─────────────►│   jaeger     │                      │
│         │              │  :16686      │                      │
│         │              └──────────────┘                      │
│         │                                                     │
│         │              ┌──────────────┐      ┌───────────┐  │
│         └─────────────►│  logstash    ├─────►│elasticsearch│
│                        │   :5000      │      │   :9200   │  │
│                        └──────────────┘      └───────┬───┘  │
│                                                       │      │
│                                              ┌────────▼────┐ │
│                                              │   kibana    │ │
│                                              │   :5601     │ │
│                                              └─────────────┘ │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │  promtail    ├─────►│    loki      ├──────┐              │
│  │              │      │   :3100      │      │              │
│  └──────────────┘      └──────────────┘      │              │
│                                               │              │
│  ┌──────────────┐      ┌──────────────┐      │              │
│  │alertmanager  │◄─────┤ prometheus   │      │              │
│  │   :9093      │      │              │      │              │
│  └──────┬───────┘      └──────────────┘      │              │
│         │                                     │              │
│         │                                     │              │
│         ▼                                     ▼              │
│  ┌──────────────┐              ┌──────────────────────────┐ │
│  │ Slack/Email  │              │       grafana            │ │
│  │  PagerDuty   │              │  (Multiple Datasources)  │ │
│  └──────────────┘              └──────────────────────────┘ │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │node-exporter │─────►│  prometheus  │                     │
│  │   :9100      │      │              │                     │
│  └──────────────┘      └──────────────┘                     │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │  cadvisor    │─────►│  prometheus  │                     │
│  │   :8080      │      │              │                     │
│  └──────────────┘      └──────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

## Correlation Architecture

### Request Lifecycle with Observability

```
1. Request arrives → CorrelationIdMiddleware
                     ├─ Generates correlation_id
                     ├─ Sets in context
                     └─ Adds to response headers

2. Logging → Structlog
             ├─ Reads correlation_id from context
             ├─ Adds to every log entry
             └─ Outputs JSON with correlation_id

3. Tracing → OpenTelemetry
             ├─ Creates span with trace_id
             ├─ Links trace_id = correlation_id
             └─ Sends to Jaeger

4. Metrics → Prometheus
             ├─ Increments counters
             ├─ Records histograms
             └─ Tagged with labels

5. Response → Client
              ├─ X-Correlation-ID header
              └─ Status and body
```

### Correlation Example

**Request ID:** `abc-123-def-456`

**Metrics:**
```
sentiment_requests_total{endpoint="/predict",status="200"} 1
sentiment_request_duration_seconds{endpoint="/predict"} 0.045
```

**Trace:**
```
Trace ID: abc-123-def-456
├─ Span: POST /predict (45ms)
│  ├─ Span: Model Inference (40ms)
│  │  ├─ Span: Tokenization (5ms)
│  │  └─ Span: Forward Pass (35ms)
│  └─ Span: Redis Cache Check (5ms)
```

**Logs:**
```json
{
  "event": "API request completed",
  "correlation_id": "abc-123-def-456",
  "trace_id": "abc-123-def-456",
  "http_method": "POST",
  "http_path": "/predict",
  "http_status": 200,
  "duration_ms": 45.2,
  "model_name": "distilbert",
  "confidence": 0.95
}
```

## Scalability Considerations

### Horizontal Scaling

```
┌─────────────────────────────────────────────────────┐
│              Load Balancer (K8s Ingress)             │
└────────────┬────────────┬────────────┬──────────────┘
             │            │            │
             ▼            ▼            ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐
    │ API Pod 1 │  │ API Pod 2 │  │ API Pod 3 │
    └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
          │              │              │
          └──────────────┼──────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Prometheus          │
              │  (Service Discovery) │
              └──────────────────────┘
```

**All pods expose:**
- `/metrics` endpoint (scraped by Prometheus)
- Traces sent to Jaeger (via agent)
- Logs shipped to Logstash/Loki

### High Availability

**Prometheus:**
- Multiple Prometheus instances
- Thanos for long-term storage
- Remote write to durable storage

**Jaeger:**
- Distributed deployment
- Elasticsearch/Cassandra backend
- Query service scaling

**ELK Stack:**
- Elasticsearch cluster
- Logstash cluster
- Kibana replicas

## Security Architecture

### Authentication Flow

```
Client Request
      ↓
API Key Middleware
      ↓
┌─────────────────┐
│ Valid API Key?  │
└────┬─────────┬──┘
     No        Yes
     │         │
     ▼         ▼
  401      Continue
            Processing
                ↓
        Security Logs
   (tagged, monitored)
                ↓
        AlertManager
       (if threshold)
```

### Secrets Management

```
Application
     ↓
HashiCorp Vault
     ↓
┌─────────────────────┐
│ Vault Metrics       │
│ - Auth attempts     │
│ - Secret access     │
│ - Token renewals    │
└──────────┬──────────┘
           │
           ▼
    Vault Dashboard
    (Grafana)
           │
           ▼
    Vault Alerts
    (AlertManager)
```

## Monitoring Strategy

### Golden Signals

**Latency:**
- P50, P95, P99 response times
- Inference duration
- Cache lookup time

**Traffic:**
- Requests per second
- Batch size
- Kafka throughput

**Errors:**
- HTTP 4xx/5xx rates
- Model errors
- Cache failures

**Saturation:**
- CPU/Memory usage
- Queue depth
- Connection pool utilization

### SLOs/SLIs

| Service Level Indicator | Target | Alert Threshold |
|------------------------|--------|----------------|
| Availability | 99.9% | < 99.9% for 5m |
| P95 Latency | < 200ms | > 200ms for 10m |
| Error Rate | < 0.1% | > 0.1% for 5m |
| ML Confidence | > 80% | < 80% for 15m |

## Cost Optimization

### Resource Allocation

```
Component         CPU    Memory   Storage   Priority
─────────────────────────────────────────────────────
Application       2 core  4GB      -        High
Prometheus        1 core  2GB      100GB    High
Grafana           0.5 core 1GB     10GB     High
Jaeger            1 core  2GB      50GB     Medium
Elasticsearch     2 core  4GB      200GB    Medium
Logstash          1 core  2GB      -        Medium
Kibana            0.5 core 1GB     -        Low
Loki (alt)        0.5 core 1GB     50GB     Medium
AlertManager      0.5 core 512MB   1GB      High
```

### Cost vs Features

**Full Stack (ELK + Jaeger):**
- Cost: ~10 cores, ~20GB RAM, ~360GB storage
- Features: Full-featured log search, rich analytics

**Lightweight (Loki + Jaeger):**
- Cost: ~6 cores, ~12GB RAM, ~200GB storage
- Features: Label-based log search, trace analysis

## Conclusion

The observability architecture provides:

✅ **Complete Visibility** - Metrics, logs, traces
✅ **Proactive Monitoring** - Alerts before issues
✅ **Fast Debugging** - Correlated data
✅ **Performance Insights** - Optimization opportunities
✅ **Business Intelligence** - Usage analytics
✅ **Production Ready** - Scalable and secure

---

**Reference:** See `docs/OBSERVABILITY_GUIDE.md` for implementation details.

