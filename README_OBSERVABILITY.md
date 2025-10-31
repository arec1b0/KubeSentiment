# KubeSentiment Observability Integration

## Quick Start

Start the complete observability stack in under 2 minutes:

```bash
# Start all observability services
make observability

# Or using docker-compose directly
docker-compose -f docker-compose.observability.yml up -d
```

Access the dashboards:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **Jaeger** | http://localhost:16686 | - |
| **Kibana** | http://localhost:5601 | - |
| **AlertManager** | http://localhost:9093 | - |

## What's Included

### 📊 Metrics (Prometheus + Grafana)

- **3 Pre-configured Dashboards:**
  - Advanced MLOps Dashboard (SLOs, latency, resource usage)
  - Business Metrics Dashboard (throughput, confidence, predictions)
  - Vault Secrets Dashboard (authentication, rotation, access patterns)

- **Recording Rules:** Pre-aggregated metrics for performance
- **Custom Metrics:** ML-specific metrics (inference time, confidence, text length)

### 🔍 Distributed Tracing (Jaeger + OpenTelemetry)

- **Automatic Instrumentation:**
  - FastAPI requests/responses
  - HTTP client calls (httpx, requests)
  - Redis operations
  - Logging correlation

- **Multiple Backends Supported:**
  - Jaeger (default)
  - Zipkin
  - OTLP (OpenTelemetry Protocol)
  - Console (debugging)

- **Features:**
  - Request flow visualization
  - Performance bottleneck identification
  - Error propagation tracking
  - Log-trace correlation

### 📝 Log Aggregation (ELK Stack + Loki)

**ELK Stack (Full-featured):**
- Elasticsearch for storage and indexing
- Logstash for processing and enrichment
- Kibana for visualization

**Loki + Promtail (Lightweight):**
- Loki for log aggregation
- Promtail for log shipping
- Grafana integration for unified view

**Features:**
- Structured JSON logging
- Automatic log correlation (correlation_id, trace_id)
- Geoip enrichment
- Security event tagging
- Performance metric extraction

### 🚨 Alerting (AlertManager)

- **SLO-Based Alerts:** Availability, latency, model quality
- **Business Logic Alerts:** Traffic patterns, model drift
- **Infrastructure Alerts:** Node health, storage, network
- **Predictive Alerts:** Disk/memory exhaustion forecasting
- **Vault Alerts:** Authentication, secrets, rotation

**Notification Channels:**
- Slack (real-time)
- Email (detailed reports)
- PagerDuty (critical escalation)

## Configuration

### Environment Variables

```bash
# Distributed Tracing
MLOPS_ENABLE_TRACING=true
MLOPS_TRACING_BACKEND=jaeger  # jaeger, zipkin, otlp, console
MLOPS_SERVICE_NAME=sentiment-analysis-api
MLOPS_ENVIRONMENT=production

# Jaeger
MLOPS_JAEGER_AGENT_HOST=jaeger
MLOPS_JAEGER_AGENT_PORT=6831

# Zipkin
MLOPS_ZIPKIN_ENDPOINT=http://zipkin:9411

# OTLP
MLOPS_OTLP_ENDPOINT=jaeger:4317

# Metrics
MLOPS_ENABLE_METRICS=true
MLOPS_METRICS_CACHE_TTL=5

# Logging
MLOPS_LOG_LEVEL=INFO
```

### Docker Compose

The observability stack includes:

```yaml
services:
  - prometheus      # Metrics collection
  - grafana         # Visualization
  - alertmanager    # Alert routing
  - jaeger          # Distributed tracing
  - elasticsearch   # Log storage
  - logstash        # Log processing
  - kibana          # Log visualization
  - loki            # Lightweight logs
  - promtail        # Log shipping
  - node-exporter   # Host metrics
  - cadvisor        # Container metrics
```

## Architecture

```
Application (FastAPI)
├── Metrics → Prometheus → Grafana → AlertManager
├── Traces → OpenTelemetry → Jaeger → Grafana
└── Logs → Logstash → Elasticsearch → Kibana
         └→ Promtail → Loki → Grafana
```

