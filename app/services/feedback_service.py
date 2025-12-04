"""
Service for handling user feedback on predictions.

This module manages the collection and processing of user feedback, primarily
by publishing feedback events to a Kafka topic for asynchronous processing
by downstream systems (active learning, dashboarding, etc.).
"""

import asyncio
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
        self._started = False

    async def start(self):
        """Initialize the Kafka producer asynchronously."""
        if self.settings.kafka.kafka_enabled and not self._started:
            await self._init_producer_with_retry()
            self._started = True
        elif not self.settings.kafka.kafka_enabled:
             logger.info("Kafka disabled, feedback service will only log locally")
             self._started = True

    async def stop(self):
        """Close the Kafka producer."""
        if self.producer:
            self.producer.close()
            self.producer = None
            self._started = False
            logger.info("Feedback service stopped")

    async def _init_producer_with_retry(self):
        """Initialize the Kafka producer with retry logic."""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Run blocking init in thread
                loop = asyncio.get_running_loop()
                self.producer = await loop.run_in_executor(
                    None,
                    lambda: KafkaProducer(
                        bootstrap_servers=self.settings.kafka.kafka_bootstrap_servers,
                        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                        acks=self.settings.kafka.kafka_producer_acks,
                        retries=self.settings.kafka.kafka_producer_retries,
                        batch_size=self.settings.kafka.kafka_producer_batch_size,
                        linger_ms=self.settings.kafka.kafka_producer_linger_ms,
                        compression_type=self.settings.kafka.kafka_producer_compression_type,
                    )
                )
                logger.info("Feedback Kafka producer initialized successfully")
                return
            except Exception as e:
                logger.warning(
                    f"Failed to initialize Feedback Kafka producer (attempt {attempt+1}/{max_retries})",
                    error=str(e)
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error("Failed to initialize Feedback Kafka producer after all retries")
        self.producer = None


    async def submit_feedback(self, feedback: FeedbackRequest) -> bool:
        """Submit feedback for a prediction.

        Publishes the feedback to the configured Kafka topic.

        Args:
            feedback: The feedback request object.

        Returns:
            True if submitted successfully, False otherwise.
        """
        # Ensure start was called (lazy start fallback if not called in lifespan)
        if not self._started:
             await self.start()

        feedback_data = feedback.model_dump()
        # Convert UUID to string for serialization
        feedback_data["prediction_id"] = str(feedback_data["prediction_id"])
        feedback_data["timestamp"] = time.time()
        
        logger.info(
            "Received feedback",
            prediction_id=feedback_data["prediction_id"],
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
            # Send to Kafka asynchronously but wait for confirmation
            loop = asyncio.get_running_loop()
            
            # Ensure serialization is safe
            def _send_and_wait():
                future = self.producer.send(
                    self.settings.kafka.kafka_feedback_topic,
                    value=feedback_data
                )
                # Wait for acknowledgment to ensure delivery
                return future.get(timeout=10.0)

            await loop.run_in_executor(None, _send_and_wait)
            
            logger.info(
                "Feedback sent to Kafka",
                topic=self.settings.kafka.kafka_feedback_topic,
                prediction_id=feedback_data["prediction_id"]
            )
            return True

        except KafkaError as e:
            logger.error(
                "Failed to publish feedback to Kafka",
                error=str(e),
                prediction_id=feedback_data["prediction_id"],
                exc_info=True
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error submitting feedback",
                error=str(e),
                prediction_id=feedback_data["prediction_id"],
                exc_info=True
            )
            return False

    def close(self):
        """Close the Kafka producer (sync wrapper for backward compatibility if needed)."""
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
