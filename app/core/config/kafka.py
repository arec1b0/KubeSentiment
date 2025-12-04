"""Kafka streaming configuration settings."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class KafkaConfig(BaseSettings):
    """Kafka streaming and messaging configuration.

    Attributes:
        kafka_enabled: Enable Kafka streaming.
        kafka_bootstrap_servers: Kafka bootstrap servers.
        kafka_consumer_group: Kafka consumer group ID.
        kafka_topic: Kafka topic to consume from.
        kafka_auto_offset_reset: Auto offset reset strategy.
        kafka_max_poll_records: Maximum records to poll per request.
        kafka_session_timeout_ms: Session timeout in milliseconds.
        kafka_heartbeat_interval_ms: Heartbeat interval in milliseconds.
        kafka_max_poll_interval_ms: Maximum poll interval in milliseconds.
        kafka_enable_auto_commit: Enable automatic offset commits.
        kafka_auto_commit_interval_ms: Auto commit interval in milliseconds.
        kafka_consumer_threads: Number of consumer threads for parallel processing.
        kafka_batch_size: Batch size for processing messages.
        kafka_processing_timeout_ms: Processing timeout per batch in milliseconds.
        kafka_buffer_size: Internal buffer size for message queuing.
        kafka_dlq_topic: Dead letter queue topic for failed messages.
        kafka_dlq_enabled: Enable dead letter queue for failed messages.
        kafka_max_retries: Maximum number of retries before sending to DLQ.
        kafka_producer_bootstrap_servers: Kafka bootstrap servers for producer (DLQ).
        kafka_producer_acks: Producer acknowledgment level.
        kafka_producer_retries: Number of producer retries.
        kafka_producer_batch_size: Producer batch size in bytes.
        kafka_producer_linger_ms: Producer linger time in milliseconds.
        kafka_producer_compression_type: Producer compression type.
        kafka_partition_assignment_strategy: Partition assignment strategy for consumer group.
    """

    # Basic Kafka settings
    kafka_enabled: bool = Field(
        default=False,
        description="Enable Kafka streaming",
    )
    kafka_bootstrap_servers: List[str] = Field(
        default_factory=lambda: ["localhost:9092"],
        description="Kafka bootstrap servers",
        min_length=1,
    )
    kafka_consumer_group: str = Field(
        default="kubesentiment_consumer",
        description="Kafka consumer group ID",
        min_length=1,
    )
    kafka_topic: str = Field(
        default="sentiment_requests",
        description="Kafka topic to consume from",
        min_length=1,
    )
    kafka_feedback_topic: str = Field(
        default="sentiment_feedback",
        description="Kafka topic to publish feedback events to",
        min_length=1,
    )

    # Consumer settings
    kafka_auto_offset_reset: str = Field(
        default="latest",
        description="Auto offset reset strategy",
        pattern=r"^(earliest|latest|none)$",
    )
    kafka_max_poll_records: int = Field(
        default=500,
        description="Maximum records to poll per request",
        ge=1,
        le=10000,
    )
    kafka_session_timeout_ms: int = Field(
        default=30000,
        description="Session timeout in milliseconds",
        ge=1000,
        le=300000,
    )
    kafka_heartbeat_interval_ms: int = Field(
        default=3000,
        description="Heartbeat interval in milliseconds",
        ge=1000,
        le=30000,
    )
    kafka_max_poll_interval_ms: int = Field(
        default=300000,
        description="Maximum poll interval in milliseconds",
        ge=10000,
        le=2147483647,
    )
    kafka_enable_auto_commit: bool = Field(
        default=False,
        description="Enable automatic offset commits",
    )
    kafka_auto_commit_interval_ms: int = Field(
        default=5000,
        description="Auto commit interval in milliseconds",
        ge=1000,
        le=60000,
    )

    # High-throughput consumer settings
    kafka_consumer_threads: int = Field(
        default=4,
        description="Number of consumer threads for parallel processing",
        ge=1,
        le=32,
    )
    kafka_batch_size: int = Field(
        default=100,
        description="Batch size for processing messages",
        ge=1,
        le=1000,
    )
    kafka_processing_timeout_ms: int = Field(
        default=30000,
        description="Processing timeout per batch in milliseconds",
        ge=1000,
        le=300000,
    )
    kafka_buffer_size: int = Field(
        default=10000,
        description="Internal buffer size for message queuing",
        ge=1000,
        le=100000,
    )

    # Dead letter queue settings
    kafka_dlq_topic: str = Field(
        default="sentiment_requests_dlq",
        description="Dead letter queue topic for failed messages",
    )
    kafka_dlq_enabled: bool = Field(
        default=True,
        description="Enable dead letter queue for failed messages",
    )
    kafka_max_retries: int = Field(
        default=3,
        description="Maximum number of retries before sending to DLQ",
        ge=1,
        le=10,
    )

    # Producer settings for DLQ
    kafka_producer_bootstrap_servers: List[str] = Field(
        default_factory=lambda: ["localhost:9092"],
        description="Kafka bootstrap servers for producer (DLQ)",
        min_length=1,
    )
    kafka_producer_acks: str = Field(
        default="all",
        description="Producer acknowledgment level",
        pattern=r"^(0|1|all)$",
    )
    kafka_producer_retries: int = Field(
        default=3,
        description="Number of producer retries",
        ge=0,
        le=10,
    )
    kafka_producer_batch_size: int = Field(
        default=16384,
        description="Producer batch size in bytes",
        ge=0,
        le=1048576,
    )
    kafka_producer_linger_ms: int = Field(
        default=5,
        description="Producer linger time in milliseconds",
        ge=0,
        le=100,
    )
    kafka_producer_compression_type: str = Field(
        default="lz4",
        description="Producer compression type",
        pattern=r"^(none|gzip|snappy|lz4|zstd)$",
    )
    kafka_producer_timeout_seconds: float = Field(
        default=10.0,
        description="Timeout in seconds for waiting for producer acknowledgment",
        ge=1.0,
        le=60.0,
    )
    kafka_producer_init_retries: int = Field(
        default=10,
        description="Number of retries for producer initialization",
        ge=1,
        le=50,
    )

    # Advanced settings
    kafka_partition_assignment_strategy: str = Field(
        default="roundrobin",
        description="Partition assignment strategy for consumer group",
        pattern=r"^(range|roundrobin|sticky)$",
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
