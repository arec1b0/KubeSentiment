# GPU Deployment Guide for KubeSentiment

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration Options](#configuration-options)
4. [Deployment Examples](#deployment-examples)
5. [Multi-GPU Setup](#multi-gpu-setup)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### 1. GPU Nodes in Kubernetes Cluster

Ensure your Kubernetes cluster has GPU-enabled nodes:

```bash
# Check for GPU nodes
kubectl get nodes -o json | jq '.items[] | select(.status.capacity."nvidia.com/gpu" != null) | {name: .metadata.name, gpu: .status.capacity."nvidia.com/gpu"}'
```

### 2. NVIDIA Device Plugin

Install NVIDIA Device Plugin DaemonSet:

```bash
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.5/nvidia-device-plugin.yml
```

Verify installation:

```bash
kubectl get pods -n kube-system | grep nvidia-device-plugin
kubectl describe node <gpu-node-name> | grep nvidia.com/gpu
```

### 3. GPU Node Labels

Label your GPU nodes for proper scheduling:

```bash
# Label by GPU type
kubectl label nodes <node-name> accelerator=nvidia-tesla-t4
kubectl label nodes <node-name> gpu-count=1

# For multi-GPU nodes
kubectl label nodes <node-name> gpu-count=2
kubectl label nodes <node-name> multi-gpu=true
```

### 4. Optional: DCGM Exporter for Monitoring

Install DCGM (Data Center GPU Manager) exporter for detailed GPU metrics:

```bash
helm repo add gpu-helm-charts https://nvidia.github.io/dcgm-exporter/helm-charts
helm install dcgm-exporter gpu-helm-charts/dcgm-exporter \
  --namespace gpu-metrics \
  --create-namespace
```

## Quick Start

### Single GPU Deployment

**1. Create GPU values file:**

```bash
cat > values-gpu.yaml <<EOF
# Enable GPU support
gpu:
  enabled: true
  count: 1
  type: nvidia-tesla-t4

# Reduce replica count for GPU (due to higher cost)
deployment:
  replicaCount: 1

# Adjust HPA for GPU
hpa:
  minReplicas: 1
  maxReplicas: 3
EOF
```

**2. Deploy with GPU support:**

```bash
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  -f values-gpu.yaml \
  --namespace mlops \
  --create-namespace
```

**3. Verify GPU deployment:**

```bash
# Check pod is running on GPU node
kubectl get pods -n mlops -o wide

# Verify GPU allocation
kubectl describe pod <pod-name> -n mlops | grep -A 5 "Limits"

# Check GPU is detected in container
kubectl exec -it <pod-name> -n mlops -- nvidia-smi
```

## Configuration Options

### Basic GPU Configuration

```yaml
# values-gpu.yaml
gpu:
  # Enable/disable GPU support
  enabled: true

  # Number of GPUs per pod
  count: 1

  # GPU vendor (nvidia, amd, intel)
  vendor: nvidia

  # GPU type for node selection
  type: nvidia-tesla-t4

  # GPU resource requests/limits
  resources:
    requests:
      cpu: 2000m
      memory: 8Gi
      nvidia.com/gpu: 1
    limits:
      cpu: 4000m
      memory: 16Gi
      nvidia.com/gpu: 1

  # GPU-specific environment variables
  env:
    GPU_BATCH_SIZE: "64"
    GPU_MAX_BATCH_SIZE: "128"
    GPU_MEMORY_FRACTION: "0.9"
    ENABLE_GPU_OPTIMIZATION: "true"
```

### Multi-GPU Configuration

```yaml
# values-multi-gpu.yaml
gpu:
  enabled: true
  vendor: nvidia
  type: nvidia-tesla-t4

  # Enable multi-GPU support
  multiGpu:
    enabled: true
    gpusPerPod: 2  # Use 2 GPUs per pod

    # Load balancing strategy
    loadBalancing:
      strategy: "gpu-utilization-based"  # or "round-robin", "least-loaded"
      memoryAware: true

  # Larger resources for multi-GPU
  resources:
    requests:
      cpu: 4000m
      memory: 16Gi
    limits:
      cpu: 8000m
      memory: 32Gi

  # Shared memory for multi-GPU (important!)
  volumes:
    sharedMemory:
      enabled: true
      sizeLimit: 4Gi  # Larger for multi-GPU communication

  env:
    MULTI_GPU_ENABLED: "true"
    GPU_COUNT: "2"
    GPU_BATCH_SIZE: "128"  # Larger batches for multi-GPU
    DISTRIBUTED_BACKEND: "nccl"
```

### Advanced GPU Configuration

```yaml
# values-gpu-advanced.yaml
gpu:
  enabled: true
  type: nvidia-a100  # High-end GPU

  # Fine-tuned GPU settings
  env:
    # Memory management
    GPU_MEMORY_FRACTION: "0.95"
    PYTORCH_CUDA_ALLOC_CONF: "max_split_size_mb:512"

    # Model optimizations
    ENABLE_GPU_OPTIMIZATION: "true"
    ENABLE_TORCH_COMPILE: "true"  # PyTorch 2.0+ JIT compilation
    ENABLE_TENSORRT: "false"  # TensorRT optimization

    # Batch processing
    GPU_BATCH_SIZE: "128"
    GPU_MAX_BATCH_SIZE: "256"
    GPU_DYNAMIC_BATCHING: "true"

  # Node affinity for specific GPU types
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: accelerator
            operator: In
            values:
            - nvidia-a100
            - nvidia-a10g
      # Prefer A100 over A10G
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
          - key: accelerator
            operator: In
            values:
            - nvidia-a100

  # Conservative HPA for expensive GPUs
  hpa:
    enabled: true
    minReplicas: 1
    maxReplicas: 2
    behavior:
      scaleUp:
        stabilizationWindowSeconds: 300  # Wait 5 min before scaling up
      scaleDown:
        stabilizationWindowSeconds: 900  # Wait 15 min before scaling down
```

## Deployment Examples

### Example 1: Development with Single T4 GPU

```yaml
# values-dev-gpu.yaml
namespace:
  name: "mlops-dev"

gpu:
  enabled: true
  count: 1
  type: nvidia-tesla-t4

  env:
    GPU_BATCH_SIZE: "32"
    GPU_MEMORY_FRACTION: "0.8"  # Conservative for dev

deployment:
  replicaCount: 1

hpa:
  enabled: false  # Disable autoscaling in dev

# Use smaller model cache
modelPersistence:
  enabled: true
  size: 5Gi
```

**Deploy:**
```bash
helm upgrade --install mlops-sentiment-dev ./helm/mlops-sentiment \
  -f values-dev-gpu.yaml \
  --namespace mlops-dev \
  --create-namespace
```

### Example 2: Production with Multi-GPU (2x A10G)

```yaml
# values-prod-multi-gpu.yaml
namespace:
  name: "mlops-prod"

gpu:
  enabled: true
  vendor: nvidia
  type: nvidia-a10g

  multiGpu:
    enabled: true
    gpusPerPod: 2
    loadBalancing:
      strategy: "gpu-utilization-based"
      memoryAware: true

  resources:
    requests:
      cpu: 4000m
      memory: 16Gi
    limits:
      cpu: 8000m
      memory: 32Gi

  volumes:
    sharedMemory:
      enabled: true
      sizeLimit: 4Gi

  env:
    MULTI_GPU_ENABLED: "true"
    GPU_COUNT: "2"
    GPU_BATCH_SIZE: "128"
    GPU_MAX_BATCH_SIZE: "256"
    ENABLE_GPU_OPTIMIZATION: "true"

deployment:
  replicaCount: 2

hpa:
  enabled: true

# Production-grade persistence
modelPersistence:
  enabled: true
  size: 20Gi
  storageClassName: "fast-ssd"

# Production monitoring
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 15s
```

**Deploy:**
```bash
helm upgrade --install mlops-sentiment-prod ./helm/mlops-sentiment \
  -f values-prod.yaml \
  -f values-prod-multi-gpu.yaml \
  --namespace mlops-prod \
  --create-namespace
```

### Example 3: Hybrid CPU + GPU Deployment

Deploy both CPU and GPU variants for cost optimization:

**CPU Deployment (handles baseline traffic):**
```bash
helm upgrade --install mlops-sentiment-cpu ./helm/mlops-sentiment \
  -f values-prod.yaml \
  --set deployment.replicaCount=3 \
  --set hpa.minReplicas=2 \
  --set hpa.maxReplicas=10 \
  --namespace mlops-prod
```

**GPU Deployment (handles peak/batch traffic):**
```bash
helm upgrade --install mlops-sentiment-gpu ./helm/mlops-sentiment \
  -f values-prod.yaml \
  --set gpu.enabled=true \
  --set gpu.type=nvidia-tesla-t4 \
  --set deployment.replicaCount=1 \
  --set hpa.minReplicas=1 \
  --set hpa.maxReplicas=3 \
  --set service.type=ClusterIP \
  --set service.port=8080 \
  --namespace mlops-prod
```

**Route traffic with Istio VirtualService:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: mlops-sentiment-routing
  namespace: mlops-prod
spec:
  hosts:
  - mlops-sentiment.local
  http:
  # Send batch requests to GPU
  - match:
    - uri:
        prefix: "/api/v1/batch"
    route:
    - destination:
        host: mlops-sentiment-gpu
        port:
          number: 8080
      weight: 100
  # Send regular traffic to CPU with GPU fallback
  - route:
    - destination:
        host: mlops-sentiment-cpu
        port:
          number: 80
      weight: 80
    - destination:
        host: mlops-sentiment-gpu
        port:
          number: 8080
      weight: 20
```

### Example 4: Spot/Preemptible GPU Instances

Save costs using spot instances with proper redundancy:

```yaml
# values-spot-gpu.yaml
gpu:
  enabled: true
  type: nvidia-tesla-t4

  # Tolerate spot instance interruptions
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
  - key: cloud.google.com/gke-preemptible
    operator: Equal
    value: "true"
    effect: NoSchedule
  - key: eks.amazonaws.com/capacityType
    operator: Equal
    value: "SPOT"
    effect: NoSchedule

  # Prefer spot instances
  affinity:
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
          - key: cloud.google.com/gke-preemptible
            operator: In
            values:
            - "true"

# More aggressive scaling for spot
hpa:
  enabled: true
  minReplicas: 2  # Maintain redundancy
  maxReplicas: 6

# Pod disruption budget for spot interruptions
pdb:
  enabled: true
  minAvailable: 1  # Always keep 1 pod running
```

## Multi-GPU Setup

### Architecture Options

#### 1. Model Parallelism (Single Large Model)
For very large models that don't fit on single GPU:

```yaml
gpu:
  multiGpu:
    enabled: true
    gpusPerPod: 2
    topology: "single-numa-node"  # Keep GPUs close for fast communication

  env:
    MULTI_GPU_ENABLED: "true"
    GPU_COUNT: "2"
    MULTI_GPU_STRATEGY: "model-parallel"
```

#### 2. Data Parallelism (Batch Distribution)
For high throughput with batch processing:

```yaml
gpu:
  multiGpu:
    enabled: true
    gpusPerPod: 2
    loadBalancing:
      strategy: "gpu-utilization-based"

  env:
    MULTI_GPU_ENABLED: "true"
    GPU_COUNT: "2"
    MULTI_GPU_STRATEGY: "data-parallel"
    GPU_BATCH_SIZE: "64"  # Per GPU
    DISTRIBUTED_BACKEND: "nccl"  # NCCL for NVIDIA
```

### Verifying Multi-GPU

```bash
# Check GPUs are allocated
kubectl describe pod <pod-name> -n mlops | grep "nvidia.com/gpu"

# Verify GPUs visible in container
kubectl exec -it <pod-name> -n mlops -- nvidia-smi -L

# Check GPU utilization
kubectl exec -it <pod-name> -n mlops -- nvidia-smi dmon -s u -c 1
```

## Monitoring

### GPU Metrics Dashboard

Create Grafana dashboard with key GPU metrics:

```yaml
# Key metrics to monitor
- GPU Utilization (%)
- GPU Memory Used (MB)
- GPU Temperature (°C)
- GPU Power Usage (W)
- Tensor Core Utilization (%)
- Requests per Second per GPU
- Average Batch Size
- Cost per Million Requests
```

### Prometheus Rules

Add alerting rules for GPU issues:

```yaml
# gpu-alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: gpu-alerts
  namespace: mlops
spec:
  groups:
  - name: gpu
    interval: 30s
    rules:
    # Low GPU utilization (waste of money)
    - alert: LowGPUUtilization
      expr: avg(DCGM_FI_DEV_GPU_UTIL) < 40
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: "Low GPU utilization detected"
        description: "GPU utilization below 40% for 15 minutes. Consider scaling down."

    # High GPU memory usage (risk of OOM)
    - alert: HighGPUMemory
      expr: (DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_FREE) > 0.90
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "GPU memory usage above 90%"
        description: "GPU memory usage critical. Risk of OOM errors."

    # GPU temperature too high
    - alert: HighGPUTemperature
      expr: DCGM_FI_DEV_GPU_TEMP > 85
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "GPU temperature above 85°C"
        description: "GPU overheating detected. Check cooling."

    # Low batch efficiency
    - alert: LowBatchEfficiency
      expr: avg(inference_batch_size) < 16
      for: 15m
      labels:
        severity: info
      annotations:
        summary: "Average batch size below 16"
        description: "GPU not efficiently utilized. Batch size too small."
```

### PromQL Queries

Useful queries for GPU monitoring:

```promql
# Average GPU utilization across all GPUs
avg(DCGM_FI_DEV_GPU_UTIL)

# GPU memory utilization percentage
(DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_FREE) * 100

# Cost per million requests (estimated)
(sum(kube_pod_container_resource_requests{resource="nvidia_com_gpu"}) * <gpu_hourly_cost> * 24 * 30) /
(sum(rate(http_requests_total[30d])) * 30 * 24 * 3600) * 1000000

# GPU throughput (inferences per second)
rate(inference_requests_total{gpu="true"}[5m])

# Average batch size
avg(inference_batch_size{gpu="true"})
```

## Troubleshooting

### Issue 1: Pod Stuck in Pending (No GPU Available)

**Symptoms:**
```
Events:
  Warning  FailedScheduling  pod didn't trigger scale-up: 1 Insufficient nvidia.com/gpu
```

**Solutions:**
1. Check GPU nodes exist:
   ```bash
   kubectl get nodes -o json | jq '.items[] | select(.status.capacity."nvidia.com/gpu" != null)'
   ```

2. Verify NVIDIA Device Plugin running:
   ```bash
   kubectl get pods -n kube-system | grep nvidia
   ```

3. Check node labels match:
   ```bash
   kubectl describe node <gpu-node> | grep accelerator
   ```

4. Verify GPU not already allocated:
   ```bash
   kubectl describe node <gpu-node> | grep -A 5 "Allocated resources"
   ```

### Issue 2: CUDA Out of Memory (OOM)

**Symptoms:**
```
RuntimeError: CUDA out of memory. Tried to allocate X MiB (GPU 0; Y GiB total capacity)
```

**Solutions:**
1. Reduce GPU memory fraction:
   ```yaml
   gpu:
     env:
       GPU_MEMORY_FRACTION: "0.7"  # Reduce from 0.9
   ```

2. Decrease batch size:
   ```yaml
   gpu:
     env:
       GPU_BATCH_SIZE: "32"  # Reduce from 64
   ```

3. Enable gradient checkpointing (in model code):
   ```python
   model.gradient_checkpointing_enable()
   ```

4. Use mixed precision (FP16):
   ```yaml
   gpu:
     env:
       ENABLE_MIXED_PRECISION: "true"
   ```

### Issue 3: Low GPU Utilization

**Symptoms:**
- GPU utilization <50%
- CPU bottleneck
- Small batch sizes

**Solutions:**
1. Increase batch size:
   ```yaml
   gpu:
     env:
       GPU_BATCH_SIZE: "128"  # Increase
       GPU_DYNAMIC_BATCHING: "true"
   ```

2. Enable multi-threading for data loading:
   ```yaml
   deployment:
     env:
       DATALOADER_NUM_WORKERS: "4"
   ```

3. Use ONNX or TensorRT optimization:
   ```yaml
   gpu:
     env:
       ENABLE_TENSORRT: "true"
   ```

4. Check CPU is not bottleneck:
   ```bash
   kubectl top pod <pod-name> -n mlops
   ```

### Issue 4: Multi-GPU Communication Failure

**Symptoms:**
```
RuntimeError: NCCL error: unhandled system error
```

**Solutions:**
1. Enable shared memory:
   ```yaml
   gpu:
     volumes:
       sharedMemory:
         enabled: true
         sizeLimit: 4Gi
   ```

2. Check GPUs are on same node:
   ```yaml
   gpu:
     multiGpu:
       topology: "single-numa-node"
   ```

3. Verify NCCL is working:
   ```bash
   kubectl exec -it <pod-name> -- python -c "import torch; print(torch.cuda.nccl.version())"
   ```

### Issue 5: High GPU Costs

**Symptoms:**
- Cloud bill higher than expected
- Low requests-per-dollar ratio

**Solutions:**
1. Use spot/preemptible instances (60-90% savings)
2. Right-size GPU type (T4 vs A100)
3. Implement autoscaling with conservative limits
4. Use hybrid CPU/GPU deployment
5. Enable batch processing to increase throughput
6. Monitor cost-per-request metrics

## Best Practices

### 1. Start Small, Scale Gradually
- Begin with 1 GPU replica
- Monitor utilization for 1 week
- Scale based on actual metrics

### 2. Use Appropriate GPU Type
- **T4**: Best price/performance for inference (<$0.50/hr)
- **A10G**: High throughput (2x T4 performance, 2x cost)
- **V100/A100**: Maximum performance (4-6x T4, 6-10x cost)

### 3. Implement Cost Controls
- Set `maxReplicas` limits in HPA
- Use PodDisruptionBudget
- Monitor cost-per-request metrics
- Set budget alerts in cloud provider

### 4. Optimize for Batch Inference
- Use dynamic batching
- Target batch sizes 32-128
- Enable async batch processing

### 5. Plan for Failures
- Use spot instances with on-demand fallback
- Maintain minAvailable: 1 in PDB
- Implement graceful shutdown handlers
- Test failover scenarios

## Next Steps

1. **Run Cost Analysis:** See [GPU_COST_ANALYSIS.md](GPU_COST_ANALYSIS.md)
2. **Deploy Dev Environment:** Start with Example 1
3. **Benchmark Performance:** Compare CPU vs GPU latency/throughput
4. **Monitor Costs:** Track cost-per-request for 1-2 weeks
5. **Scale to Production:** Use Example 2 or 3 based on requirements

---

**Need Help?**
- Check [GPU_COST_ANALYSIS.md](GPU_COST_ANALYSIS.md) for cost optimization
- See [Troubleshooting](#troubleshooting) section above
- Review NVIDIA GPU documentation: https://docs.nvidia.com/datacenter/cloud-native/
