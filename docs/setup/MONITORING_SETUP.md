# Monitoring Setup Guide

This guide provides detailed instructions for setting up the complete monitoring stack for KubeSentiment.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Setup](#quick-setup)
4. [Manual Setup](#manual-setup)
5. [Configuration](#configuration)
6. [Accessing Dashboards](#accessing-dashboards)
7. [Alert Configuration](#alert-configuration)
8. [Troubleshooting](#troubleshooting)

## Overview

The KubeSentiment monitoring stack includes:

- **Prometheus**: Metrics collection, storage, and alerting engine
- **Grafana**: Visualization and dashboarding
- **Alertmanager**: Alert routing and notification management
- **Prometheus Operator**: Automated Prometheus management
- **ServiceMonitor**: Automatic service discovery for metrics

## Prerequisites

### Required Tools

- Kubernetes cluster (1.21+)
- kubectl configured
- Helm 3.7+
- At least 4GB available memory
- 10GB available storage

### Recommended

- Ingress controller (NGINX, Traefik)
- Persistent storage (for long-term metrics retention)
- External alerting destinations (Slack, PagerDuty, email)

## Quick Setup

### One-Command Setup

The fastest way to get the full monitoring stack running:

```bash
# Make the script executable
chmod +x scripts/setup-monitoring.sh

# Run the setup script
./scripts/setup-monitoring.sh
```

This script will:
1. Install kube-prometheus-stack via Helm
2. Deploy the application with monitoring enabled
3. Configure ServiceMonitors and PrometheusRules
4. Set up Grafana dashboards
5. Configure Alertmanager

### Verify Installation

```bash
# Check monitoring namespace
kubectl get all -n monitoring

# Check application namespace
kubectl get all -n mlops-sentiment

# Verify ServiceMonitor
kubectl get servicemonitor -n mlops-sentiment
```

## Manual Setup

### Step 1: Install Prometheus Operator

```bash
# Add Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Create monitoring namespace
kubectl create namespace monitoring

# Install kube-prometheus-stack
helm install prometheus-operator prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
  --set grafana.adminPassword=admin123
```

### Step 2: Deploy Application with Monitoring

```bash
# Deploy with monitoring enabled
helm install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-sentiment \
  --create-namespace \
  --set monitoring.enabled=true \
  --set monitoring.serviceMonitor.enabled=true
```

### Step 3: Configure Prometheus Rules

```bash
# Apply custom alerting rules
kubectl apply -f config/monitoring/prometheus-rules.yaml -n monitoring
```

### Step 4: Import Grafana Dashboards

```bash
# Import dashboards via Grafana UI or ConfigMap
kubectl create configmap grafana-dashboard-mlops \
  --from-file=config/grafana-dashboard.json \
  -n monitoring \
  --dry-run=client -o yaml | kubectl apply -f -

# Label the ConfigMap for auto-discovery
kubectl label configmap grafana-dashboard-mlops \
  grafana_dashboard=1 \
  -n monitoring
```

## Configuration

### Prometheus Configuration

Prometheus is configured via the `prometheus-operator` Helm chart. Key configurations:

#### Metrics Retention

```yaml
# values.yaml
prometheus:
  prometheusSpec:
    retention: 30d  # Keep metrics for 30 days
    retentionSize: "50GB"  # Maximum storage size
```

#### Resource Limits

```yaml
prometheus:
  prometheusSpec:
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 2000m
        memory: 8Gi
```

#### ServiceMonitor Selector

```yaml
prometheus:
  prometheusSpec:
    serviceMonitorSelectorNilUsesHelmValues: false  # Monitor all ServiceMonitors
    serviceMonitorNamespaceSelector: {}  # Monitor all namespaces
```

### Grafana Configuration

#### Admin Credentials

```yaml
grafana:
  adminPassword: admin123  # Change in production!
  adminUser: admin
```

#### Data Sources

```yaml
grafana:
  additionalDataSources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-operator-kube-p-prometheus:9090
      access: proxy
      isDefault: true
```

#### Dashboard Provisioning

```yaml
grafana:
  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
        - name: 'default'
          orgId: 1
          folder: ''
          type: file
          disableDeletion: false
          options:
            path: /var/lib/grafana/dashboards/default
```

### Alertmanager Configuration

Configure alert routing in `helm/mlops-sentiment/values.yaml`:

```yaml
alertmanager:
  config:
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'default'
      routes:
        - match:
            severity: critical
          receiver: 'critical-alerts'
        - match:
            severity: warning
          receiver: 'warning-alerts'

    receivers:
      - name: 'default'
        slack_configs:
          - channel: '#monitoring'
            title: 'KubeSentiment Alert'
            text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

      - name: 'critical-alerts'
        slack_configs:
          - channel: '#critical-alerts'
            title: '🔴 CRITICAL: {{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        pagerduty_configs:
          - service_key: 'YOUR_PAGERDUTY_KEY'

      - name: 'warning-alerts'
        slack_configs:
          - channel: '#warnings'
            title: '🟡 Warning: {{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

## Accessing Dashboards

### Grafana

```bash
# Port forward to Grafana
kubectl port-forward -n monitoring svc/prometheus-operator-grafana 3000:80

# Open in browser: http://localhost:3000
# Login: admin / admin123
```

### Prometheus

```bash
# Port forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus-operator-kube-p-prometheus 9090:9090

# Open in browser: http://localhost:9090
```

### Alertmanager

```bash
# Port forward to Alertmanager
kubectl port-forward -n monitoring svc/prometheus-operator-kube-p-alertmanager 9093:9093

# Open in browser: http://localhost:9093
```

### Ingress Setup (Production)

```yaml
# grafana-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
  namespace: monitoring
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - grafana.yourdomain.com
      secretName: grafana-tls
  rules:
    - host: grafana.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: prometheus-operator-grafana
                port:
                  number: 80
```

## Alert Configuration

### Custom Alerting Rules

Create custom rules in `config/monitoring/prometheus-rules.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: mlops-sentiment-alerts
  namespace: monitoring
spec:
  groups:
    - name: mlops-sentiment
      interval: 30s
      rules:
        - alert: HighErrorRate
          expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High error rate detected"
            description: "Error rate is {{ $value }} requests/second"
```

### Available Alerts

The system includes pre-configured alerts for:

**Critical Alerts**
- Service Down
- Model Not Loaded
- High Error Rate (>5%)
- Vault Sealed/Down

**Warning Alerts**
- High Latency (>200ms)
- High Resource Usage (CPU >80%, Memory >85%)
- Slow Model Inference (>500ms)
- Low Prediction Confidence

**Info Alerts**
- Traffic Anomalies
- Resource Inefficiency
- Vault Secret Expiry Warnings

## Metrics Reference

### Application Metrics

```
# HTTP Metrics
http_requests_total{method, endpoint, status}
http_request_duration_seconds{method, endpoint}

# ML Metrics
ml_prediction_total{model, outcome}
ml_prediction_duration_seconds{model}
ml_model_confidence{model, sentiment}
ml_cache_hits_total
ml_cache_misses_total

# Model Performance
ml_model_load_duration_seconds
ml_warmup_duration_seconds
ml_inference_throughput

# Resource Metrics
process_cpu_seconds_total
process_resident_memory_bytes
process_open_fds
```

### Kubernetes Metrics

```
# Pod Metrics
kube_pod_status_phase{namespace, pod}
kube_pod_container_resource_requests{resource}
kube_pod_container_resource_limits{resource}

# Deployment Metrics
kube_deployment_status_replicas{deployment}
kube_deployment_spec_replicas{deployment}

# Node Metrics
node_cpu_seconds_total
node_memory_MemTotal_bytes
node_filesystem_size_bytes
```

## Troubleshooting

### Prometheus Not Scraping Metrics

**Check ServiceMonitor**
```bash
kubectl get servicemonitor -n mlops-sentiment
kubectl describe servicemonitor mlops-sentiment -n mlops-sentiment
```

**Check Prometheus Targets**
1. Port-forward to Prometheus: `kubectl port-forward -n monitoring svc/prometheus-operator-kube-p-prometheus 9090:9090`
2. Open http://localhost:9090/targets
3. Look for mlops-sentiment targets

**Common Issues**
- ServiceMonitor label selectors don't match Service labels
- Prometheus not configured to discover ServiceMonitors in application namespace
- Network policies blocking Prometheus from scraping

### Grafana Dashboards Not Loading

**Check Dashboard ConfigMap**
```bash
kubectl get configmap -n monitoring | grep grafana-dashboard
kubectl describe configmap grafana-dashboard-mlops -n monitoring
```

**Check Grafana Logs**
```bash
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana
```

### Alerts Not Firing

**Check Prometheus Rules**
```bash
kubectl get prometheusrule -n monitoring
kubectl describe prometheusrule mlops-sentiment-alerts -n monitoring
```

**Check Alertmanager**
1. Port-forward: `kubectl port-forward -n monitoring svc/prometheus-operator-kube-p-alertmanager 9093:9093`
2. Open http://localhost:9093
3. Check for active alerts and routing

**Verify Alert Expression**
Query the metric in Prometheus UI to ensure it returns data.

### High Memory Usage

**Reduce Metrics Retention**
```yaml
prometheus:
  prometheusSpec:
    retention: 15d  # Reduce from 30d
    retentionSize: "25GB"  # Reduce from 50GB
```

**Increase Resources**
```yaml
prometheus:
  prometheusSpec:
    resources:
      limits:
        memory: 16Gi  # Increase as needed
```

## Best Practices

1. **Secure Grafana**: Change default admin password
2. **Enable TLS**: Use HTTPS for all monitoring interfaces
3. **Configure Backups**: Regular Grafana dashboard and Prometheus data backups
4. **Tune Retention**: Balance storage costs with data retention needs
5. **Alert Fatigue**: Set appropriate thresholds to avoid excessive alerts
6. **Label Consistency**: Use consistent labels across metrics
7. **High Availability**: Run multiple Prometheus and Alertmanager replicas
8. **Resource Limits**: Set appropriate CPU/memory limits
9. **Network Policies**: Restrict access to monitoring components
10. **Regular Updates**: Keep Prometheus Operator and components updated

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [Architecture Guide](../architecture.md)
