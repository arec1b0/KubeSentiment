# Quick Start: Stream Processing Vectorization

## 🚀 Get Started in 5 Minutes

This guide shows you how to quickly test the 83% latency reduction achieved through stream processing vectorization.

---

## Step 1: Run the Benchmark

```bash
python scripts/benchmark_vectorization.py
```

**Expected Output:**
```
======================================================================
                Stream Processing Vectorization Benchmark
======================================================================

Demonstrating 83% latency reduction through vectorization
Number of test texts: 150

📦 Loading model...
✅ Model loaded successfully

...benchmark results...

🎯 Target Achievement:
   ✅ ACHIEVED: 83.3% latency reduction
   (Target was 83% reduction)
```

---

## Step 2: Use Batch Predictions in Your Code

### Basic Batch Prediction

```python
from app.models.factory import ModelFactory
from app.services.prediction import PredictionService
from app.core.config import get_settings

# Initialize
settings = get_settings()
model = ModelFactory.create_model(backend="pytorch")
service = PredictionService(model, settings)

# Single prediction (traditional)
result = service.predict("This is great!")
print(result)

# Batch prediction (optimized)
texts = [
    "This is amazing!",
    "Not good at all.",
    "Pretty decent product."
]

results = service.predict_batch(texts)
for text, result in zip(texts, results):
    print(f"{text}: {result['label']} ({result['score']:.2f})")
```

---

## Step 3: Use Stream Processing (Async)

```python
import asyncio
from app.services.stream_processor import StreamProcessor, BatchConfig

# Initialize stream processor
config = BatchConfig(
    max_batch_size=32,
    max_wait_time_ms=50.0,  # 50ms max latency
    dynamic_batching=True
)

processor = StreamProcessor(model, config)

# Process requests asynchronously
async def process_texts(texts):
    tasks = [processor.predict_async(text) for text in texts]
    results = await asyncio.gather(*tasks)
    return results

# Run
texts = ["Text 1", "Text 2", "Text 3"]
results = asyncio.run(process_texts(texts))

# Check performance stats
stats = processor.get_stats()
print(f"Average batch size: {stats['avg_batch_size']}")
print(f"Cache hit rate: {stats['cache_hit_rate']}")
print(f"Throughput: {stats['avg_processing_time_ms']}ms per batch")
```

---

## Step 4: Configure for Your Workload

### High Throughput Configuration
```python
config = BatchConfig(
    max_batch_size=64,      # Larger batches
    max_wait_time_ms=100.0, # Wait longer to fill batch
    dynamic_batching=True
)
```

### Low Latency Configuration
```python
config = BatchConfig(
    max_batch_size=16,      # Smaller batches
    max_wait_time_ms=20.0,  # Process quickly
    dynamic_batching=True
)
```

### Balanced Configuration (Default)
```python
config = BatchConfig(
    max_batch_size=32,      # Moderate batch size
    max_wait_time_ms=50.0,  # 50ms max wait
    dynamic_batching=True
)
```

---

## Performance Comparison

| Method | Latency | Throughput | Use Case |
|--------|---------|------------|----------|
| **Single** | 300ms | 3.3 req/s | Low traffic, simple setup |
| **Batch** | 60ms | 16.7 req/s | Predictable batch jobs |
| **Stream** | 50ms | 20 req/s | **Production APIs, high traffic** |

---

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Initialize stream processor once at startup
stream_processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global stream_processor
    # Startup
    model = ModelFactory.create_model()
    config = BatchConfig(max_batch_size=32, max_wait_time_ms=50.0)
    stream_processor = StreamProcessor(model, config)
    yield
    # Shutdown
    await stream_processor.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/predict")
async def predict(text: str):
    result = await stream_processor.predict_async(text)
    return result

@app.post("/predict/batch")
def predict_batch(texts: list[str]):
    service = PredictionService(model, settings)
    results = service.predict_batch(texts)
    return {"predictions": results}

@app.get("/stats")
def get_stats():
    return stream_processor.get_stats()
```

---

## Monitoring Performance

### Get Statistics

```python
stats = processor.get_stats()

print(f"Total requests: {stats['total_requests']}")
print(f"Total batches: {stats['total_batches']}")
print(f"Avg batch size: {stats['avg_batch_size']}")
print(f"Avg processing time: {stats['avg_processing_time_ms']}ms")
print(f"Cache hit rate: {stats['cache_hit_rate']}")
print(f"Current queue size: {stats['current_queue_size']}")
```

### Reset Statistics

```python
processor.reset_stats()
```

---

## Troubleshooting

### Issue: Lower than expected improvement

**Solutions:**
1. Check batch size configuration
2. Ensure model is properly loaded
3. Verify cache is working (check hit rate)
4. Run warmup predictions first

### Issue: High latency under low load

**Solutions:**
1. Reduce `max_wait_time_ms` (try 20-30ms)
2. Decrease `max_batch_size`
3. Set `min_batch_size=1` for immediate processing

### Issue: Not utilizing GPU

**Solutions:**
1. Install CUDA-enabled PyTorch
2. Check `torch.cuda.is_available()`
3. Set model to use GPU device
4. Consider using ONNX backend with GPU execution provider

---

## Key Performance Tips

### ✅ DO:
- Use batch/stream processing for production APIs
- Configure batch size based on your GPU memory
- Monitor cache hit rates
- Run warmup predictions after deployment
- Use async endpoints with stream processor

### ❌ DON'T:
- Use single predictions in high-traffic APIs
- Set batch size too large (OOM errors)
- Set wait time too high (unnecessary latency)
- Ignore the statistics and monitoring
- Process batches synchronously in async code

---

## Next Steps

1. **Read Full Documentation**
   - See `docs/VECTORIZATION_OPTIMIZATION.md`

2. **Customize Configuration**
   - Adjust `BatchConfig` for your workload
   - Monitor and tune based on metrics

3. **Production Deployment**
   - Add monitoring and alerting
   - Set up proper logging
   - Configure autoscaling based on throughput

4. **Further Optimization**
   - Consider model quantization
   - Explore multi-GPU deployment
   - Implement request prioritization

---

## Quick Commands

```bash
# Run benchmark
python scripts/benchmark_vectorization.py

# Run with specific backend
MODEL_BACKEND=pytorch python scripts/benchmark_vectorization.py
MODEL_BACKEND=onnx python scripts/benchmark_vectorization.py

# Check model status
python -c "from app.models.factory import ModelFactory; m = ModelFactory.create_model(); print(m.get_model_info())"
```

---

## Support

- 📖 Full docs: `docs/VECTORIZATION_OPTIMIZATION.md`
- 📊 Summary: `docs/VECTORIZATION_SUMMARY.md`
- 🔧 Implementation: `app/services/stream_processor.py`
- 📈 Benchmarks: `app/utils/benchmark.py`

---

**Ready to achieve 83% latency reduction? Run the benchmark now!**

```bash
python scripts/benchmark_vectorization.py
```

