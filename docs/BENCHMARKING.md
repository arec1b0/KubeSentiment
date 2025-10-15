# 🚀 MLOps Sentiment Analysis - Benchmarking Guide

## 📊 Overview

Comprehensive benchmarking system for testing sentiment analysis model performance on various instance types (CPU and GPU). This module allows you to:

- **Measure performance** - latency, RPS, throughput
- **Analyze costs** - cost of 1000 predictions for each instance type
- **Monitor resources** - CPU, GPU, memory utilization during load
- **Compare instances** - choose optimal type for your requirements

## 🎯 Benchmarking Goals

### Performance

- ⚡ **Latency** - request response time (P50, P95, P99)
- 🚀 **RPS** - requests per second
- 📊 **Throughput** - overall throughput
- ❌ **Error Rate** - percentage of failed requests

### Resources

- 🖥️ **CPU Utilization** - processor usage
- 💾 **Memory Usage** - memory consumption
- 🎮 **GPU Utilization** - GPU usage (for GPU instances)
- 🌐 **Network I/O** - network traffic

### Cost

- 💰 **Cost per 1000 predictions** - main cost metric
- ⏰ **Cost per hour** - hourly instance cost
- 📈 **Cost efficiency** - performance/cost ratio

## 🚀 Quick Start

### 1. Simple Test

```bash
cd benchmarking

# Install dependencies
pip install -r requirements.txt

# Quick test with default settings
./quick-benchmark.sh
```

### 2. Test Specific Instance

```bash
# CPU instance with 20 users for 2 minutes
./quick-benchmark.sh -t cpu-medium -u 20 -d 120

# GPU instance with high load
./quick-benchmark.sh -t gpu-t4 -u 100 -d 300
```

### 3. Full Benchmark of All Instances

```bash
# Automatic testing of all instance types
./scripts/deploy-benchmark.sh
```

## 📋 Supported Instance Types

### CPU Instances

| Type | vCPU | Memory | Cost/hour | Recommendations |
|------|------|--------|-----------|----------------|
| `cpu-small` (t3.medium) | 2 | 4GB | $0.0416 | Development, testing |
| `cpu-medium` (c5.large) | 2 | 4GB | $0.096 | Low load |
| `cpu-large` (c5.xlarge) | 4 | 8GB | $0.192 | Medium load |
| `cpu-xlarge` (c5.2xlarge) | 8 | 16GB | $0.384 | High load |

### GPU Instances

| Type | GPU | vCPU | Memory | Cost/hour | Recommendations |
|------|-----|------|--------|-----------|----------------|
| `gpu-t4` (g4dn.xlarge) | T4 | 4 | 16GB | $0.526 | Inference, medium load |
| `gpu-v100` (p3.2xlarge) | V100 | 8 | 61GB | $3.06 | High-performance inference |
| `gpu-a100` (p4d.xlarge) | A100 | 4 | 96GB | $3.912 | Maximum performance |

## 📊 Interpreting Results

### Performance Metrics

#### Latency

- **P50 < 100ms** - excellent performance
- **P95 < 200ms** - good performance
- **P99 < 500ms** - acceptable performance
- **P99 > 1000ms** - requires optimization

#### RPS (Requests Per Second)

- **< 10 RPS** - low performance
- **10-50 RPS** - medium performance
- **50-100 RPS** - good performance
- **> 100 RPS** - excellent performance

#### Error Rate

- **< 1%** - excellent stability
- **1-5%** - acceptable stability
- **> 5%** - requires investigation

### Cost Analysis

#### Cost per 1000 Predictions

- **< $0.01** - very economical
- **$0.01-0.05** - economical
- **$0.05-0.10** - moderate
- **> $0.10** - expensive

#### Efficiency

Calculated as: `(RPS × Latency_Score) / Cost_per_Hour`

## 🎯 Instance Selection Recommendations

### For Development and Testing

```bash
# Recommended: cpu-small
./quick-benchmark.sh -t cpu-small -u 5 -d 60
```

