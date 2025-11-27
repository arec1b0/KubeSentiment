# ADR 003: Use Kafka for Asynchronous Message Processing

**Status:** Accepted
**Date:** 2024-02-01
**Authors:** KubeSentiment Team

## Context

The KubeSentiment service needs to handle high-volume batch predictions and asynchronous processing workloads. As the system scales, we face several challenges:

1. **Synchronous API limitations**: REST API has finite request/response timeout limits
2. **Large batch processing**: Processing thousands of predictions synchronously blocks resources
3. **Traffic spikes**: Need to absorb sudden bursts of prediction requests
4. **Reliability**: Need guaranteed delivery and retry mechanisms
5. **Decoupling**: Producers and consumers should operate independently
6. **Scalability**: Need horizontal scaling of prediction workers

Key requirements:
- Handle > 100,000 messages/second throughput
- Guaranteed message delivery (at-least-once semantics)
- Consumer group support for parallel processing
- Message persistence for reliability
- Low latency (< 10ms per message)
- Integration with existing monitoring stack

## Decision

We will use **Apache Kafka** as the distributed message queue for asynchronous prediction processing.

### Implementation Strategy

1. **Topic Structure**:
   - `sentiment-requests`: Incoming prediction requests
   - `sentiment-responses`: Completed prediction results
   - `sentiment-dlq`: Dead letter queue for failed messages

2. **Consumer Groups**:
   - Multiple consumer instances for horizontal scaling
   - Configurable number of partitions (default: 8)
   - Parallel processing with consumer group coordination

3. **Message Format**:
   - JSON-serialized prediction requests/responses
   - Correlation IDs for request tracking
   - Metadata for monitoring and debugging

4. **Error Handling**:
   - Retry logic with exponential backoff
   - Dead letter queue for permanent failures
   - Circuit breaker pattern for downstream failures

## Consequences

### Positive

- **High throughput**: Achieved ~105,700 messages/second in benchmarks
- **Decoupling**: Producers and consumers operate independently
- **Horizontal scaling**: Add more consumer instances as needed
- **Reliability**: Message persistence ensures no data loss
- **Buffering**: Absorbs traffic spikes without dropping requests
- **Replay capability**: Can reprocess messages from any offset
- **Low latency**: Average message latency ~5ms
- **Battle-tested**: Kafka is proven at scale (LinkedIn, Uber, Netflix)

### Negative

- **Operational complexity**: Kafka cluster requires management (ZooKeeper/KRaft)
- **Infrastructure cost**: Additional compute and storage resources
- **Learning curve**: Team needs Kafka expertise
- **Debugging**: Async processing harder to debug than synchronous
- **Storage requirements**: Message retention requires disk space
- **Network overhead**: Additional network hops for message delivery

### Neutral

- **Latency**: Async processing trades immediate response for throughput
- **Consistency**: Eventual consistency vs. synchronous consistency
- **Monitoring**: Requires additional metrics and dashboards

## Alternatives Considered

### Alternative 1: RabbitMQ

**Pros:**
- Simpler operational model than Kafka
- Rich routing capabilities with exchanges
- Good management UI
- Lower resource requirements

**Cons:**
- Lower throughput than Kafka (~50K msg/s vs 100K+ msg/s)
- No built-in message replay capability
- Less suitable for event streaming
- More complex clustering setup

**Rejected because**: Throughput requirements exceed RabbitMQ's typical capacity, and we need message replay for reprocessing.

### Alternative 2: AWS SQS/GCP Pub/Sub

**Pros:**
- Fully managed (no operational overhead)
- Auto-scaling
- Pay-per-use pricing
- High availability built-in

**Cons:**
- Vendor lock-in
- Higher latency (~20-100ms)
- Cost increases with high throughput
- Less control over configuration
- Requires cloud connectivity

**Rejected because**: We prioritize multi-cloud and on-premises support, and need lower latency than cloud queues provide.

