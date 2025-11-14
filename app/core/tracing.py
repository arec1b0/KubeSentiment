"""
OpenTelemetry distributed tracing configuration for MLOps sentiment analysis.

This module provides comprehensive distributed tracing using OpenTelemetry,
supporting both Jaeger and Zipkin backends for trace collection and visualization.
"""

from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TracingConfig:
    """Configuration for OpenTelemetry distributed tracing."""

    def __init__(self):
        self.settings = get_settings()
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None

    def setup_tracing(self) -> None:
        """Initialize and configure OpenTelemetry distributed tracing."""
        if not self.settings.enable_tracing:
            logger.info("Distributed tracing is disabled")
            return

        try:
            # Create resource with service information
            resource = Resource(
                attributes={
                    SERVICE_NAME: self.settings.service_name,
                    SERVICE_VERSION: self.settings.app_version,
                    "deployment.environment": self.settings.environment,
                    "service.namespace": "mlops",
                }
            )

            # Create TracerProvider
            self.tracer_provider = TracerProvider(resource=resource)

            # Configure exporters based on settings
            self._configure_exporters()

            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)

            # Get tracer instance
            self.tracer = trace.get_tracer(__name__, self.settings.app_version)

            # Instrument libraries
            self._instrument_libraries()

            logger.info(
                "Distributed tracing initialized successfully",
                service_name=self.settings.service_name,
                tracing_backend=self.settings.tracing_backend
            )

        except Exception as e:
            logger.error("Failed to initialize distributed tracing", error=str(e), exc_info=True)

    def _configure_exporters(self) -> None:
        """Configure trace exporters based on settings."""
        backend = self.settings.tracing_backend.lower()

        if backend == "jaeger":
            self._setup_jaeger_exporter()
        elif backend == "zipkin":
            self._setup_zipkin_exporter()
        elif backend == "otlp":
            self._setup_otlp_exporter()
        elif backend == "console":
            self._setup_console_exporter()
        else:
            logger.warning("Unknown tracing backend, using console exporter", backend=backend)
            self._setup_console_exporter()

    def _setup_jaeger_exporter(self) -> None:
        """Configure Jaeger exporter."""
        jaeger_exporter = JaegerExporter(
            agent_host_name=self.settings.jaeger_agent_host,
            agent_port=self.settings.jaeger_agent_port,
            udp_split_oversized_batches=True,
        )

        span_processor = BatchSpanProcessor(jaeger_exporter)
        self.tracer_provider.add_span_processor(span_processor)

        logger.info(
            "Jaeger exporter configured",
            host=self.settings.jaeger_agent_host,
            port=self.settings.jaeger_agent_port
        )

    def _setup_zipkin_exporter(self) -> None:
        """Configure Zipkin exporter."""
        zipkin_exporter = ZipkinExporter(
            endpoint=f"{self.settings.zipkin_endpoint}/api/v2/spans",
        )

        span_processor = BatchSpanProcessor(zipkin_exporter)
        self.tracer_provider.add_span_processor(span_processor)

        logger.info("Zipkin exporter configured", endpoint=self.settings.zipkin_endpoint)

    def _setup_otlp_exporter(self) -> None:
        """Configure OTLP (OpenTelemetry Protocol) exporter."""
        otlp_exporter = OTLPSpanExporter(
            endpoint=self.settings.otlp_endpoint,
            insecure=True,  # Use True for development, False for production with TLS
        )

        span_processor = BatchSpanProcessor(otlp_exporter)
        self.tracer_provider.add_span_processor(span_processor)

        logger.info("OTLP exporter configured", endpoint=self.settings.otlp_endpoint)

    def _setup_console_exporter(self) -> None:
        """Configure console exporter for debugging."""
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        self.tracer_provider.add_span_processor(span_processor)

        logger.info("Console exporter configured for debugging")

    def _instrument_libraries(self) -> None:
        """Instrument third-party libraries for automatic tracing."""
        # Instrument logging
        LoggingInstrumentor().instrument(set_logging_format=True)

        # Instrument HTTP clients
        RequestsInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()

        # Instrument Redis if available
        try:
            RedisInstrumentor().instrument()
            logger.info("Redis instrumentation enabled")
        except Exception as e:
            logger.debug("Redis instrumentation not available", error=str(e))

    def instrument_fastapi(self, app) -> None:
        """
        Instrument FastAPI application for automatic request tracing.

        Args:
            app: FastAPI application instance
        """
        if not self.settings.enable_tracing:
            return

        try:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=self.tracer_provider,
                excluded_urls=self.settings.tracing_excluded_urls,
            )
            logger.info("FastAPI instrumentation enabled")
        except Exception as e:
            logger.error("Failed to instrument FastAPI", error=str(e), exc_info=True)

    def get_tracer(self) -> trace.Tracer:
        """
        Get the configured tracer instance.

        Returns:
            OpenTelemetry Tracer instance
        """
        if self.tracer is None:
            return trace.get_tracer(__name__)
        return self.tracer


# Global tracing configuration instance
_tracing_config: Optional[TracingConfig] = None


def get_tracing_config() -> TracingConfig:
    """
    Get or create the global tracing configuration instance.

    Returns:
        TracingConfig instance
    """
    global _tracing_config
    if _tracing_config is None:
        _tracing_config = TracingConfig()
    return _tracing_config


def setup_tracing() -> None:
    """Initialize distributed tracing."""
    config = get_tracing_config()
    config.setup_tracing()


def instrument_fastapi_app(app) -> None:
    """
    Instrument FastAPI application for distributed tracing.

    Args:
        app: FastAPI application instance
    """
    config = get_tracing_config()
    config.instrument_fastapi(app)


def get_current_span() -> trace.Span:
    """
    Get the current active span.

    Returns:
        Current OpenTelemetry Span
    """
    return trace.get_current_span()


def add_span_attributes(**attributes) -> None:
    """
    Add attributes to the current span.

    Args:
        **attributes: Key-value pairs to add as span attributes
    """
    span = get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(name: str, **attributes) -> None:
    """
    Add an event to the current span.

    Args:
        name: Event name
        **attributes: Event attributes
    """
    span = get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=attributes)


def set_span_status(status_code: StatusCode, description: Optional[str] = None) -> None:
    """
    Set the status of the current span.

    Args:
        status_code: Status code (OK, ERROR, UNSET)
        description: Optional status description
    """
    span = get_current_span()
    if span.is_recording():
        span.set_status(Status(status_code, description))


def record_exception(exception: Exception) -> None:
    """
    Record an exception in the current span.

    Args:
        exception: Exception to record
    """
    span = get_current_span()
    if span.is_recording():
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))


# Context manager for creating traced operations
class traced_operation:
    """
    Context manager for creating traced operations.

    Usage:
        with traced_operation("my_operation", key1="value1"):
            # Your code here
            pass
    """

    def __init__(self, operation_name: str, **attributes):
        self.operation_name = operation_name
        self.attributes = attributes
        self.span = None

    def __enter__(self):
        tracer = get_tracing_config().get_tracer()
        self.span = tracer.start_span(self.operation_name)
        if self.attributes:
            for key, value in self.attributes.items():
                self.span.set_attribute(key, value)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.record_exception(exc_val)
            self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
        else:
            self.span.set_status(Status(StatusCode.OK))
        self.span.end()
        return False