## Usage Examples

### Custom Tracing

```python
from app.core.tracing import traced_operation, add_span_attributes

with traced_operation("custom_ml_operation", model_name="distilbert"):
    result = ml_model.predict(data)
    add_span_attributes(
        prediction_count=len(result),
        confidence=result.confidence
    )
```

### Structured Logging

```python
from app.core.logging import get_logger

logger = get_logger(__name__)
logger.info(
    "Model prediction completed",
    model_name="distilbert",
    inference_time_ms=45.2,
    confidence=0.95,
    text_length=128
)
```

### Custom Metrics

```python
from app.monitoring.prometheus import (
    record_inference_duration,
    record_prediction_metrics
)

start_time = time.time()
prediction = model.predict(text)
duration = time.time() - start_time

record_inference_duration(duration)
record_prediction_metrics(prediction.score, len(text))
```

## Monitoring Best Practices

### 1. **Metrics**
- Use histograms for latency
- Use gauges for current state
- Use counters for events
- Label cardinality matters

### 2. **Tracing**
- Trace business-critical paths
- Add custom attributes for context
- Record exceptions
- Set span status appropriately

### 3. **Logging**
- Always use structured logging
- Include correlation IDs
- Use appropriate log levels
- Add contextual information

### 4. **Alerting**
- Define clear SLOs
- Avoid alert fatigue
- Use inhibition rules
- Configure smart routing

## Kubernetes Deployment

Deploy to Kubernetes using Helm:

```bash
# Create monitoring namespace
kubectl create namespace monitoring

# Apply Prometheus rules
kubectl apply -f config/prometheus-rules.yaml -n monitoring

# Apply AlertManager config
kubectl apply -f config/alertmanager-config.yaml -n monitoring

# Deploy kube-prometheus-stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring

# Deploy Jaeger
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm install jaeger jaegertracing/jaeger -n monitoring
```

## Performance Impact

Observability overhead:

| Component | CPU Impact | Memory Impact | Network Impact |
|-----------|-----------|---------------|----------------|
| Prometheus Metrics | <1% | ~10MB | <1KB/req |
| Distributed Tracing (sampled 10%) | <2% | ~20MB | ~2KB/req |
| Structured Logging | <1% | ~5MB | ~1KB/req |
| **Total** | **<4%** | **~35MB** | **~4KB/req** |

## Troubleshooting

### Metrics not appearing?
```bash
# Check Prometheus targets
curl http://localhost:9090/targets

# Verify /metrics endpoint
curl http://localhost:8000/metrics
```

### Traces not in Jaeger?
```bash
# Check tracing configuration
docker logs sentiment-api | grep tracing

# Verify Jaeger connectivity
docker logs jaeger
```

### Logs not in Elasticsearch?
```bash
# Check Logstash pipeline
curl http://localhost:9600/_node/stats

# Verify Elasticsearch health
curl http://localhost:9200/_cluster/health
```

## Stop Observability Stack

```bash
# Stop all services
make observability-down

# Or using docker-compose
docker-compose -f docker-compose.observability.yml down

# Remove volumes
docker-compose -f docker-compose.observability.yml down -v
```

## Documentation

- **Complete Guide:** [docs/OBSERVABILITY_GUIDE.md](docs/OBSERVABILITY_GUIDE.md)
- **Prometheus Rules:** [config/prometheus-rules.yaml](config/prometheus-rules.yaml)
- **AlertManager Config:** [config/alertmanager-config.yaml](config/alertmanager-config.yaml)
- **Grafana Dashboards:** [config/grafana-*.json](config/)

## Links

- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)
- [Jaeger](https://www.jaegertracing.io/)
- [OpenTelemetry](https://opentelemetry.io/)
- [Elastic Stack](https://www.elastic.co/)
- [Loki](https://grafana.com/oss/loki/)

---

**Questions?** See [docs/OBSERVABILITY_GUIDE.md](docs/OBSERVABILITY_GUIDE.md) for detailed documentation.

