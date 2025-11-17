"""Models for stream processing with intelligent batching."""

import asyncio
from dataclasses import dataclass


@dataclass
class BatchConfig:
    """Configuration for batch processing behavior.

    This class defines the parameters that control how the StreamProcessor
    groups requests into batches. These settings allow for fine-tuning the
    trade-off between latency and throughput.

    Attributes:
        max_batch_size: The largest number of items to include in a single batch.
        max_wait_time_ms: The maximum time in milliseconds to wait for a batch
                          to fill up before processing it, even if it's not full.
        min_batch_size: The minimum number of items required to process a batch,
                        unless the max_wait_time_ms is exceeded.
        dynamic_batching: A flag to enable or disable dynamic adjustment of
                          batch sizes based on request load.
    """

    max_batch_size: int = 32
    max_wait_time_ms: float = 50.0
    min_batch_size: int = 1
    dynamic_batching: bool = True


@dataclass
class PendingRequest:
    """Represents a pending prediction request in the batch queue.

    Each instance of this class holds the data for a single prediction request,
    along with metadata needed for asynchronous processing and tracking.

    Attributes:
        text: The input text to be analyzed for sentiment.
        future: An asyncio.Future object that will be resolved with the
                prediction result when the batch is processed.
        timestamp: The time when the request was added to the queue, used for
                   calculating wait times.
        request_id: A unique identifier for the request, used for logging and
                    tracking.
    """

    text: str
    future: asyncio.Future
    timestamp: float
    request_id: str
