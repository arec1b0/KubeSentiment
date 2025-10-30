# ADR 002: Use Redis for Distributed Caching

**Status:** Accepted
**Date:** 2024-01-20
**Authors:** KubeSentiment Team

## Context

As we scale KubeSentiment horizontally with multiple pod replicas, we need a caching strategy that:
- Works across distributed instances
- Reduces redundant model inference operations
- Improves response times for repeated requests
- Minimizes database/external API calls
- Provides high availability and fault tolerance

Key requirements:
- Cache hit rate target: > 40%
- Latency overhead: < 5ms per cache operation
- Support for TTL-based expiration
- Horizontal scalability with pod replicas
- Minimal operational overhead

## Decision

We will use **Redis** as the distributed caching layer for prediction results and frequently accessed data.

### Implementation Strategy

1. **Cache Layers**:
   - **L1 (Local)**: In-memory Python dict cache per pod (LRU, 500 entries)
   - **L2 (Distributed)**: Redis cluster shared across all pods

2. **Cached Data**:
   - Prediction results (key: hash of input text, TTL: 1 hour)
   - Feature vectors (TTL: 30 minutes)
   - Model metadata (TTL: 24 hours)

3. **Cache Strategy**:
   - Write-through for predictions
   - Lazy loading for metadata
   - Automatic expiration with TTL

## Consequences

### Positive

- **40%+ cache hit rate achieved**: Reduces inference load significantly
- **3x faster response for cached requests**: ~15ms vs ~45ms
- **Reduced infrastructure costs**: Fewer compute resources needed
- **Scalable**: Works seamlessly with 2-10 pod replicas
- **Battle-tested**: Redis is mature and well-understood
- **Rich features**: Pub/sub, TTL, atomic operations

### Negative

- **Additional infrastructure**: Redis cluster to manage and monitor
- **Network latency**: L2 cache adds ~2-4ms vs local cache
- **Cache invalidation complexity**: Must handle stale data scenarios
- **Memory costs**: Redis cluster memory requirements
- **Single point of failure**: Redis outage impacts cache availability

### Neutral

- **Operational overhead**: Requires monitoring and maintenance
- **Data consistency**: Trade-off between cache freshness and hit rate
- **Cost**: Redis managed service fees vs infrastructure savings

## Alternatives Considered

### Alternative 1: Memcached

**Pros:**
- Simpler than Redis
- Slightly lower memory overhead
- Good performance

**Cons:**
- Less feature-rich (no pub/sub, limited data structures)
- No built-in persistence
- Less flexible for future use cases

**Rejected because**: Redis provides more flexibility for future features (pub/sub for cache invalidation, persistence options).

### Alternative 2: Local Cache Only

**Pros:**
- No external dependencies
- Zero network latency
- Simplest implementation

**Cons:**
- No sharing across pods
- Duplicated cache entries
- Lower cache hit rate in distributed setup
- Wasted memory across pods

**Rejected because**: Insufficient cache hit rate in multi-pod deployment.

### Alternative 3: Database-backed Cache

**Pros:**
- Uses existing infrastructure
- Persistent by default

**Cons:**
- Much slower than Redis (~50-100ms)
- Adds load to database
- Not designed for caching use case

**Rejected because**: Too slow for our latency requirements.

### Alternative 4: Cloud-native Cache (AWS ElastiCache, GCP Memorystore)

**Pros:**
- Fully managed
- High availability built-in
- Auto-scaling

**Cons:**
- Vendor lock-in
- Higher cost
- Less control over configuration

**Decision**: Use this in production, but support standard Redis for development/staging.

## Implementation Details

### Configuration

```python
# Redis connection settings
REDIS_HOST = os.getenv("MLOPS_REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("MLOPS_REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("MLOPS_REDIS_DB", 0))
REDIS_MAX_CONNECTIONS = int(os.getenv("MLOPS_REDIS_MAX_CONNECTIONS", 50))
```

### Cache Key Strategy

```python
import hashlib

def generate_cache_key(text: str, model_name: str) -> str:
    """Generate deterministic cache key."""
    content = f"{model_name}:{text}"
    return f"prediction:{hashlib.sha256(content.encode()).hexdigest()}"
```

### Cache Usage Pattern

```python
async def get_prediction(text: str) -> dict:
    # Check L1 cache
    cache_key = generate_cache_key(text, model_name)
    result = local_cache.get(cache_key)
    if result:
        return {**result, "cached": True, "cache_level": "L1"}

    # Check L2 cache (Redis)
    result = await redis_cache.get(cache_key)
    if result:
        local_cache.set(cache_key, result)  # Populate L1
        return {**result, "cached": True, "cache_level": "L2"}

    # Cache miss - perform inference
    result = await model.predict(text)

    # Write to both caches
    await redis_cache.set(cache_key, result, ttl=3600)
    local_cache.set(cache_key, result)

    return {**result, "cached": False}
```

## Performance Metrics

### Cache Performance

| Metric | Target | Actual |
|--------|--------|--------|
| Hit Rate | >40% | 42.5% |
| L1 Latency | <1ms | 0.3ms |
| L2 Latency | <5ms | 3.2ms |
| Cache Memory | <2GB | 1.8GB |

### Impact on Response Time

| Scenario | Latency |
|----------|---------|
| Cache Miss (Inference) | 45ms |
| L1 Cache Hit | 0.5ms |
| L2 Cache Hit | 3.5ms |

## Monitoring

Key metrics to track:
- `redis_cache_hits_total{cache_type="prediction"}`
- `redis_cache_misses_total{cache_type="prediction"}`
- `redis_operation_duration_seconds{operation="get|set"}`
- `redis_connections_active`
- `redis_cache_size_bytes{cache_type="prediction"}`

## Operational Considerations

### Redis Deployment

- Development: Single Redis instance
- Staging: Redis with persistence (AOF)
- Production: Redis Cluster or managed service (AWS ElastiCache)

### Backup & Recovery

- Enable AOF (Append-Only File) persistence
- Regular snapshots to S3/GCS
- Cache can be rebuilt from database if necessary

### Security

- Redis authentication (REQUIREPASS)
- Network isolation (private subnet)
- TLS encryption for production

## Migration Path

1. **Phase 1** (Complete): Implement Redis cache with feature flag
2. **Phase 2** (Complete): Test in staging with real traffic
3. **Phase 3** (Complete): Enable in production for 10% of traffic
4. **Phase 4** (Complete): Rollout to 100% of traffic
5. **Phase 5** (In Progress): Optimize TTL values based on metrics

## References

- [Redis Documentation](https://redis.io/documentation)
- [Redis Best Practices](https://redis.io/docs/management/optimization/)
- [Caching Implementation](../../app/services/redis_cache.py)
- [Scalability Documentation](../../SCALABILITY_ENHANCEMENTS.md)

## Related ADRs

- [ADR 003: Use Kafka for Async Processing](003-use-kafka-for-async-processing.md)
- [ADR 004: Use FastAPI as Web Framework](004-use-fastapi-as-web-framework.md)

## Change History

- 2024-01-20: Initial decision
- 2024-02-15: Production deployment complete
- 2024-03-10: Updated metrics with actual performance
- 2025-10-30: Added to ADR repository
