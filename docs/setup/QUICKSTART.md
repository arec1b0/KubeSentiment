# 🚀 MLOps Sentiment Analysis - Quick Start

## ⚡ Quick Start (5 minutes)

### 1️⃣ Prerequisites

```bash
# Check that you have:
kubectl version --client  # Kubernetes CLI
helm version              # Helm package manager
```

### 2️⃣ Clone Repository

```bash
git clone https://github.com/arec1b0/KubeSentiment.git
cd KubeSentiment
```

### 3️⃣ Launch Full Monitoring System

```bash
# Make script executable
chmod +x scripts/setup-monitoring.sh

# Run full setup (takes 5-10 minutes)
./scripts/setup-monitoring.sh
```

### 4️⃣ Access Interfaces

After successful installation:

```bash
# Grafana (dashboards and visualization)
kubectl port-forward -n monitoring svc/prometheus-operator-grafana 3000:80
# Open: http://localhost:3000 (admin/admin123)

# Prometheus (metrics and alerts)
kubectl port-forward -n monitoring svc/prometheus-operator-kube-p-prometheus 9090:9090
# Open: http://localhost:9090

# MLOps API (the service itself)
kubectl port-forward -n mlops-sentiment svc/mlops-sentiment 8080:80
# Test: curl http://localhost:8080/health
```

## 🎯 What You Get

### 📊 Monitoring

- **Grafana dashboards** with performance metrics
- **Prometheus alerts** for critical issues
- **SLO/SLI metrics** (99.9% availability, <200ms latency)
- **ML-specific metrics** (model confidence, inference time)

### 🔒 Security

- **NetworkPolicy** - strict network traffic isolation
- **RBAC** - minimal access rights
- **Security Context** - run without root privileges
- **Secrets management** - secure key storage

### 🚀 Deployment

- **Helm charts** - packaging of all components
- **Multi-environment** - dev/staging/prod configurations
- **Auto-scaling** - HPA based on CPU/Memory
- **Rolling updates** - updates without downtime

### 🚨 Alerting

- **Slack notifications** - integration with team channels
- **Email alerts** - for critical issues
- **PagerDuty** - escalation for production
- **Smart routing** - different channels for different alert types

## 📊 Benchmarking and Performance Testing

### 🚀 Quick Benchmark

```bash
# Navigate to benchmarking directory
cd benchmarking

# Install benchmarking system
./install.sh

# Quick performance test
./quick-benchmark.sh

# Test specific instance type
./quick-benchmark.sh -t cpu-medium -u 20 -d 120
```

### 📈 What You Get from Benchmark

- **Performance metrics** - RPS, latency, throughput
- **Cost analysis** - cost of 1000 predictions for each instance type
- **Resource monitoring** - CPU, GPU, memory utilization
- **Recommendations** - optimal instance choice for your requirements
- **Interactive reports** - HTML dashboards with charts and analysis

### 🎯 Instance Types for Testing

| Type | Purpose | Cost/hour | RPS |
|------|---------|-----------|-----|
| `cpu-small` | Development, testing | $0.04 | ~20 |
| `cpu-medium` | Low load | $0.10 | ~50 |
| `cpu-large` | Medium load | $0.19 | ~100 |
| `gpu-t4` | GPU inference | $0.53 | ~200 |
| `gpu-v100` | High performance | $3.06 | ~500 |

More details: [Benchmarking Guide](BENCHMARKING.md)

## 🧪 Testing

> **Note:** The examples below use root-level endpoints (e.g., `/health`, `/predict`). In production deployments, all API endpoints are prefixed with `/api/v1` (e.g., `/api/v1/health`, `/api/v1/predict`). The debug mode (used in local development) omits this prefix for convenience.

```bash
# Check service health (production: /api/v1/health)
curl http://localhost:8080/health

# Test prediction API (production: /api/v1/predict)
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this monitoring system!"}'

# View metrics (production: /api/v1/metrics)
curl http://localhost:8080/metrics

# Check logs
kubectl logs -f -n mlops-sentiment -l app.kubernetes.io/name=mlops-sentiment
```

## 🔧 Management

```bash
# Scaling
kubectl scale deployment mlops-sentiment --replicas=5 -n mlops-sentiment

# Update
helm upgrade mlops-sentiment ./helm/mlops-sentiment -n mlops-sentiment --set image.tag=v1.1.0

# Status
./scripts/infra/setup-monitoring.sh status

# Complete removal
./scripts/infra/setup-monitoring.sh cleanup
```

## 📈 Grafana Dashboards

After logging into Grafana, find:

1. **MLOps Sentiment Analysis** - main dashboard
2. **MLOps Sentiment Analysis - Advanced** - extended metrics
3. **Kubernetes / Compute Resources / Pod** - pod resources
4. **Prometheus / Overview** - Prometheus status

## 🚨 Alerts

System automatically configures alerts for:

- 🔴 **Critical**: Service unavailable, model not loaded
- 🟡 **Warning**: High latency, resource usage
- 🔵 **Info**: Traffic anomalies, resource inefficiency

## 🆘 Help

```bash
# Check status of all components
kubectl get all -n monitoring
kubectl get all -n mlops-sentiment

# View events
kubectl get events --sort-by=.metadata.creationTimestamp

# Monitoring logs
kubectl logs -n monitoring -l app.kubernetes.io/name=prometheus
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana
```

## 📚 Further Reading

- [MONITORING.md](MONITORING.md) - Complete monitoring documentation
- [DEVELOPMENT.md](DEVELOPMENT.md) - Developer guide
- [KUBERNETES.md](KUBERNETES.md) - Kubernetes deployment

---

**🎉 Congratulations! Your MLOps system with full monitoring is ready to work!**
