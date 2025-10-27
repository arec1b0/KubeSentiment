"""
Distributed Kafka Consumer Architecture

This module extends the high-throughput Kafka consumer with distributed coordination
capabilities for horizontal scaling across multiple instances/pods.

Features:
- Consumer group coordination with automatic partition rebalancing
- Instance health monitoring and graceful shutdown
- Distributed offset management
- Consumer lag monitoring per instance
- Pod-aware partition assignment strategies
- Graceful handling of consumer group changes
"""

import os
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from kafka import KafkaConsumer, TopicPartition
from kafka.coordinator.assignors.range import RangePartitionAssignor
from kafka.coordinator.assignors.roundrobin import RoundRobinPartitionAssignor
from kafka.coordinator.assignors.sticky.sticky_assignor import StickyPartitionAssignor

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConsumerInstance:
    """Represents a single consumer instance in the distributed system."""

    instance_id: str
    pod_name: str
    node_name: str
    namespace: str
    started_at: float = field(default_factory=time.time)
    assigned_partitions: Set[int] = field(default_factory=set)
    current_offsets: Dict[int, int] = field(default_factory=dict)
    lag_per_partition: Dict[int, int] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)
    is_healthy: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to dictionary representation."""
        return {
            "instance_id": self.instance_id,
            "pod_name": self.pod_name,
            "node_name": self.node_name,
            "namespace": self.namespace,
            "started_at": self.started_at,
            "uptime_seconds": time.time() - self.started_at,
            "assigned_partitions": list(self.assigned_partitions),
            "partition_count": len(self.assigned_partitions),
            "current_offsets": self.current_offsets,
            "lag_per_partition": self.lag_per_partition,
            "total_lag": sum(self.lag_per_partition.values()),
            "last_heartbeat": self.last_heartbeat,
            "seconds_since_heartbeat": time.time() - self.last_heartbeat,
            "is_healthy": self.is_healthy,
        }


class PartitionRebalanceListener:
    """
    Listener for partition rebalance events.

    This listener is notified when partitions are assigned or revoked from
    the consumer, enabling graceful handling of rebalancing events.
    """

    def __init__(
        self,
        instance_id: str,
        on_partitions_assigned: Optional[Callable] = None,
        on_partitions_revoked: Optional[Callable] = None,
    ):
        """
        Initialize the rebalance listener.

        Args:
            instance_id: Unique identifier for this consumer instance
            on_partitions_assigned: Callback for partition assignment
            on_partitions_revoked: Callback for partition revocation
        """
        self.instance_id = instance_id
        self.logger = get_logger(f"{__name__}.rebalance")
        self._on_partitions_assigned = on_partitions_assigned
        self._on_partitions_revoked = on_partitions_revoked
        self._rebalance_count = 0
        self._last_rebalance_time = None

    def on_partitions_assigned(self, assigned: List[TopicPartition]) -> None:
        """
        Called when partitions are assigned to this consumer.

        Args:
            assigned: List of assigned TopicPartition objects
        """
        self._rebalance_count += 1
        self._last_rebalance_time = time.time()

        partition_ids = [tp.partition for tp in assigned]
        self.logger.info(
            f"Partitions assigned to {self.instance_id}",
            partitions=partition_ids,
            partition_count=len(assigned),
            rebalance_count=self._rebalance_count,
        )

        if self._on_partitions_assigned:
            self._on_partitions_assigned(assigned)

    def on_partitions_revoked(self, revoked: List[TopicPartition]) -> None:
        """
        Called when partitions are revoked from this consumer.

        Args:
            revoked: List of revoked TopicPartition objects
        """
        partition_ids = [tp.partition for tp in revoked]
        self.logger.info(
            f"Partitions revoked from {self.instance_id}",
            partitions=partition_ids,
            partition_count=len(revoked),
        )

        if self._on_partitions_revoked:
            self._on_partitions_revoked(revoked)

    def get_stats(self) -> Dict[str, Any]:
        """Get rebalance statistics."""
        return {
            "rebalance_count": self._rebalance_count,
            "last_rebalance_time": self._last_rebalance_time,
            "last_rebalance_datetime": (
                datetime.fromtimestamp(self._last_rebalance_time).isoformat()
                if self._last_rebalance_time
                else None
            ),
        }


class DistributedKafkaConsumer:
    """
    Distributed Kafka consumer with automatic scaling and coordination.

    This consumer is designed to work in a Kubernetes environment with multiple
    replicas, automatically coordinating partition assignment and rebalancing
    across instances.
    """

    def __init__(self, settings=None):
        """
        Initialize the distributed Kafka consumer.

        Args:
            settings: Application settings (optional)
        """
        self.settings = settings or get_settings()
        self.logger = get_logger(__name__)

        # Instance identification (for distributed coordination)
        self.instance = self._create_instance_info()
        self.logger.info(
            "Initializing distributed Kafka consumer",
            instance_id=self.instance.instance_id,
            pod_name=self.instance.pod_name,
        )

        # Consumer configuration
        self._consumer: Optional[KafkaConsumer] = None
        self._running = False
        self._consumer_lock = threading.Lock()

        # Partition management
        self._assigned_partitions: Set[TopicPartition] = set()
        self._partition_lock = threading.Lock()

        # Rebalance listener
        self._rebalance_listener = PartitionRebalanceListener(
            instance_id=self.instance.instance_id,
            on_partitions_assigned=self._handle_partitions_assigned,
            on_partitions_revoked=self._handle_partitions_revoked,
        )

        # Health monitoring
        self._health_check_thread: Optional[threading.Thread] = None
        self._health_check_interval = 30  # seconds

    def _create_instance_info(self) -> ConsumerInstance:
        """
        Create instance information for this consumer.

        Uses Kubernetes environment variables when available, falls back to
        hostname-based identification.
        """
        # Try to get Kubernetes pod information
        pod_name = os.getenv("HOSTNAME", socket.gethostname())
        node_name = os.getenv("NODE_NAME", "unknown")
        namespace = os.getenv("POD_NAMESPACE", "default")

        # Generate unique instance ID
        instance_id = f"{pod_name}-{str(uuid4())[:8]}"

        return ConsumerInstance(
            instance_id=instance_id,
            pod_name=pod_name,
            node_name=node_name,
            namespace=namespace,
        )

    def _get_partition_assignor_strategy(self) -> str:
        """
        Get the partition assignment strategy.

        Returns:
            The partition assignor class name
        """
        strategy = self.settings.kafka_partition_assignment_strategy

        strategies = {
            "range": RangePartitionAssignor,
            "roundrobin": RoundRobinPartitionAssignor,
            "sticky": StickyPartitionAssignor,
        }

        return strategies.get(strategy, RoundRobinPartitionAssignor)

    def _create_consumer(self) -> KafkaConsumer:
        """
        Create and configure the Kafka consumer.

        Returns:
            Configured KafkaConsumer instance
        """
        consumer_config = {
            # Basic configuration
            "bootstrap_servers": self.settings.kafka_bootstrap_servers,
            "group_id": self.settings.kafka_consumer_group,
            "client_id": self.instance.instance_id,
            # Offset management
            "auto_offset_reset": self.settings.kafka_auto_offset_reset,
            "enable_auto_commit": False,  # Manual commits for exactly-once
            # Session management
            "session_timeout_ms": self.settings.kafka_session_timeout_ms,
            "heartbeat_interval_ms": self.settings.kafka_heartbeat_interval_ms,
            "max_poll_interval_ms": self.settings.kafka_max_poll_interval_ms,
            # Performance tuning
            "max_poll_records": self.settings.kafka_max_poll_records,
            "fetch_min_bytes": 1024 * 1024,  # 1MB
            "fetch_max_wait_ms": 500,
            "max_partition_fetch_bytes": 8 * 1024 * 1024,  # 8MB
            # Partition assignment strategy
            "partition_assignment_strategy": [self._get_partition_assignor_strategy()],
            # Deserialization
            "value_deserializer": lambda x: x.decode("utf-8") if x else None,
            "key_deserializer": lambda x: x.decode("utf-8") if x else None,
        }

        consumer = KafkaConsumer(**consumer_config)

        # Subscribe to topic with rebalance listener
        consumer.subscribe(
            [self.settings.kafka_topic],
            listener=self._rebalance_listener,
        )

        self.logger.info(
            "Kafka consumer created",
            instance_id=self.instance.instance_id,
            topic=self.settings.kafka_topic,
            consumer_group=self.settings.kafka_consumer_group,
        )

        return consumer

    def _handle_partitions_assigned(self, assigned: List[TopicPartition]) -> None:
        """
        Handle partition assignment events.

        Args:
            assigned: List of assigned partitions
        """
        with self._partition_lock:
            self._assigned_partitions = set(assigned)
            self.instance.assigned_partitions = {tp.partition for tp in assigned}

        self.logger.info(
            "Updated partition assignments",
            instance_id=self.instance.instance_id,
            assigned_partitions=list(self.instance.assigned_partitions),
        )

    def _handle_partitions_revoked(self, revoked: List[TopicPartition]) -> None:
        """
        Handle partition revocation events.

        Args:
            revoked: List of revoked partitions
        """
        with self._partition_lock:
            # Commit offsets for revoked partitions before rebalancing
            if self._consumer and revoked:
                try:
                    self._consumer.commit()
                    self.logger.info(
                        "Committed offsets for revoked partitions",
                        instance_id=self.instance.instance_id,
                        revoked_partitions=[tp.partition for tp in revoked],
                    )
                except Exception as e:
                    self.logger.error(
                        "Failed to commit offsets for revoked partitions",
                        error=str(e),
                    )

    def get_consumer_lag(self) -> Dict[int, int]:
        """
        Get consumer lag per partition.

        Returns:
            Dictionary mapping partition ID to lag
        """
        if not self._consumer:
            return {}

        lag_per_partition = {}

        with self._partition_lock:
            for tp in self._assigned_partitions:
                try:
                    # Get current position
                    current_offset = self._consumer.position(tp)

                    # Get end offset (high water mark)
                    end_offsets = self._consumer.end_offsets([tp])
                    end_offset = end_offsets.get(tp, current_offset)

                    # Calculate lag
                    lag = max(0, end_offset - current_offset)
                    lag_per_partition[tp.partition] = lag

                except Exception as e:
                    self.logger.warning(
                        f"Failed to get lag for partition {tp.partition}",
                        error=str(e),
                    )

        self.instance.lag_per_partition = lag_per_partition
        return lag_per_partition

    def get_instance_info(self) -> Dict[str, Any]:
        """
        Get detailed information about this consumer instance.

        Returns:
            Dictionary with instance details
        """
        lag = self.get_consumer_lag()

        return {
            **self.instance.to_dict(),
            "consumer_group": self.settings.kafka_consumer_group,
            "topic": self.settings.kafka_topic,
            "rebalance_stats": self._rebalance_listener.get_stats(),
            "is_running": self._running,
        }

    def _health_check_loop(self) -> None:
        """Background thread for health monitoring."""
        while self._running:
            try:
                # Update heartbeat timestamp
                self.instance.last_heartbeat = time.time()

                # Update consumer lag
                self.get_consumer_lag()

                # Log health status
                total_lag = sum(self.instance.lag_per_partition.values())
                self.logger.debug(
                    "Health check",
                    instance_id=self.instance.instance_id,
                    partition_count=len(self.instance.assigned_partitions),
                    total_lag=total_lag,
                )

                time.sleep(self._health_check_interval)

            except Exception as e:
                self.logger.error(
                    "Health check failed",
                    instance_id=self.instance.instance_id,
                    error=str(e),
                )
                self.instance.is_healthy = False

    def start(self) -> None:
        """Start the distributed consumer."""
        if self._running:
            self.logger.warning("Consumer already running")
            return

        self._running = True

        # Create consumer
        with self._consumer_lock:
            self._consumer = self._create_consumer()

        # Start health check thread
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            name=f"health-check-{self.instance.instance_id}",
            daemon=True,
        )
        self._health_check_thread.start()

        self.logger.info(
            "Distributed consumer started",
            instance_id=self.instance.instance_id,
        )

    def stop(self) -> None:
        """Stop the distributed consumer gracefully."""
        self.logger.info(
            "Stopping distributed consumer",
            instance_id=self.instance.instance_id,
        )

        self._running = False

        # Stop consumer
        with self._consumer_lock:
            if self._consumer:
                try:
                    # Commit final offsets
                    self._consumer.commit()

                    # Close consumer
                    self._consumer.close()
                    self.logger.info("Consumer closed successfully")

                except Exception as e:
                    self.logger.error(
                        "Error closing consumer",
                        error=str(e),
                    )
                finally:
                    self._consumer = None

        # Wait for health check thread to stop
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)

        self.logger.info(
            "Distributed consumer stopped",
            instance_id=self.instance.instance_id,
        )

    def poll(self, timeout_ms: int = 1000) -> Dict[TopicPartition, List[Any]]:
        """
        Poll for new messages.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            Dictionary mapping TopicPartition to list of messages
        """
        if not self._consumer:
            raise RuntimeError("Consumer not initialized. Call start() first.")

        with self._consumer_lock:
            try:
                records = self._consumer.poll(timeout_ms=timeout_ms, max_records=None)

                # Update current offsets
                if records:
                    for tp, messages in records.items():
                        if messages:
                            latest_offset = messages[-1].offset
                            self.instance.current_offsets[tp.partition] = latest_offset

                return records

            except Exception as e:
                self.logger.error(
                    "Error polling messages",
                    instance_id=self.instance.instance_id,
                    error=str(e),
                )
                raise

    def commit(self, offsets: Optional[Dict[TopicPartition, int]] = None) -> None:
        """
        Commit offsets to Kafka.

        Args:
            offsets: Optional dictionary of offsets to commit
        """
        if not self._consumer:
            raise RuntimeError("Consumer not initialized. Call start() first.")

        with self._consumer_lock:
            try:
                if offsets:
                    self._consumer.commit(offsets=offsets)
                else:
                    self._consumer.commit()

                self.logger.debug(
                    "Offsets committed",
                    instance_id=self.instance.instance_id,
                )

            except Exception as e:
                self.logger.error(
                    "Error committing offsets",
                    instance_id=self.instance.instance_id,
                    error=str(e),
                )
                raise

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
