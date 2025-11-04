# 🚀 MLOps Sentiment Analysis - Benchmark Results Documentation

## 📋 Overview

This document provides comprehensive documentation for running the full benchmark suite and interpreting the results. The benchmarking framework tests the sentiment analysis service across different instance types (CPU and GPU) to measure performance, resource utilization, and cost efficiency.

## 🔧 Prerequisites

### 1. Service Deployment

The benchmark suite requires a running instance of the MLOps Sentiment Analysis service. Choose one of the following deployment methods:

#### Option A: Local Development Server

```bash
# Start the service locally
python run.py

# Or using Docker
docker-compose up -d

# Service will be available at http://localhost:8000
```

#### Option B: Kubernetes Deployment

```bash
# Deploy to Kubernetes using Helm
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-sentiment \
  --create-namespace \
  --values ./helm/mlops-sentiment/values-dev.yaml

# Port-forward for local access
kubectl port-forward -n mlops-sentiment svc/mlops-sentiment 8080:80
```

### 2. Python Dependencies

```bash
# Install benchmarking dependencies
cd benchmarking
pip install -r requirements.txt

# Or install from project root
pip install -r requirements.txt
pip install aiohttp pandas plotly pyyaml numpy matplotlib seaborn scipy
```

### 3. Required Tools

- **Python 3.11+** with pip
- **kubectl** (for Kubernetes deployments)
- **helm** (for Kubernetes deployments)
- **curl** or **wget** (for endpoint testing)

## 🎯 Running the Benchmark Suite

### Quick Benchmark (Single Instance)

The quick benchmark tests a single instance type with default parameters:

```bash
cd benchmarking

# Default: cpu-small, 10 users, 60 seconds
./quick-benchmark.sh

# Custom parameters
./quick-benchmark.sh -t cpu-medium -u 20 -d 120

# GPU instance test
./quick-benchmark.sh -t gpu-t4 -u 50 -d 300
```

**Parameters:**
- `-t, --type`: Instance type (cpu-small, cpu-medium, cpu-large, gpu-t4, etc.)
- `-u, --users`: Number of concurrent users (default: 10)
- `-d, --duration`: Test duration in seconds (default: 60)
- `-e, --endpoint`: API endpoint URL (default: http://localhost:8080/predict)
- `-n, --namespace`: Kubernetes namespace (default: mlops-benchmark)

### Full Benchmark Suite (All Instances)

The full benchmark suite tests multiple instance types with varying load levels:

```bash
cd benchmarking

# Run full benchmark suite
./scripts/deploy-benchmark.sh

# With custom namespace and results directory
./scripts/deploy-benchmark.sh --namespace my-benchmark --results-dir ./my-results
```

**What it does:**
1. Deploys benchmark infrastructure to Kubernetes
2. Tests each instance type with concurrent users: [1, 5, 10, 20, 50, 100]
3. Collects performance metrics, resource utilization, and cost data
4. Generates comprehensive reports

### Individual Component Testing

Run specific components individually:

```bash
# Load testing only
python scripts/load-test.py \
  --instance-type cpu-medium \
  --endpoint http://localhost:8080/predict \
  --users 20 \
  --duration 120 \
  --output results/load_test.json

# Resource monitoring only
python scripts/resource-monitor.py \
  --namespace mlops-benchmark \
  --duration 300 \
  --output results/resource_metrics.json

# Cost calculation only
python scripts/cost-calculator.py \
  --results results/benchmark_results.json \
  --predictions 1000 \
  --output results/cost_analysis.json

# Report generation
python scripts/report-generator.py \
  --results-dir results \
  --output results/comprehensive_report.html
```

## 📊 Results Structure

### Output Files

After running benchmarks, the following files are generated in the `results/` directory:

```
results/
├── benchmark_<instance>_<users>users.json    # Performance metrics per test
├── resource_metrics_<instance>.json          # Resource utilization data
├── cost_analysis_<instance>.json             # Cost analysis results
├── consolidated_results.json                # Combined benchmark data
├── reports/
│   ├── performance_charts.html              # Performance visualizations
│   └── cost_charts.html                      # Cost analysis charts
└── comprehensive_report.html                 # Complete HTML report
```

### Performance Metrics

Each benchmark result JSON contains:

```json
{
  "instance_type": "cpu-medium",
  "concurrent_users": 20,
  "duration": 120.0,
  "total_requests": 2400,
  "successful_requests": 2398,
  "failed_requests": 2,
  "requests_per_second": 19.98,
  "avg_latency": 45.2,
  "p50_latency": 42.1,
  "p90_latency": 68.5,
  "p95_latency": 85.3,
  "p99_latency": 125.7,
  "min_latency": 12.3,
  "max_latency": 234.5,
  "error_rate": 0.08,
  "throughput": 19.98
}
```

### Resource Metrics

Resource monitoring data includes:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "cpu_percent": 65.3,
  "memory_percent": 45.2,
  "gpu_utilization": 78.5,
  "network_rx_bytes": 1250000,
  "network_tx_bytes": 890000
}
```

### Cost Analysis

Cost calculation results:

```json
{
  "instance_name": "cpu-medium",
  "cost_per_hour": 0.096,
  "cost_per_1000_predictions": 0.0048,
  "requests_per_second": 19.98,
  "total_efficiency_score": 208.13
}
```

## 📈 Interpreting Results

### Key Performance Indicators (KPIs)

1. **Requests Per Second (RPS)**
   - Higher is better
   - Indicates throughput capacity
   - Target: >20 RPS for CPU instances, >100 RPS for GPU instances

2. **Latency Percentiles**
   - **P50 (Median)**: Typical response time
   - **P95**: 95% of requests complete within this time
   - **P99**: Worst-case scenario response time
   - Target: P95 < 200ms, P99 < 500ms

3. **Error Rate**
   - Should be < 1% for production workloads
   - Higher error rates indicate system stress or resource constraints

4. **Cost Efficiency**
   - Cost per 1000 predictions
   - Lower is better for cost-sensitive deployments
   - Balance with performance requirements

### Instance Type Recommendations

Based on typical benchmark results:

| Instance Type | Best For | Expected RPS | Cost/1k Pred |
|--------------|----------|--------------|--------------|
| cpu-small     | Development, testing | 10-20 | $0.002 |
| cpu-medium    | Low-medium load | 20-50 | $0.005 |
| cpu-large     | Medium-high load | 50-100 | $0.010 |
| gpu-t4        | GPU inference, batch processing | 100-200 | $0.026 |
| gpu-v100      | High-performance inference | 200-500 | $0.153 |

### Performance Optimization Tips

1. **CPU Instances**
   - Best for cost-sensitive, low-to-medium load scenarios
   - Consider horizontal scaling (HPA) for higher throughput
   - Optimize model quantization for CPU inference

2. **GPU Instances**
   - Best for high-throughput, low-latency requirements
   - Utilize batch processing for efficiency
   - Monitor GPU utilization to avoid over-provisioning

3. **Scaling Strategies**
   - Use HPA for dynamic scaling based on CPU/memory
   - Consider vertical scaling for consistent high load
   - Implement caching for repeated queries

## 🔍 Troubleshooting

### Service Not Accessible

```bash
# Check if service is running
curl http://localhost:8080/health

