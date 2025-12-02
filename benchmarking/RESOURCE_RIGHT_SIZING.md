# Resource Right-Sizing Guide

This guide explains how to analyze benchmark results and optimize Kubernetes resource requests and limits for the MLOps Sentiment Analysis service.

## Overview

Resource right-sizing is critical for:
- **Cost Optimization**: Proper requests allow high bin-packing efficiency
- **Stability**: Equal memory requests/limits prevent OOM kills
- **Performance**: Appropriate limits handle traffic bursts without throttling

## Current Resource Settings

### CPU Resources

**Strategy**:
- **Requests**: Set to average usage (~40-50% of limit) to allow high bin-packing
- **Limits**: Set to P95 usage + 20% buffer to handle bursts (startup, traffic spikes)

**Rationale**:
- ONNX inference is CPU-bound but has predictable average usage
- Startup and traffic bursts require higher CPU temporarily
- Lower requests allow Kubernetes to pack more pods per node

### Memory Resources

**Strategy**:
- **Requests = Limits**: Set to P95 usage + 10% buffer
- **Equal values**: Prevents OOM kills and ensures stable scheduling

**Rationale**:
- Memory usage is relatively stable for inference workloads
- OOM kills cause pod restarts and service disruption
- Equal requests/limits ensure predictable scheduling

## Environment-Specific Settings

### Development (`values-dev.yaml`)
```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 200m      # ~40% of limit
    memory: 512Mi  # Equal to limit
```

### Staging (`values-staging.yaml`)
```yaml
resources:
  limits:
    cpu: 1000m
    memory: 768Mi
  requests:
    cpu: 400m      # ~40% of limit
    memory: 768Mi  # Equal to limit
```

### Production (`values-prod.yaml`)
```yaml
resources:
  limits:
    cpu: 2000m
    memory: 1536Mi
  requests:
    cpu: 800m      # ~40% of limit
    memory: 1536Mi # Equal to limit
```

### GPU Workloads

GPU workloads follow similar patterns but with higher CPU limits for model loading/preprocessing:

```yaml
resources:
  limits:
    cpu: 4000m     # Higher for preprocessing
    memory: 16Gi   # Equal to requests
  requests:
    cpu: 2000m     # ~50% of limit
    memory: 16Gi   # Equal to limits
```

## Analyzing Benchmark Results

### Step 1: Run Benchmarks

Run benchmarks with resource monitoring enabled:

```bash
cd benchmarking
./quick-benchmark.sh -t cpu-medium -u 20 -d 300
```

This generates `results/resource_metrics_*.json` files.

### Step 2: Analyze Results

Use the analysis script to extract recommendations:

```bash
python scripts/analyze-resources.py \
  --resource-file results/resource_metrics_cpu-medium.json \
  --current-cpu-limit 1000m \
  --current-memory-limit 1Gi \
  --helm-values \
  --environment production \
  --output results/resource_analysis.json
```

### Step 3: Review Recommendations

The script outputs:
- **Statistics**: Average, P95, P99, and max CPU/memory usage
- **Recommendations**: Suggested CPU and memory requests/limits
- **Helm Values**: Ready-to-use YAML snippet

### Step 4: Update Helm Values

1. Review the recommendations against current settings
2. Update the appropriate `values-*.yaml` file
3. Test in staging before production deployment

## Example Analysis Output

```
RESOURCE ANALYSIS SUMMARY
============================================================

CPU Statistics:
  Average: 42.3%
  P95:     78.5%
  P99:     89.2%
  Max:     95.1%
  Samples: 120

CPU Recommendations:
  Request: 400m (0.40 cores)
  Limit:   1000m (1.00 cores)

Memory Statistics:
  Average: 58.2%
  P95:     82.4%
  Max:     88.7%
  Avg Used: 0.45 GB
  P95 Used: 0.63 GB
  Max Used: 0.68 GB

Memory Recommendations:
  Request: 768Mi (0.75 GB)
  Limit:   768Mi (0.75 GB)
```

## Best Practices

### 1. Regular Benchmarking

Run benchmarks regularly to catch resource usage changes:
- After model updates
- After code optimizations
- When traffic patterns change
- Quarterly reviews

### 2. Monitor Actual Usage

Use Prometheus/Grafana to monitor:
- CPU utilization vs. requests/limits
- Memory utilization vs. requests/limits
- OOM kill events
- Pod evictions

### 3. Gradual Adjustments

- Start with conservative settings
- Monitor for 24-48 hours after changes
- Adjust incrementally based on metrics
- Document changes and rationale

### 4. Environment-Specific Tuning

- **Development**: Minimal resources for cost savings
- **Staging**: Production-like but with safety margins
- **Production**: Optimized based on actual benchmark data

## Troubleshooting

### High CPU Throttling

**Symptoms**: High CPU throttling metrics, slow response times

**Solution**: Increase CPU limits while keeping requests low

```yaml
resources:
  limits:
    cpu: 1500m  # Increase limit
  requests:
    cpu: 400m   # Keep request low
```

### OOM Kills

**Symptoms**: Pod restarts, `OOMKilled` status

**Solution**: Increase memory requests/limits equally

```yaml
resources:
  limits:
    memory: 1024Mi  # Increase both
  requests:
    memory: 1024Mi  # Keep equal
```

### Low Bin-Packing Efficiency

**Symptoms**: Many nodes with low utilization, high costs

**Solution**: Reduce CPU requests (if safe)

```yaml
resources:
  requests:
    cpu: 300m  # Reduce from 400m
```

## Integration with CI/CD

Add resource analysis to your CI/CD pipeline:

```yaml
# .github/workflows/benchmark-analysis.yml
- name: Analyze Resources
  run: |
    python benchmarking/scripts/analyze-resources.py \
      --resource-file results/resource_metrics.json \
      --helm-values \
      --output resource-recommendations.json

    # Compare with current values
    python scripts/compare-resources.py \
      --current helm/mlops-sentiment/values-prod.yaml \
      --recommended resource-recommendations.json
```

## References

- [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [ADR-001: ONNX Model Optimization](../docs/architecture/decisions/001-use-onnx-for-model-optimization.md)
- [Benchmarking Guide](./README.md)

## Related Files

- `benchmarking/scripts/analyze-resources.py` - Analysis script
- `benchmarking/scripts/resource-monitor.py` - Resource monitoring
- `helm/mlops-sentiment/values-*.yaml` - Helm values files
