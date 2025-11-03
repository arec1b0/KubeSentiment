# Application-Level Chaos Engineering

This directory contains Python code for injecting chaos at the application level, complementing infrastructure-level chaos experiments.

## Components

### 1. `chaos_middleware.py`
FastAPI middleware for injecting various types of failures:
- **Latency**: Random delays (100ms - 5s)
- **HTTP Errors**: 500, 503, 504 responses
- **Exceptions**: Raised application exceptions
- **Timeouts**: Request timeout simulation
- **Rate Limiting**: 429 responses with retry headers
- **Partial Failures**: Degraded responses

### 2. `chaos_routes.py`
REST API endpoints for runtime chaos control:
- `GET /chaos/status` - View chaos statistics
- `POST /chaos/enable` - Enable/configure chaos
- `POST /chaos/disable` - Disable chaos
- `PUT /chaos/config` - Update configuration
- `GET /chaos/types` - List available chaos types

## Integration

### Step 1: Add to Application

Add the middleware to your FastAPI application in `app/main.py`:

```python
from chaos.app_chaos.chaos_middleware import (
    ChaosMiddleware,
    ChaosConfig,
    ChaosType,
    set_chaos_middleware
)
from chaos.app_chaos.chaos_routes import router as chaos_router

# Create chaos configuration
chaos_config = ChaosConfig(
    enabled=False,  # Disabled by default
    chaos_probability=0.1,  # 10% of requests
    latency_ms_min=100,
    latency_ms_max=3000,
    error_codes=[500, 503, 504],
    excluded_paths=["/health", "/metrics", "/docs"],
    chaos_types=[
        ChaosType.LATENCY,
        ChaosType.ERROR,
        ChaosType.EXCEPTION,
    ]
)

# Add middleware
chaos_middleware = ChaosMiddleware(app, config=chaos_config)
app.add_middleware(ChaosMiddleware, config=chaos_config)
set_chaos_middleware(chaos_middleware)

# Add chaos control routes
app.include_router(chaos_router, prefix="/api/v1")
```

### Step 2: Environment Configuration

Add environment variables for chaos configuration:

```bash
# Enable chaos injection
CHAOS_ENABLED=false
CHAOS_PROBABILITY=0.1
CHAOS_LATENCY_MAX_MS=3000
CHAOS_ERROR_CODES=500,503,504
CHAOS_EXCLUDED_PATHS=/health,/metrics,/docs
```

### Step 3: Configuration via Settings

Update `app/core/config.py` to include chaos settings:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Chaos Engineering
    chaos_enabled: bool = Field(False, env="CHAOS_ENABLED")
    chaos_probability: float = Field(0.1, env="CHAOS_PROBABILITY")
    chaos_latency_max_ms: int = Field(3000, env="CHAOS_LATENCY_MAX_MS")
    chaos_error_codes: str = Field("500,503,504", env="CHAOS_ERROR_CODES")
```

## Usage

### Enable Chaos via API

```bash
# Enable chaos with default settings
curl -X POST http://localhost:8000/api/v1/chaos/enable \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Enable with custom probability
curl -X POST http://localhost:8000/api/v1/chaos/enable \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "probability": 0.2,
    "latency_ms_max": 5000,
    "chaos_types": ["latency", "error"]
  }'
```

### Check Chaos Status

```bash
curl http://localhost:8000/api/v1/chaos/status
```

Response:
```json
{
  "enabled": true,
  "total_requests": 1000,
  "chaos_injected": 98,
  "chaos_rate": 0.098,
  "configured_probability": 0.1
}
```

### Update Configuration

```bash
curl -X PUT http://localhost:8000/api/v1/chaos/config \
  -H "Content-Type: application/json" \
  -d '{
    "chaos_probability": 0.3,
    "latency_ms_max": 2000,
    "error_codes": [500, 503]
  }'
```

### Disable Chaos

```bash
curl -X POST http://localhost:8000/api/v1/chaos/disable
```

### List Available Chaos Types

```bash
curl http://localhost:8000/api/v1/chaos/types
```

## Chaos Types

### 1. Latency Injection
Adds random delay to requests:
```python
chaos_types=[ChaosType.LATENCY]
latency_ms_min=100
latency_ms_max=3000
```

### 2. HTTP Error Injection
Returns error responses:
```python
chaos_types=[ChaosType.ERROR]
error_codes=[500, 503, 504]
```

### 3. Exception Injection
Raises exceptions:
```python
chaos_types=[ChaosType.EXCEPTION]
```

### 4. Timeout Injection
Simulates timeouts:
```python
chaos_types=[ChaosType.TIMEOUT]
timeout_ms=10000
```

### 5. Rate Limit Injection
Returns 429 responses:
```python
chaos_types=[ChaosType.RATE_LIMIT]
rate_limit_delay_ms=1000
```

### 6. Partial Failure
Returns degraded responses:
```python
chaos_types=[ChaosType.PARTIAL_FAILURE]
```

## Advanced Usage

### Targeted Chaos Injection

Use `TargetedChaosMiddleware` for condition-based chaos:

```python
from chaos.app_chaos.chaos_middleware import TargetedChaosMiddleware

