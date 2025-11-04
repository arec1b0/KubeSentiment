# 🚀 MLOps Sentiment Analysis - Benchmarking Framework

## 📊 Overview

Comprehensive benchmarking system for testing sentiment analysis model performance on various instance types (CPU and GPU).

## 🎯 Benchmarking Goals

- **Measure latency** - request response time
- **Test RPS** - requests per second
- **Monitor resources** - CPU, GPU, memory utilization
- **Calculate costs** - cost of 1000 predictions for each instance type

## 🏗️ Project Structure

```
benchmarking/
├── configs/                    # Configurations for different instance types
│   ├── cpu-instances.yaml
│   ├── gpu-instances.yaml
│   └── benchmark-config.yaml
├── scripts/                    # Benchmarking scripts
│   ├── load-test.py           # Load testing
│   ├── resource-monitor.py    # Resource monitoring
│   ├── cost-calculator.py     # Cost calculation
│   └── deploy-benchmark.sh    # Automatic deployment
├── deployments/               # Kubernetes manifests
│   ├── cpu-deployment.yaml
│   ├── gpu-deployment.yaml
│   └── monitoring.yaml
├── results/                   # Benchmark results
│   ├── reports/
│   ├── metrics/
│   └── charts/
└── requirements.txt           # Python dependencies
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd benchmarking
pip install -r requirements.txt

# Make scripts executable (Linux/macOS)
chmod +x scripts/*.sh
chmod +x quick-benchmark.sh
```

### 2. Quick Test of Single Instance

```bash
# Simple test with default settings
./quick-benchmark.sh

# Test with custom parameters
./quick-benchmark.sh -t cpu-medium -u 20 -d 120

# Test GPU instance
./quick-benchmark.sh -t gpu-t4 -u 50 -d 300
```

### 3. Full Benchmark of All Instances

```bash
# Automatic benchmark on all instance types
./scripts/deploy-benchmark.sh

# With custom parameters
./scripts/deploy-benchmark.sh --namespace my-benchmark --results-dir ./my-results
```

### 4. Manual Launch of Individual Components

```bash
# Load testing only
python scripts/load-test.py --instance-type cpu-small --users 10 --duration 60

# Resource monitoring only
python scripts/resource-monitor.py --duration 300 --namespace mlops-benchmark

# Cost calculation only
python scripts/cost-calculator.py --results results/benchmark_results.json
```

## 📈 Metrics

### Performance

- **Latency P50/P95/P99** - response time percentiles
- **RPS (Requests Per Second)** - throughput
- **Throughput** - number of processed requests

### Resources

- **CPU Utilization** - processor usage
- **GPU Utilization** - GPU usage (for GPU instances)
- **Memory Usage** - memory consumption
- **Network I/O** - network traffic

### Cost

- **Cost per 1000 predictions** - cost of 1000 predictions
- **Cost per hour** - hourly instance cost
- **Cost efficiency** - performance/cost ratio

## 🔧 Configuration

Main parameters in `configs/benchmark-config.yaml`:

```yaml
benchmark:
  duration: 300s              # Test duration
  concurrent_users: [1, 5, 10, 20, 50, 100]  # Number of concurrent users
  ramp_up_time: 30s          # Load ramp-up time

instances:
  cpu:
    - type: "t3.medium"
    - type: "c5.large"
    - type: "c5.xlarge"
  gpu:
    - type: "p3.2xlarge"
    - type: "g4dn.xlarge"

costs:
  # Instance costs in USD/hour (AWS)
  t3.medium: 0.0416
  c5.large: 0.096
  c5.xlarge: 0.192
  p3.2xlarge: 3.06
  g4dn.xlarge: 0.526
```

## 📊 Reports

After benchmark completion, the following will be created:

1. **HTML report** - interactive charts and tables
2. **JSON metrics** - raw data for further analysis
3. **CSV files** - data for import to Excel/Google Sheets
4. **Grafana dashboard** - real-time monitoring

## 📚 Documentation

- **[Benchmark Results Guide](BENCHMARK_RESULTS.md)** - Comprehensive guide for running benchmarks and interpreting results
- **[Results Template](BENCHMARK_RESULTS_TEMPLATE.md)** - Template for documenting benchmark results

## 🎯 Usage Examples

### Compare CPU vs GPU

```bash
python scripts/load-test.py --compare-instances --output results/cpu-vs-gpu.json
```

### Scalability Test

```bash
python scripts/load-test.py --scalability-test --max-users 200
```

### Cost Analysis

```bash
python scripts/cost-calculator.py --predictions 1000000 --report results/cost-analysis.html
```