- ✅ Low cost
- ✅ Sufficient for development
- ❌ Limited performance

### For Production with Low Load (< 20 RPS)

```bash
# Recommended: cpu-medium
./quick-benchmark.sh -t cpu-medium -u 20 -d 300
```

- ✅ Good price/performance ratio
- ✅ Stable operation
- ✅ Auto-scaling capability

### For Production with Medium Load (20-100 RPS)

```bash
# Recommended: cpu-large or gpu-t4
./quick-benchmark.sh -t cpu-large -u 50 -d 300
./quick-benchmark.sh -t gpu-t4 -u 50 -d 300
```

- ✅ High performance
- ✅ Low latency
- ⚠️ Medium cost

### For Production with High Load (> 100 RPS)

```bash
# Recommended: gpu-v100 or gpu-a100
./quick-benchmark.sh -t gpu-v100 -u 100 -d 600
```

- ✅ Maximum performance
- ✅ Minimum latency
- ❌ High cost

## 📈 Monitoring and Alerts

### Recommended Alerts

```yaml
# Prometheus alerts
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5

- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05

- alert: LowThroughput
  expr: rate(http_requests_total[5m]) < 10
```

### Grafana Dashboards

After benchmarking, import dashboards from `results/grafana_dashboards/`

## 🔧 Configuration and Customization

### Changing Test Parameters

Edit `configs/benchmark-config.yaml`:

```yaml
benchmark:
  load_test:
    duration: 300  # Test duration in seconds
    concurrent_users: [1, 5, 10, 20, 50, 100]  # Number of users

instances:
  cpu:
    - name: "my-custom-cpu"
      type: "c5.4xlarge"
      cost_per_hour: 0.768
```

### Adding New Instance Types

1. Update `configs/benchmark-config.yaml`
2. Create corresponding Kubernetes manifests in `deployments/`
3. Run benchmark

## 📁 Results Structure

After benchmark execution, the `results/` directory will contain:

```
results/
├── benchmark_*.json              # Load test results
├── resource_metrics_*.json       # Resource usage metrics
├── cost_analysis.json           # Cost analysis
├── consolidated_results.json    # Consolidated results
├── reports/                     # Charts and visualization
│   ├── benchmark_report_*.png
│   └── cost_performance_*.png
├── cost_reports/               # Cost reports
│   ├── cost_analysis.png
│   └── cost_performance_bubble.png
└── benchmark_final_report.md   # Final report
```

## 🚨 Troubleshooting

### Problem: "No connection to Kubernetes cluster"

```bash
# Check cluster connection
kubectl cluster-info

# Configure kubeconfig
export KUBECONFIG=/path/to/your/kubeconfig
```

### Problem: "GPU not available"

```bash
# Check for GPU nodes
kubectl get nodes -l accelerator=nvidia-tesla-t4

# Install NVIDIA Device Plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml
```

### Problem: "High error rate during testing"

1. Check application logs: `kubectl logs -l app=mlops-sentiment`
2. Increase resources in deployment
3. Reduce number of concurrent users

## 🔗 CI/CD Integration

### GitHub Actions

```yaml
name: Performance Benchmark
on:
  schedule:
    - cron: '0 2 * * 1'  # Every Monday at 2:00

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run Benchmark
      run: |
        cd benchmarking
        ./quick-benchmark.sh -t cpu-medium -u 20 -d 120
    - name: Upload Results
      uses: actions/upload-artifact@v3
      with:
        name: benchmark-results
        path: benchmarking/results/
```

## 📚 Additional Resources

- [Main project documentation](../README.md)
- [Deployment guide](../deployment-guide.md)
- [System architecture](../docs/architecture.md)
- [Troubleshooting](../docs/troubleshooting/index.md)
- [OpenAPI specification](../openapi-specs/sentiment-api.yaml)

---

**Next Steps:**

1. Run quick benchmark: `./quick-benchmark.sh`
2. Analyze results in HTML report
3. Choose optimal instance type for your requirements
4. Configure production deployment with selected parameters
