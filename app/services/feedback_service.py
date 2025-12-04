"""
Service for handling user feedback on predictions.

This module manages the collection and processing of user feedback, primarily
by publishing feedback events to a Kafka topic for asynchronous processing
by downstream systems (active learning, dashboarding, etc.).
"""

import json
import time
from typing import Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError

from app.api.schemas.requests import FeedbackRequest
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class FeedbackService:
    """Service for submitting feedback to the sentiment analysis system."""

    def __init__(self, settings: Settings):
        """Initialize the feedback service.

        Args:
            settings: Application configuration settings.
        """
        self.settings = settings
        self.producer: Optional[KafkaProducer] = None
        
        if self.settings.kafka.kafka_enabled:
            self._init_producer()
        else:
            logger.info("Kafka disabled, feedback service will only log locally")

    def _init_producer(self):
        """Initialize the Kafka producer."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.settings.kafka.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks=self.settings.kafka.kafka_producer_acks,
                retries=self.settings.kafka.kafka_producer_retries,
                batch_size=self.settings.kafka.kafka_producer_batch_size,
                linger_ms=self.settings.kafka.kafka_producer_linger_ms,
                compression_type=self.settings.kafka.kafka_producer_compression_type,
            )
            logger.info("Feedback Kafka producer initialized successfully")
        except Exception as e:
            logger.error(
                "Failed to initialize Feedback Kafka producer",
                error=str(e),
                exc_info=True
            )
            self.producer = None

    async def submit_feedback(self, feedback: FeedbackRequest) -> bool:
        """Submit feedback for a prediction.

        Publishes the feedback to the configured Kafka topic.

        Args:
            feedback: The feedback request object.

        Returns:
            True if submitted successfully (or queued), False otherwise.
        """
        feedback_data = feedback.model_dump()
        feedback_data["timestamp"] = time.time()
        
        logger.info(
            "Received feedback",
            prediction_id=feedback.prediction_id,
            corrected_label=feedback.corrected_label
        )

        if not self.producer:
            if self.settings.kafka.kafka_enabled:
                logger.error("Feedback dropped: Kafka enabled but producer not available")
                return False
            # If Kafka is disabled, we just log it (in a real system, might save to DB)
            logger.info("Feedback logged (Kafka disabled): %s", feedback_data)
            return True

        try:
            # Send to Kafka asynchronously
            future = self.producer.send(
                self.settings.kafka.kafka_feedback_topic,
                value=feedback_data
            )
            
            # We can optionally wait for acknowledgment or let it be async
            # For high throughput, we usually don't await future.get() in the request path
            # unless strict consistency is required.
            
            logger.debug(
                "Feedback sent to Kafka",
                topic=self.settings.kafka.kafka_feedback_topic,
                prediction_id=feedback.prediction_id
            )
            return True

        except KafkaError as e:
            logger.error(
                "Failed to publish feedback to Kafka",
                error=str(e),
                prediction_id=feedback.prediction_id,
                exc_info=True
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error submitting feedback",
                error=str(e),
                prediction_id=feedback.prediction_id,
                exc_info=True
            )
            return False

    def close(self):
        """Close the Kafka producer."""
        if self.producer:
            self.producer.close()


# Singleton instance
_feedback_service: Optional[FeedbackService] = None


def get_feedback_service(settings: Settings) -> FeedbackService:
    """Get or create the global feedback service instance.

    Args:
        settings: Application configuration settings.

    Returns:
        FeedbackService instance.
    """
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService(settings)
    return _feedback_service
