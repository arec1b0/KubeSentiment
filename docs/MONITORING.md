# Monitoring Guide

For monitoring setup and configuration, please see:

**[setup/QUICKSTART.md](setup/QUICKSTART.md)** - Includes full monitoring stack setup

## What You Get

The monitoring stack includes:
- **Prometheus** - Metrics collection and alerting
- **Grafana** - Dashboards and visualization
- **Alertmanager** - Alert routing and notifications
- **ServiceMonitor** - Automated metrics discovery

## Quick Setup

```bash
# Clone repository
git clone https://github.com/arec1b0/KubeSentiment.git
cd KubeSentiment

# Run full setup script
./scripts/setup-monitoring.sh
```

## Access Monitoring Interfaces

```bash
# Grafana (dashboards)
kubectl port-forward -n monitoring svc/prometheus-operator-grafana 3000:80
# Open: http://localhost:3000 (admin/admin123)

# Prometheus (metrics)
kubectl port-forward -n monitoring svc/prometheus-operator-kube-p-prometheus 9090:9090
# Open: http://localhost:9090
```

## Available Dashboards

1. **MLOps Sentiment Analysis** - Main application metrics
2. **MLOps Sentiment Analysis - Advanced** - Detailed performance metrics
3. **Kubernetes / Compute Resources / Pod** - Resource utilization
4. **Prometheus / Overview** - Prometheus health

## Metrics & Alerts

### Key Metrics

- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `ml_prediction_total` - Total predictions
- `ml_prediction_duration_seconds` - Inference time
- `ml_model_confidence` - Model confidence scores

### Alert Rules

Configured alerts include:
- 🔴 **Critical**: Service down, model not loaded
- 🟡 **Warning**: High latency (>200ms), resource usage
- 🔵 **Info**: Traffic anomalies, efficiency issues

## Further Reading

- [Architecture Documentation](architecture.md) - System design
- [Deployment Guide](setup/deployment-guide.md) - Deployment options
- [Troubleshooting Guide](troubleshooting/index.md) - Common issues

## Configuration Files

- `config/monitoring/prometheus-rules.yaml` - Prometheus alerting rules
- `config/grafana-*.json` - Grafana dashboard definitions
- `helm/mlops-sentiment/values.yaml` - Monitoring configuration
