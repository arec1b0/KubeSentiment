"""Message batching utilities for Kafka consumer."""

import time
from typing import Any, Iterable, List, Tuple

from app.models.kafka_models import MessageMetadata


class MessageBatch:
    """Container for messages that should be processed together."""

    def __init__(self, max_size: int, created_at: float | None = None) -> None:
        """Initializes the MessageBatch.

        Args:
            max_size: The maximum number of messages this batch can hold.
            created_at: The timestamp when the batch was created. Defaults to current time.
        """
        self.max_size = max_size
        self._messages: List[Any] = []
        self._metadata: List[MessageMetadata] = []
        self.created_at = created_at or time.time()

    def add_message(self, message: Any, metadata: MessageMetadata) -> bool:
        """Add a message to the batch if capacity is available.

        Args:
            message: The message payload.
            metadata: Metadata associated with the message.

        Returns:
            `True` if the message was added, `False` if the batch is full.
        """

        if self.is_full():
            return False
        self._messages.append(message)
        self._metadata.append(metadata)
        return True

    def size(self) -> int:
        """Return the number of messages currently buffered.

        Returns:
            The number of messages in the batch.
        """

        return len(self._messages)

    def is_full(self) -> bool:
        """Return ``True`` when the batch reached its configured size.

        Returns:
            `True` if the batch is full, `False` otherwise.
        """

        return self.size() >= self.max_size

    def is_empty(self) -> bool:
        """Return ``True`` when the batch has no buffered messages.

        Returns:
            `True` if the batch is empty, `False` otherwise.
        """

        return self.size() == 0

    def clear(self) -> None:
        """Remove all buffered messages from the batch."""

        self._messages.clear()
        self._metadata.clear()
        self.created_at = time.time()

    def iter_messages(self) -> Iterable[Tuple[Any, MessageMetadata]]:
        """Yield pairs of message payloads and their metadata.

        Yields:
            Tuple of (message, metadata).
        """

        return zip(self._messages, self._metadata, strict=True)

    def get_texts_and_ids(self) -> Tuple[List[str], List[str]]:
        """Extract message texts and identifiers for model inference.

        Returns:
            A tuple containing a list of texts and a list of message IDs.
        """

        texts: List[str] = []
        message_ids: List[str] = []
        for message in self._messages:
            text = message.get("text", "") if isinstance(message, dict) else str(message)
            # Ensure message_id is always a string
            if isinstance(message, dict) and message.get("id") is not None:
                message_id = str(message.get("id"))
            else:
                message_id = f"{time.time_ns()}"

            texts.append(text)
            message_ids.append(message_id)
        return texts, message_ids
