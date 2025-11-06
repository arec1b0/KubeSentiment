# GPU Support for KubeSentiment

## Quick Start

### Single GPU Deployment
```bash
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  -f values-gpu-single.yaml \
  --namespace mlops \
  --create-namespace
```

### Multi-GPU Deployment
```bash
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  -f values-gpu-multi.yaml \
  --namespace mlops \
  --create-namespace
```

### Spot/Preemptible GPU Deployment (60-90% cost savings)
```bash
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  -f values-gpu-spot.yaml \
  --namespace mlops \
  --create-namespace
```

## Configuration Files

| File | Description | Use Case | Cost (AWS) |
|------|-------------|----------|------------|
| `values-gpu-single.yaml` | Single T4 GPU | Medium-scale production (500-2000 req/s) | ~$382/month |
| `values-gpu-multi.yaml` | Multi-GPU (2x A10G) | High-scale production (2000-5000 req/s) | ~$881/month |
| `values-gpu-spot.yaml` | Spot T4 GPU | Cost-optimized production | ~$115/month |

## Prerequisites

1. **GPU Nodes:** Kubernetes cluster with GPU-enabled nodes
2. **NVIDIA Device Plugin:** Install with:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.5/nvidia-device-plugin.yml
   ```
3. **GPU Node Labels:** Label nodes with GPU type:
   ```bash
   kubectl label nodes <node-name> accelerator=nvidia-tesla-t4
   ```

## Features

### GPU Scheduling & Load Balancing
- Automatic GPU selection based on utilization
- Multi-GPU support with NCCL backend
- Load balancing strategies: round-robin, least-loaded, utilization-based

### Batch Inference Optimization
- Dynamic batch sizing (16-256)
- GPU memory-aware batching
- Multi-GPU batch distribution
- Automatic throughput optimization

### Cost Optimization
- Spot/preemptible instance support
- Hybrid CPU/GPU deployments
- Conservative autoscaling for GPU pods
- Cost-per-request monitoring

## Performance

| Hardware | Throughput | Latency (p95) | Cost per M requests |
|----------|------------|---------------|---------------------|
| CPU (c6i.xlarge) | 150 req/s | 260ms | $82.32 |
| GPU (T4) | 800 req/s | 28ms | $47.79 |
| GPU (A10G) | 1,500 req/s | 18ms | $48.76 |
| Multi-GPU (2x A10G) | 3,000 req/s | 15ms | $29.37 |

## Documentation

- **[GPU Deployment Guide](../../docs/GPU_DEPLOYMENT_GUIDE.md)** - Complete setup instructions
- **[GPU Cost Analysis](../../docs/GPU_COST_ANALYSIS.md)** - Detailed cost comparison and ROI

## Monitoring

### Verify GPU Deployment
```bash
# Check pod is on GPU node
kubectl get pods -n mlops -o wide

# Verify GPU allocation
kubectl describe pod <pod-name> -n mlops | grep nvidia.com/gpu

# Check GPU status
kubectl exec -it <pod-name> -n mlops -- nvidia-smi
```

### GPU Metrics
Install DCGM Exporter for detailed GPU metrics:
```bash
helm repo add gpu-helm-charts https://nvidia.github.io/dcgm-exporter/helm-charts
helm install dcgm-exporter gpu-helm-charts/dcgm-exporter \
  --namespace gpu-metrics \
  --create-namespace
```

Key metrics to monitor:
- GPU Utilization (target: >70%)
- GPU Memory Usage (alert if >90%)
- Batch Size (target: >32 for GPU)
- Cost per Million Requests

## Troubleshooting

### Pod stuck in Pending
```bash
# Check GPU availability
kubectl describe node <gpu-node> | grep nvidia.com/gpu
```

### CUDA Out of Memory
Reduce memory fraction or batch size in values file:
```yaml
gpu:
  env:
    GPU_MEMORY_FRACTION: "0.7"  # Reduce from 0.9
    GPU_BATCH_SIZE: "32"  # Reduce from 64
```

### Low GPU Utilization
Increase batch size for better GPU efficiency:
```yaml
gpu:
  env:
    GPU_BATCH_SIZE: "128"
    GPU_DYNAMIC_BATCHING: "true"
```

## Support

For issues and questions:
- See full [GPU Deployment Guide](../../docs/GPU_DEPLOYMENT_GUIDE.md)
- Check [Troubleshooting section](../../docs/GPU_DEPLOYMENT_GUIDE.md#troubleshooting)
- Open an issue on GitHub