# For Kubernetes
kubectl get pods -n mlops-sentiment
kubectl port-forward -n mlops-sentiment svc/mlops-sentiment 8080:80
```

### Benchmark Failures

1. **Connection Timeouts**
   - Increase `request_timeout` in config
   - Check network connectivity
   - Verify service is healthy

2. **High Error Rates**
   - Reduce concurrent users
   - Check resource limits
   - Review service logs

3. **Missing Dependencies**
   ```bash
   pip install -r benchmarking/requirements.txt
   ```

### Resource Monitoring Issues

```bash
# Verify metrics-server is running (Kubernetes)
kubectl get deployment metrics-server -n kube-system

# Check Prometheus (if enabled)
kubectl get pods -n monitoring -l app=prometheus
```

## 📝 Example Benchmark Run

### Step-by-Step Execution

```bash
# 1. Start the service
python run.py &
# Service running on http://localhost:8000

# 2. Verify service is accessible
curl http://localhost:8000/health

# 3. Run quick benchmark
cd benchmarking
./quick-benchmark.sh -t cpu-medium -u 20 -d 120

# 4. View results
cat results/benchmark_cpu-medium_quick.json | python -m json.tool

# 5. Generate comprehensive report
python scripts/report-generator.py \
  --results-dir results \
  --output results/benchmark_report.html

# 6. Open report in browser
# Windows: start results/benchmark_report.html
# Linux/Mac: open results/benchmark_report.html
```

## 🎯 Benchmark Scenarios

### 1. Performance Baseline
- **Users**: 1, 5, 10
- **Duration**: 180 seconds
- **Purpose**: Establish baseline performance metrics

### 2. Stress Test
- **Users**: 50, 100, 200
- **Duration**: 300 seconds
- **Purpose**: Test system limits and failure points

### 3. Scalability Test
- **Users**: Gradually increase from 1 to 100
- **Duration**: 600 seconds
- **Purpose**: Validate horizontal scaling behavior

### 4. Stability Test
- **Users**: 20 (constant)
- **Duration**: 3600 seconds (1 hour)
- **Purpose**: Test long-term stability and resource leaks

## 📊 Reporting

### HTML Report Features

The generated HTML report includes:

1. **Performance Comparison Charts**
   - RPS by instance type
   - Latency percentiles
   - Efficiency metrics

2. **Cost Analysis**
   - Cost per 1000 predictions
   - Cost vs. performance bubble chart
   - Efficiency scores

3. **Resource Utilization**
   - CPU/Memory/GPU over time
   - Average utilization by instance
   - Resource summary charts

4. **Detailed Tables**
   - All benchmark results
   - Cost breakdown
   - Recommendations

### Exporting Results

```bash
# Convert JSON to CSV
python -c "
import json
import pandas as pd
data = json.load(open('results/consolidated_results.json'))
df = pd.DataFrame(data)
df.to_csv('results/benchmark_results.csv', index=False)
"

# Generate PDF report (requires weasyprint)
python scripts/report-generator.py --format pdf
```

## 🔄 Continuous Benchmarking

### Automated Benchmark Runs

Set up automated benchmarks using cron or CI/CD:

```bash
# Cron job (daily at 2 AM)
0 2 * * * cd /path/to/KubeSentiment/benchmarking && ./quick-benchmark.sh -t cpu-medium >> /var/log/benchmark.log 2>&1
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Run Benchmarks
  run: |
    cd benchmarking
    ./quick-benchmark.sh -t cpu-medium -u 20 -d 120
    python scripts/report-generator.py --results-dir results --output benchmark_report.html
  continue-on-error: true
```

## 📚 Additional Resources

- [Benchmarking README](README.md) - Detailed framework documentation
- [Example Usage](examples/example-usage.md) - Usage examples
- [Configuration Guide](configs/benchmark-config.yaml) - Configuration options
- [Main Project README](../../README.md) - Project overview

## 🆘 Support

For issues or questions:
1. Check troubleshooting section above
2. Review service logs: `kubectl logs -n mlops-sentiment -l app.kubernetes.io/name=mlops-sentiment`
3. Verify configuration: `cat configs/benchmark-config.yaml`
4. Open an issue in the repository

---

**Last Updated**: 2024-01-15
**Version**: 1.0.0

