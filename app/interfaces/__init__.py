"""
Service Interfaces for KubeSentiment

This module defines abstract base classes (interfaces) for all services in the application.
These interfaces promote:
- Loose coupling between components
- Easier testing through interface mocking
- Dependency Inversion Principle (DIP)
- Clear contracts for service implementations

Usage:
    from app.interfaces import IPredictionService, IStreamProcessor

    def my_function(prediction_service: IPredictionService):
        result = prediction_service.predict("sample text")
"""

from app.interfaces.prediction_interface import IPredictionService
from app.interfaces.batch_interface import IAsyncBatchService
from app.interfaces.stream_interface import IStreamProcessor
from app.interfaces.cache_interface import ICacheClient
from app.interfaces.kafka_interface import IKafkaConsumer
from app.interfaces.storage_interface import IDataWriter
from app.interfaces.drift_interface import IDriftDetector
from app.interfaces.explainability_interface import IExplainabilityEngine
from app.interfaces.optimization_interface import IGPUBatchOptimizer
from app.interfaces.resilience_interface import ICircuitBreaker, ILoadMetrics
from app.interfaces.registry_interface import IModelRegistry
from app.interfaces.buffer_interface import IAnomalyBuffer

__all__ = [
    # Core prediction services
    "IPredictionService",
    "IAsyncBatchService",
    "IStreamProcessor",
    # Infrastructure services
    "ICacheClient",
    "IKafkaConsumer",
    "IDataWriter",
    # Monitoring and quality services
    "IDriftDetector",
    "IExplainabilityEngine",
    # Optimization services
    "IGPUBatchOptimizer",
    # Resilience services
    "ICircuitBreaker",
    "ILoadMetrics",
    # Model management
    "IModelRegistry",
    # Storage
    "IAnomalyBuffer",
]
