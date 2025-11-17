"""Common mock classes used across multiple test files.

This module provides shared mock implementations for models, settings,
and other commonly-mocked components to reduce code duplication.
"""

from unittest.mock import Mock

from app.models.pytorch_sentiment import SentimentAnalyzer


class MockModel:
    """Mock model for testing sentiment analysis predictions.

    This mock provides consistent prediction behavior for testing
    without requiring actual ML model loading.
    """

    def __init__(self):
        """Initialize mock model with default predictions."""
        self.predictions = [
            {"label": "POSITIVE", "score": 0.9, "inference_time_ms": 10.0},
            {"label": "NEGATIVE", "score": 0.8, "inference_time_ms": 12.0},
            {"label": "NEUTRAL", "score": 0.7, "inference_time_ms": 8.0},
        ]
        self.call_count = 0

    def predict_batch(self, texts):
        """Mock batch prediction.

        Args:
            texts: List of text strings to predict.

        Returns:
            List of prediction dictionaries.
        """
        results = []
        for text in texts:
            result = self.predictions[self.call_count % len(self.predictions)]
            result = result.copy()
            result["text_length"] = len(text)
            result["model_name"] = "test_model"
            result["backend"] = "test"
            result["cached"] = False
            results.append(result)
            self.call_count += 1
        return results

    def is_ready(self):
        """Check if model is ready.

        Returns:
            Always True for testing.
        """
        return True

    def get_model_info(self):
        """Get model information.

        Returns:
            Dictionary with model name and version.
        """
        return {"name": "test_model", "version": "1.0.0"}


class MockAsyncModel:
    """Mock async model for testing async operations.

    Similar to MockModel but with async predict method.
    """

    def __init__(self):
        """Initialize mock async model."""
        self.predictions = [
            {"label": "POSITIVE", "score": 0.9, "inference_time_ms": 10.0},
            {"label": "NEGATIVE", "score": 0.8, "inference_time_ms": 12.0},
            {"label": "NEUTRAL", "score": 0.7, "inference_time_ms": 8.0},
        ]
        self.call_count = 0

    async def predict_batch(self, texts):
        """Mock async batch prediction.

        Args:
            texts: List of text strings to predict.

        Returns:
            List of prediction dictionaries.
        """
        results = []
        for text in texts:
            result = self.predictions[self.call_count % len(self.predictions)]
            result = result.copy()
            result["text_length"] = len(text)
            result["model_name"] = "test_async_model"
            result["backend"] = "test"
            result["cached"] = False
            results.append(result)
            self.call_count += 1
        return results

    def is_ready(self):
        """Check if model is ready.

        Returns:
            Always True for testing.
        """
        return True

    def get_model_info(self):
        """Get model information.

        Returns:
            Dictionary with model name and version.
        """
        return {"name": "test_async_model", "version": "1.0.0"}


class MockPerformanceConfig:
    """Mock performance configuration for testing."""

    def __init__(self):
        """Initialize with default performance settings."""
        self.async_batch_enabled = True
        self.async_batch_max_jobs = 1000
        self.async_batch_max_batch_size = 1000
        self.async_batch_default_timeout_seconds = 300
        self.async_batch_priority_high_limit = 100
        self.async_batch_priority_medium_limit = 500
        self.async_batch_priority_low_limit = 1000
        self.async_batch_cleanup_interval_seconds = 60
        self.async_batch_cache_ttl_seconds = 3600
        self.async_batch_result_cache_max_size = 1000


class MockKafkaSettings:
    """Mock Kafka settings for testing."""

    def __init__(self):
        """Initialize with default Kafka settings."""
        self.kafka_enabled = True
        self.kafka_bootstrap_servers = ["localhost:9092"]
        self.kafka_consumer_group = "test_consumer"
        self.kafka_topic = "test_topic"
        self.kafka_auto_offset_reset = "earliest"
        self.kafka_max_poll_records = 100
        self.kafka_session_timeout_ms = 30000
        self.kafka_heartbeat_interval_ms = 3000
        self.kafka_max_poll_interval_ms = 300000
        self.kafka_enable_auto_commit = False
        self.kafka_auto_commit_interval_ms = 5000
        self.kafka_consumer_threads = 2
        self.kafka_batch_size = 10
        self.kafka_processing_timeout_ms = 30000
        self.kafka_buffer_size = 1000
        self.kafka_dlq_topic = "test_dlq"
        self.kafka_dlq_enabled = True
        self.kafka_max_retries = 3
        self.kafka_producer_bootstrap_servers = ["localhost:9092"]
        self.kafka_producer_acks = "all"
        self.kafka_producer_retries = 3
        self.kafka_producer_batch_size = 16384
        self.kafka_producer_linger_ms = 5
        self.kafka_producer_compression_type = "lz4"


class MockSettings:
    """Mock application settings for testing.

    Combines various configuration aspects commonly needed in tests.
    """

    def __init__(self, **kwargs):
        """Initialize mock settings with optional overrides.

        Args:
            **kwargs: Optional attribute overrides.
        """
        # General settings
        self.enable_metrics = True
        self.app_version = "1.0.0"
        self.debug = True

        # Performance settings
        self.performance = MockPerformanceConfig()

        # Kafka settings
        kafka_settings = MockKafkaSettings()
        for attr in dir(kafka_settings):
            if not attr.startswith("_"):
                setattr(self, attr, getattr(kafka_settings, attr))

        # Async batch settings (backward compatibility)
        self.async_batch_enabled = True
        self.async_batch_max_jobs = 1000
        self.async_batch_max_batch_size = 1000
        self.async_batch_default_timeout_seconds = 300
        self.async_batch_priority_high_limit = 100
        self.async_batch_priority_medium_limit = 500
        self.async_batch_priority_low_limit = 1000
        self.async_batch_cleanup_interval_seconds = 60
        self.async_batch_cache_ttl_seconds = 3600
        self.async_batch_result_cache_max_size = 1000

        # Apply any overrides
        for key, value in kwargs.items():
            setattr(self, key, value)


def create_mock_analyzer():
    """Create a mock SentimentAnalyzer for testing.

    This factory function creates a properly configured mock that simulates
    the behavior of the real SentimentAnalyzer without loading actual models.

    Returns:
        Mock object with SentimentAnalyzer interface.
    """
    analyzer = Mock(spec=SentimentAnalyzer)
    analyzer.is_ready.return_value = True
    analyzer.predict.return_value = {
        "label": "POSITIVE",
        "score": 0.95,
        "inference_time_ms": 150.0,
        "model_name": "test-model",
        "text_length": 20,
    }
    analyzer.get_performance_metrics.return_value = {
        "torch_version": "2.1.1",
        "cuda_available": False,
        "cuda_memory_allocated_mb": 0,
        "cuda_memory_reserved_mb": 0,
        "cuda_device_count": 0,
    }
    analyzer.get_model_info.return_value = {
        "model_name": "test-model",
        "is_loaded": True,
        "is_ready": True,
        "cache_dir": None,
        "torch_version": "2.1.1",
        "cuda_available": False,
        "device_count": 0,
    }
    return analyzer