# Only inject chaos for specific user agents
app.add_middleware(
    TargetedChaosMiddleware,
    chaos_config=chaos_config,
    target_conditions={
        "user_agent": "chaos-test-client",
        "method": ["POST", "PUT"],
    }
)
```

### Path-Specific Chaos

```python
# Only inject chaos for prediction endpoints
chaos_config = ChaosConfig(
    enabled=True,
    included_paths=["/api/v1/predict"],
    chaos_probability=0.5
)
```

### Runtime Control

```python
from chaos.app_chaos.chaos_middleware import (
    enable_chaos,
    disable_chaos,
    update_chaos_config,
    get_chaos_stats
)

# In your code
enable_chaos()
update_chaos_config(chaos_probability=0.2)
stats = get_chaos_stats()
disable_chaos()
```

## Testing Scenarios

### Test 1: Gradual Latency Increase

```bash
# Start with low latency
curl -X POST http://localhost:8000/api/v1/chaos/enable \
  -d '{"enabled": true, "probability": 0.1, "latency_ms_max": 500}'

# Run load test
ab -n 1000 -c 10 http://localhost:8000/api/v1/predict

# Increase latency
curl -X PUT http://localhost:8000/api/v1/chaos/config \
  -d '{"latency_ms_max": 2000}'

# Run load test again
ab -n 1000 -c 10 http://localhost:8000/api/v1/predict

# Observe metrics in Grafana
```

### Test 2: Error Rate Spike

```bash
# Enable error injection
curl -X POST http://localhost:8000/api/v1/chaos/enable \
  -d '{"enabled": true, "probability": 0.2, "chaos_types": ["error"]}'

# Monitor error rates in Prometheus
# Check alert triggers
# Verify retry logic in clients
```

### Test 3: Circuit Breaker Activation

```bash
# High error rate
curl -X PUT http://localhost:8000/api/v1/chaos/config \
  -d '{"chaos_probability": 0.8, "chaos_types": ["error", "exception"]}'

# Verify circuit breaker opens
# Check fallback behavior
# Monitor recovery
```

## Monitoring

### Prometheus Metrics

The middleware automatically logs chaos events, which should be captured by your logging system:

```python
# Custom metrics can be added:
from prometheus_client import Counter, Histogram

chaos_injections = Counter(
    'chaos_injections_total',
    'Total number of chaos injections',
    ['chaos_type']
)

chaos_latency = Histogram(
    'chaos_latency_seconds',
    'Latency added by chaos injection'
)
```

### Logging

All chaos events are logged with structured logging:

```json
{
  "event": "chaos_injected",
  "chaos_type": "latency",
  "path": "/api/v1/predict",
  "method": "POST",
  "chaos_count": 42,
  "total_requests": 420,
  "timestamp": "2025-11-03T12:00:00Z"
}
```

### Grafana Dashboards

Key metrics to monitor:
- Chaos injection rate
- Request latency (p50, p95, p99)
- Error rate by chaos type
- Affected endpoints
- Recovery time

## Best Practices

1. **Start Disabled**: Always deploy with chaos disabled by default
2. **Low Probability**: Start with low chaos probability (5-10%)
3. **Exclude Critical Paths**: Always exclude health checks and metrics
4. **Monitor Actively**: Watch dashboards during chaos experiments
5. **Document Experiments**: Record observations and learnings
6. **Gradual Rollout**: Test in dev → staging → limited production
7. **Time-Box Experiments**: Set clear start/end times
8. **Communicate**: Notify team before enabling chaos

## Safety Features

- ✅ Disabled by default
- ✅ Health checks excluded automatically
- ✅ Metrics endpoints excluded
- ✅ Runtime enable/disable
- ✅ Configurable probability
- ✅ Path-based filtering
- ✅ Comprehensive logging
- ✅ Statistics tracking

## Troubleshooting

### Chaos Not Being Injected

1. Check if enabled:
   ```bash
   curl http://localhost:8000/api/v1/chaos/status
   ```

2. Verify path not excluded:
   ```python
   excluded_paths=["/health", "/metrics"]
   ```

3. Check probability setting:
   ```python
   chaos_probability=0.1  # 10% of requests
   ```

### Too Much Chaos

1. Disable immediately:
   ```bash
   curl -X POST http://localhost:8000/api/v1/chaos/disable
   ```

2. Reduce probability:
   ```bash
   curl -X PUT http://localhost:8000/api/v1/chaos/config \
     -d '{"chaos_probability": 0.01}'
   ```

### Performance Impact

The middleware has minimal overhead when disabled. When enabled:
- Latency injection: Actual delay + ~1ms
- Error injection: ~1ms
- Other types: <5ms

## References

- [Chaos Engineering Principles](https://principlesofchaos.org/)
- [Netflix Chaos Monkey](https://github.com/Netflix/chaosmonkey)
- [AWS Fault Injection Simulator](https://aws.amazon.com/fis/)
- [Chaos Engineering Book](https://www.oreilly.com/library/view/chaos-engineering/9781491988459/)
