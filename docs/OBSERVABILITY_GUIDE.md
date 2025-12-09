# KubeSentiment Observability Guide

## Overview

This guide provides comprehensive documentation for the observability stack integrated into KubeSentiment. The stack follows MLOps best practices and implements the three pillars of observability: **Metrics**, **Logs**, and **Traces**.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Metrics with Prometheus & Grafana](#metrics-with-prometheus--grafana)
3. [Distributed Tracing with Jaeger/Zipkin](#distributed-tracing-with-jaegerzipkin)
4. [Log Aggregation with ELK Stack](#log-aggregation-with-elk-stack)
5. [Alerting with AlertManager](#alerting-with-alertmanager)
6. [Quick Start](#quick-start)
7. [Configuration](#configuration)
8. [Best Practices](#best-practices)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   KubeSentiment Application                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ FastAPI  │  │Structured│  │OpenTelem.│  │Prometheus│   │
│  │   App    │→ │  Logging │→ │ Tracing  │→ │  Client  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Prometheus  │ │  Logstash    │ │    Jaeger    │ │  Loki        │
│  (Metrics)   │ │  (Log Proc.) │ │  (Tracing)   │ │  (Logs)      │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Grafana    │ │Elasticsearch │ │Grafana+Tempo │ │   Grafana    │
│ (Dashboards) │ │  (Storage)   │ │     (UI)     │ │ (Logs View)  │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
         │              │
         ▼              ▼
┌──────────────┐ ┌──────────────┐
│AlertManager  │ │    Kibana    │
│  (Alerts)    │ │  (Log UI)    │
└──────────────┘ └──────────────┘
```

## Metrics with Prometheus & Grafana

### Available Metrics

The application exposes Prometheus-compatible metrics at `/metrics`:

#### Request Metrics
- `sentiment_requests_total` - Total number of requests by endpoint, method, and status code
- `sentiment_request_duration_seconds` - Request duration histogram
- `sentiment_active_requests` - Current number of active requests

#### Model Metrics
- `sentiment_model_loaded` - Model loading status (1=loaded, 0=not loaded)
- `sentiment_inference_duration_seconds` - Model inference duration histogram
- `sentiment_prediction_score` - Distribution of prediction confidence scores
- `sentiment_text_length_characters` - Distribution of input text lengths

#### System Metrics
- `sentiment_torch_version` - PyTorch version information
- `sentiment_cuda_available` - CUDA availability status
- `sentiment_cuda_memory_allocated_bytes` - CUDA memory allocated
- `sentiment_cuda_memory_reserved_bytes` - CUDA memory reserved

### Grafana Dashboards

Three pre-configured Grafana dashboards are available:

#### 1. Advanced MLOps Dashboard
**Location:** `config/grafana-advanced-dashboard.json`

Features:
- Service availability SLO monitoring (99.9% target)
- Request latency percentiles (p50, p95, p99)
- Active alerts panel
- Request rate by status code
- ML prediction confidence tracking
- CPU and memory utilization by pod
- Error rate distribution

#### 2. Business Metrics Dashboard
**Location:** `config/grafana-business-metrics-dashboard.json`

Features:
- Real-time prediction throughput
- Model confidence score gauge
- Daily prediction volume
- Average inference time
- Request status distribution pie chart
- Request duration percentiles
- Text length distribution
- Concurrent active requests

#### 3. Vault Secrets Dashboard
**Location:** `config/grafana-vault-dashboard.json`

Features:
- Vault health and availability
- Secret access patterns
- Authentication metrics
- Token management
- Secret rotation tracking

### Accessing Grafana

1. Start the observability stack:
   ```bash
   docker-compose -f docker-compose.observability.yml up -d
   ```

2. Access Grafana at `http://localhost:3000`
   - Default credentials: `admin/admin`

3. Navigate to Dashboards → Browse to see all available dashboards

## Distributed Tracing with Jaeger/Zipkin

### OpenTelemetry Integration

The application uses OpenTelemetry for vendor-neutral distributed tracing. It supports multiple backends:

- **Jaeger** (default) - Complete tracing solution with UI
- **Zipkin** - Alternative tracing backend
- **OTLP** - OpenTelemetry Protocol for vendor-neutral export
- **Console** - Debug mode for local development

### Configuration

Set tracing options via environment variables:

```bash
# Enable/disable tracing
MLOPS_ENABLE_TRACING=true

# Choose backend: jaeger, zipkin, otlp, or console
MLOPS_TRACING_BACKEND=jaeger

# Service identification
MLOPS_SERVICE_NAME=sentiment-analysis-api
MLOPS_ENVIRONMENT=production

# Jaeger configuration
MLOPS_JAEGER_AGENT_HOST=jaeger
MLOPS_JAEGER_AGENT_PORT=6831

# Zipkin configuration
MLOPS_ZIPKIN_ENDPOINT=http://zipkin:9411

# OTLP configuration
MLOPS_OTLP_ENDPOINT=jaeger:4317

# Exclude specific URLs from tracing
MLOPS_TRACING_EXCLUDED_URLS=/health,/metrics,/docs
```

### Automatic Instrumentation

The following libraries are automatically instrumented:

- **FastAPI** - All HTTP requests and responses
- **HTTPX** - Outgoing HTTP client requests
- **Requests** - Outgoing HTTP requests
- **Redis** - Cache operations
- **Logging** - Correlation between logs and traces

### Manual Instrumentation

Use the `traced_operation` context manager for custom spans:

```python
from app.core.tracing import traced_operation, add_span_attributes

with traced_operation("my_operation", user_id="123", model="distilbert"):
    # Your code here
    result = perform_operation()
    add_span_attributes(result_size=len(result))
```

### Accessing Jaeger UI

1. Navigate to `http://localhost:16686`
2. Select service `sentiment-analysis-api`
3. Click "Find Traces" to view distributed traces
4. Examine trace details including:
   - Request flow through components
   - Timing breakdown
   - Error propagation
   - Logs correlation

## Log Aggregation with ELK Stack

### Structured Logging

The application uses `structlog` for JSON-formatted structured logging:

```json
{
  "event": "API request completed",
  "timestamp": "2024-10-31T12:00:00.000Z",
  "level": "info",
  "service": "sentiment-analysis",
  "version": "1.0.0",
  "correlation_id": "abc123",
  "trace_id": "abc123",
  "http_method": "POST",
  "http_path": "/predict",
  "http_status": 200,
  "duration_ms": 45.2
}
```

### ELK Stack Components

#### Elasticsearch
- **Purpose:** Log storage and indexing
- **Port:** 9200
- **Index Pattern:** `mlops-logs-YYYY.MM.DD`

#### Logstash
- **Purpose:** Log processing and enrichment
- **Ports:** 5000 (TCP/UDP), 5044 (Beats)
- **Configuration:** `config/logstash.conf`

Features:
- JSON log parsing
- Geoip enrichment
- Tag-based categorization
- Metric calculation
- Error and security event tagging

#### Kibana
- **Purpose:** Log visualization and analysis
- **Port:** 5601
- **Access:** `http://localhost:5601`

### Loki + Promtail (Lightweight Alternative)

For resource-constrained environments, use Loki instead of ELK:

- **Loki:** Log aggregation (Port 3100)
- **Promtail:** Log shipper with Docker integration
- **Configuration:** `config/loki-config.yaml`, `config/promtail-config.yaml`

### Log Correlation

Logs are automatically correlated with traces via:
- `correlation_id` - Unique request identifier
- `trace_id` - OpenTelemetry trace ID

In Grafana, click on a trace ID in logs to jump to the corresponding trace in Jaeger.

## Alerting with AlertManager

### Alert Configuration

AlertManager rules are defined in:
- **Prometheus Rules:** `config/monitoring/prometheus-rules.yaml`
- **AlertManager Config:** `config/alertmanager.yml`

### Alert Categories

#### 1. SLO-Based Alerts
- `MLOpsSLOAvailabilityBreach` - Availability < 99.9%
- `MLOpsSLOLatencyBreach` - P95 latency > 200ms
- `MLOpsSLOQualityBreach` - Prediction confidence < 80%

#### 2. Business Logic Alerts
- `MLOpsTrafficSpike` - 5x traffic increase
- `MLOpsTrafficDrop` - 80% traffic decrease
- `MLOpsPredictionPatternChange` - Model drift detected

#### 3. Infrastructure Alerts
- `MLOpsNodeNotReady` - Kubernetes node issues
- `MLOpsPVCPendingOrLost` - Storage problems
- `MLOpsNetworkPolicyViolation` - Security violations

#### 4. Predictive Alerts
- `MLOpsDiskSpaceExhaustionPredicted` - Disk space exhaustion in 4h
- `MLOpsMemoryExhaustionPredicted` - Memory exhaustion in 2h

#### 5. Vault Alerts
- `VaultDown` - Vault server unavailable
- `VaultSealed` - Vault is sealed
- `VaultAuthenticationFailures` - Authentication issues
- `VaultSecretsExpiringSoon` - Secrets expiring in 7 days

### Notification Channels

Configure notification channels in `config/alertmanager.yml`:

- **Slack** - Real-time team notifications
- **Email** - Detailed alert information
- **PagerDuty** - On-call escalation (critical alerts only)

Example Slack webhook configuration:

```yaml
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

receivers:
  - name: 'critical-alerts'
    slack_configs:
      - channel: '#critical-alerts'
        title: '🚨 CRITICAL MLOps Alert'
```

### Accessing AlertManager

1. Navigate to `http://localhost:9093`
2. View active alerts
3. Silence alerts if needed
4. Check notification status

## Quick Start

### Docker Compose Deployment

1. **Start the complete observability stack:**

```bash
# Start all observability services
docker-compose -f docker-compose.observability.yml up -d

# Verify services are running
docker-compose -f docker-compose.observability.yml ps

# View logs
docker-compose -f docker-compose.observability.yml logs -f
```

2. **Start the application:**

```bash
# Start with observability integration
docker-compose up -d

# Or start with full stack
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

3. **Access the dashboards:**

- **Grafana:** http://localhost:3000 (admin/admin)
- **Prometheus:** http://localhost:9090
- **Jaeger:** http://localhost:16686
- **Kibana:** http://localhost:5601
- **AlertManager:** http://localhost:9093

### Kubernetes Deployment

1. **Create monitoring namespace:**

```bash
kubectl create namespace monitoring
```

2. **Deploy Prometheus and Grafana:**

```bash
# Apply Prometheus rules
kubectl apply -f config/monitoring/prometheus-rules.yaml -n monitoring

# Apply AlertManager config
kubectl apply -f config/alertmanager-config.yaml -n monitoring

# Deploy using Helm (recommended)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
```

3. **Configure service monitors:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: sentiment-api-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: sentiment-api
  endpoints:
    - port: metrics
      path: /metrics
      interval: 30s
```

## Configuration

### Environment Variables

```bash
# Tracing
MLOPS_ENABLE_TRACING=true
MLOPS_TRACING_BACKEND=jaeger
MLOPS_SERVICE_NAME=sentiment-analysis-api
MLOPS_ENVIRONMENT=production

# Metrics
MLOPS_ENABLE_METRICS=true
MLOPS_METRICS_CACHE_TTL=5

# Logging
MLOPS_LOG_LEVEL=INFO
```

### Prometheus Configuration

Edit `config/monitoring/prometheus.yml` to add custom scrape targets:

```yaml
scrape_configs:
  - job_name: 'custom-service'
    static_configs:
      - targets: ['custom-service:8080']
```

### Grafana Provisioning

Add new dashboards to `config/` directory and mount in `docker-compose.observability.yml`:

```yaml
volumes:
  - ./config/my-dashboard.json:/etc/grafana/provisioning/dashboards/my-dashboard.json:ro
```

## Best Practices

### 1. Structured Logging
- Always use structured logging with `structlog`
- Include correlation IDs in all log entries
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Add contextual information (user_id, model_name, etc.)

### 2. Metric Naming
- Follow Prometheus naming conventions
- Use consistent naming patterns
- Include units in metric names (e.g., `_seconds`, `_bytes`)
- Use labels for dimensions, not metric names

### 3. Distributed Tracing
- Trace business-critical operations
- Add custom attributes for context
- Record exceptions in spans
- Set span status appropriately

### 4. Alert Fatigue Prevention
- Define clear SLOs and SLIs
- Use appropriate thresholds
- Implement alert inhibition rules
- Configure smart grouping and routing

### 5. Performance Considerations
- Use metric caching for high-frequency scrapes
- Limit trace sampling in high-traffic scenarios
- Use Loki instead of ELK for lower resource usage
- Enable log rotation and retention policies

### 6. Security
- Secure Grafana with strong passwords
- Use TLS for production deployments
- Implement RBAC for multi-tenant environments
- Audit access to sensitive metrics and logs

## Troubleshooting

### Metrics Not Appearing

1. Check Prometheus targets: `http://localhost:9090/targets`
2. Verify service is exposing `/metrics` endpoint
3. Check Prometheus scrape configuration
4. Review Prometheus logs for errors

### Traces Not Showing in Jaeger

1. Verify `MLOPS_ENABLE_TRACING=true`
2. Check Jaeger agent connectivity
3. Review application logs for tracing errors
4. Confirm correct tracing backend configuration

### Logs Not in Elasticsearch

1. Check Logstash is receiving logs: `curl localhost:9600/_node/stats`
2. Verify Elasticsearch is running: `curl localhost:9200/_cluster/health`
3. Review Logstash pipeline configuration
4. Check application is sending logs to correct port

### Alerts Not Firing

1. Verify AlertManager is running: `http://localhost:9093`
2. Check Prometheus rules are loaded: `http://localhost:9090/rules`
3. Review alert evaluation status in Prometheus
4. Confirm notification channel configuration

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [ELK Stack Documentation](https://www.elastic.co/guide/)
- [MLOps Best Practices](https://ml-ops.org/)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs
3. Open an issue on GitHub
4. Contact the MLOps team

---

**Last Updated:** October 31, 2024
**Version:** 1.0.0