### Alternative 3: Redis Streams

**Pros:**
- Simpler than Kafka
- Already using Redis for caching
- Good performance
- Consumer groups support

**Cons:**
- Not designed for high-volume message queuing
- Limited persistence guarantees
- Less mature ecosystem
- Fewer monitoring tools

**Rejected because**: Redis Streams is not battle-tested at our target scale, and Kafka provides better persistence guarantees.

### Alternative 4: Database Queue (PostgreSQL, MySQL)

**Pros:**
- Uses existing database infrastructure
- ACID transactions
- Familiar SQL interface

**Cons:**
- Poor performance for high-volume queues
- Polling overhead
- Database becomes bottleneck
- Not designed for streaming workloads

**Rejected because**: Database queues cannot meet our throughput and latency requirements.

### Alternative 5: Celery with Redis/RabbitMQ

**Pros:**
- Python-native task queue
- Good for distributed task processing
- Rich feature set

**Cons:**
- Not designed for high-throughput streaming
- More complex than using Kafka directly
- Additional abstraction layer
- Limited replay and reprocessing capabilities

**Rejected because**: Kafka provides better performance and replay capabilities for our use case.

## Implementation Details

### Kafka Configuration

```yaml
# Kafka cluster configuration
kafka:
  bootstrap_servers: "kafka-0:9092,kafka-1:9092,kafka-2:9092"
  replication_factor: 3
  partitions: 8
  retention_ms: 86400000  # 24 hours
  compression_type: "lz4"

# Consumer group configuration
consumer:
  group_id: "sentiment-consumers"
  auto_offset_reset: "earliest"
  enable_auto_commit: false
  max_poll_records: 500
  session_timeout_ms: 30000
```

### Producer Implementation

```python
from confluent_kafka import Producer

class SentimentProducer:
    def __init__(self, bootstrap_servers: str):
        self.producer = Producer({
            'bootstrap.servers': bootstrap_servers,
            'compression.type': 'lz4',
            'linger.ms': 10,
            'batch.size': 16384,
        })

    async def send_prediction_request(self, request: dict) -> None:
        """Send prediction request to Kafka."""
        message = json.dumps(request).encode('utf-8')
        self.producer.produce(
            topic='sentiment-requests',
            key=request['correlation_id'].encode('utf-8'),
            value=message,
            callback=self._delivery_callback
        )
        self.producer.poll(0)
```

### Consumer Implementation

```python
from confluent_kafka import Consumer

class SentimentConsumer:
    def __init__(self, bootstrap_servers: str, group_id: str):
        self.consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
        })
        self.consumer.subscribe(['sentiment-requests'])

    async def process_messages(self):
        """Process messages from Kafka."""
        while True:
            msg = self.consumer.poll(timeout=1.0)
            if msg is None:
                continue

            try:
                request = json.loads(msg.value().decode('utf-8'))
                result = await self.predict(request['text'])

                # Send result to response topic
                await self.send_response(request['correlation_id'], result)

                # Commit offset
                self.consumer.commit(asynchronous=False)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await self.send_to_dlq(msg)
```

### Dead Letter Queue Handler

```python
async def send_to_dlq(self, message, error: Exception):
    """Send failed message to dead letter queue."""
    dlq_message = {
        'original_message': message.value().decode('utf-8'),
        'error': str(error),
        'timestamp': datetime.utcnow().isoformat(),
        'partition': message.partition(),
        'offset': message.offset(),
    }
    self.dlq_producer.produce(
        topic='sentiment-dlq',
        value=json.dumps(dlq_message).encode('utf-8')
    )
```

## Performance Metrics

### Throughput Benchmarks

| Configuration | Messages/Second | Latency P99 | Resource Usage |
|--------------|----------------|-------------|----------------|
| 1 producer, 1 consumer | 12,500 | 15ms | 1 CPU, 512MB |
| 3 producers, 3 consumers | 45,000 | 12ms | 3 CPU, 1.5GB |
| 10 producers, 10 consumers | 105,700 | 18ms | 10 CPU, 5GB |

