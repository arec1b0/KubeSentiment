# ADR 001: Use ONNX for Model Optimization

**Status:** Accepted
**Date:** 2024-01-15
**Authors:** KubeSentiment Team

## Context

The KubeSentiment service needs to provide fast, efficient sentiment analysis inference in a production environment. PyTorch models, while powerful and easy to develop with, have several limitations in production:

1. **Cold-start time**: Loading PyTorch models takes 5-8 seconds
2. **Memory footprint**: PyTorch runtime requires significant memory
3. **Inference speed**: PyTorch inference is slower than optimized runtimes
4. **Deployment size**: PyTorch dependencies increase container image size

We need a solution that:
- Reduces cold-start time to < 100ms
- Minimizes memory usage
- Maximizes inference throughput
- Maintains model accuracy
- Remains compatible with our existing PyTorch training pipeline

## Decision

We will use **ONNX (Open Neural Network Exchange)** Runtime for production model inference, while maintaining PyTorch for model training and development.

### Implementation Strategy

1. **Dual Backend Support**: Support both PyTorch and ONNX backends
   - PyTorch for development and testing
   - ONNX for production deployment

2. **Model Conversion**: Convert trained PyTorch models to ONNX format
   - Use `torch.onnx.export()` for conversion
   - Apply ONNX Runtime optimizations
   - Validate accuracy post-conversion

3. **Runtime Optimization**: Leverage ONNX Runtime features
   - Graph optimization (constant folding, operator fusion)
   - Quantization (INT8) for reduced memory
   - Multi-threading for CPU inference

## Consequences

### Positive

- **160x faster cold-start**: Reduced from 8s to 50ms
- **40% faster inference**: P99 latency reduced from 150ms to 90ms
- **50% lower memory usage**: ONNX Runtime uses less memory than PyTorch
- **Smaller container images**: Reduced from 1.2GB to 800MB
- **Better CPU utilization**: ONNX Runtime optimized for CPU inference
- **Cross-framework compatibility**: Can export models from other frameworks

### Negative

- **Additional conversion step**: Must convert models from PyTorch to ONNX
- **Limited operator support**: Some PyTorch operations not supported in ONNX
- **Debugging complexity**: Harder to debug ONNX models vs. PyTorch
- **Maintenance overhead**: Must maintain two model loading paths
- **Version compatibility**: ONNX version must match PyTorch export version

### Neutral

- **Accuracy**: No significant accuracy loss observed (< 0.1% difference)
- **Development workflow**: Unchanged for model training and experimentation
- **CI/CD**: Additional step for model conversion and validation

## Alternatives Considered

### Alternative 1: TensorFlow/TensorFlow Lite

**Pros:**
- TensorFlow Lite optimized for mobile and edge devices
- Good tooling and ecosystem
- Strong optimization support

**Cons:**
- Would require retraining models in TensorFlow
- Less flexible than ONNX for cross-framework support
- TensorFlow dependencies larger than ONNX Runtime

**Rejected because**: Would require significant rework of existing PyTorch models and training pipeline.

### Alternative 2: TorchScript

**Pros:**
- Native PyTorch optimization
- No conversion step required
- Preserves full PyTorch operator support

**Cons:**
- Still slower than ONNX Runtime
- Larger memory footprint than ONNX
- Cold-start time only ~2x better than standard PyTorch

**Rejected because**: Did not meet our performance targets for cold-start time and memory usage.

### Alternative 3: NVIDIA TensorRT

**Pros:**
- Excellent GPU inference performance
- Advanced optimizations for NVIDIA hardware

**Cons:**
- GPU-only solution (we need CPU support)
- NVIDIA hardware dependency
- More complex setup and deployment

**Rejected because**: We prioritize CPU inference for cost-effectiveness, and TensorRT is GPU-specific.

### Alternative 4: Keep PyTorch Only

**Pros:**
- Simplest solution
- No conversion step
- Full operator support

**Cons:**
- Does not meet performance requirements
- High cold-start latency unacceptable for production
- Higher infrastructure costs due to slower inference

**Rejected because**: Production performance requirements not met.

## Implementation Details

### Model Conversion

```python
import torch
import onnx
from optimum.onnxruntime import ORTModelForSequenceClassification

# Convert PyTorch model to ONNX
model = AutoModelForSequenceClassification.from_pretrained(model_name)
dummy_input = tokenizer("test", return_tensors="pt")

torch.onnx.export(
    model,
    (dummy_input['input_ids'], dummy_input['attention_mask']),
    "model.onnx",
    input_names=['input_ids', 'attention_mask'],
    output_names=['logits'],
    dynamic_axes={
        'input_ids': {0: 'batch', 1: 'sequence'},
        'attention_mask': {0: 'batch', 1: 'sequence'}
    },
    opset_version=14
)

# Optimize ONNX model
from onnxruntime import InferenceSession, SessionOptions
from onnxruntime.transformers import optimizer

optimized_model = optimizer.optimize_model("model.onnx")
optimized_model.save_model_to_file("model_optimized.onnx")
```

### Runtime Configuration

```python
# ONNX Runtime session options
session_options = onnxruntime.SessionOptions()
session_options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
session_options.intra_op_num_threads = 4
session_options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL

# Create inference session
session = onnxruntime.InferenceSession("model_optimized.onnx", session_options)
```

## Validation

### Accuracy Validation

- Compared predictions on 10,000 test samples
- Maximum difference: 0.08%
- Average difference: 0.02%
- Conclusion: No significant accuracy loss

### Performance Benchmarks

| Metric | PyTorch | ONNX | Improvement |
|--------|---------|------|-------------|
| Cold-start | 8000ms | 50ms | 160x |
| P50 Latency | 95ms | 60ms | 1.6x |
| P99 Latency | 150ms | 90ms | 1.7x |
| Throughput (RPS) | 12 | 40 | 3.3x |
| Memory Usage | 2.1GB | 1.1GB | 1.9x |

## Migration Path

1. **Phase 1** (Complete): Implement ONNX backend alongside PyTorch
2. **Phase 2** (Complete): Test ONNX in staging environment
3. **Phase 3** (Complete): Deploy ONNX to production with feature flag
4. **Phase 4** (In Progress): Make ONNX the default backend
5. **Phase 5** (Future): Deprecate PyTorch backend for production

## Monitoring

Track key metrics to ensure ONNX performance:
- `ml_inference_duration_seconds{backend="onnx"}`
- `ml_model_load_duration_seconds{backend="onnx"}`
- `ml_prediction_accuracy_score{backend="onnx"}`

## References

- [ONNX Runtime Documentation](https://onnxruntime.ai/)
- [PyTorch ONNX Export](https://pytorch.org/docs/stable/onnx.html)
- [Model Persistence Documentation](../../MODEL_PERSISTENCE.md)
- [Performance Benchmarking Results](../../benchmarking/README.md)
- [ONNX Model Zoo](https://github.com/onnx/models)

## Related ADRs

- [ADR 004: Use FastAPI as Web Framework](004-use-fastapi-as-web-framework.md) - Framework that hosts ONNX inference
- [ADR 005: Use Helm for Kubernetes Deployments](005-use-helm-for-kubernetes-deployments.md) - Deployment of ONNX models
- [ADR 010: Refactor Model Hierarchy](010-refactor-model-hierarchy.md) - Refactoring the model implementation structure

## Change History

- 2024-01-15: Initial decision
- 2024-02-20: Updated with production metrics
- 2025-10-30: Added to ADR repository