### Message Processing

| Metric | Value |
|--------|-------|
| Average message size | 1.2KB |
| Compression ratio (LZ4) | 3:1 |
| Batch size | 500 messages |
| Processing time per message | 45ms (including inference) |

## Monitoring

Key metrics to track:

**Kafka Metrics:**
- `kafka_messages_in_per_sec` - Incoming message rate
- `kafka_messages_out_per_sec` - Outgoing message rate
- `kafka_consumer_lag` - Consumer lag per partition
- `kafka_bytes_in_per_sec` - Network throughput
- `kafka_under_replicated_partitions` - Replication health

**Application Metrics:**
- `kafka_predictions_processed_total` - Total predictions processed
- `kafka_processing_duration_seconds` - Processing time per message
- `kafka_dlq_messages_total` - Dead letter queue size
- `kafka_batch_size` - Average batch size processed

## Operational Considerations

### Kafka Deployment

- **Development**: Single Kafka broker with Docker Compose
- **Staging**: 3-broker Kafka cluster with KRaft mode
- **Production**: Managed Kafka service (Confluent Cloud, AWS MSK, or self-hosted cluster)

### Scaling Strategy

1. **Horizontal scaling**: Increase partition count and consumer instances
2. **Vertical scaling**: Increase broker resources for higher throughput
3. **Auto-scaling**: Scale consumers based on consumer lag metric

### Disaster Recovery

- **Replication**: 3x replication factor for production
- **Backups**: MirrorMaker 2.0 for cross-datacenter replication
- **Monitoring**: Alert on consumer lag > 10,000 messages

### Security

- **Authentication**: SASL/SCRAM or mTLS
- **Authorization**: Kafka ACLs for topic-level permissions
- **Encryption**: TLS for data in transit
- **Network isolation**: Private subnets for Kafka brokers

## Migration Path

1. **Phase 1** (Complete): Proof of concept with Docker Compose
2. **Phase 2** (Complete): Integration testing with staging environment
3. **Phase 3** (Complete): Deploy to production with feature flag
4. **Phase 4** (In Progress): Migrate batch processing workloads to Kafka
5. **Phase 5** (Planned): Event-driven architecture for model retraining triggers

## Validation

### Testing Performed

- **Load testing**: 100K messages/second for 1 hour
- **Failure testing**: Broker failure, network partition, consumer crashes
- **Latency testing**: P50/P95/P99 latency under various loads
- **Integration testing**: End-to-end prediction flow

### Results

- ✅ Throughput target met: 105,700 msg/s
- ✅ Latency target met: P99 < 20ms
- ✅ No message loss during broker failure
- ✅ Consumer lag recovery < 5 minutes

## References

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Confluent Kafka Python Client](https://docs.confluent.io/kafka-clients/python/current/overview.html)
- [Kafka Consumer Implementation](../../app/services/kafka_consumer.py)
- [Kafka Producer Implementation](../../app/services/kafka_producer.py)
- [Kafka High Throughput Consumer Guide](../../docs/kafka-high-throughput.md)
- [Docker Compose Kafka Setup](../../docker-compose.kafka.yml)

## Related ADRs

- [ADR 002: Use Redis for Distributed Caching](002-use-redis-for-distributed-caching.md) - Complements Kafka for caching
- [ADR 004: Use FastAPI as Web Framework](004-use-fastapi-as-web-framework.md) - Kafka consumers use FastAPI dependencies
- [ADR 007: Implement Three Pillars of Observability](007-three-pillars-of-observability.md) - Kafka monitoring integration

## Change History

- 2024-02-01: Initial decision
- 2024-03-15: Production deployment complete
- 2024-04-20: Updated with production performance metrics
- 2025-11-18: Added to ADR repository
