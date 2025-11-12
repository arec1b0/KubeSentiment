"""Monitoring, logging, and distributed tracing configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings


class MonitoringConfig(BaseSettings):
    """Monitoring, metrics, logging, and distributed tracing configuration.

    Attributes:
        enable_metrics: Enable metrics collection.
        log_level: Logging level.
        metrics_cache_ttl: Seconds to cache generated Prometheus metrics.
        advanced_metrics_enabled: Enable advanced metrics and KPIs tracking.
        advanced_metrics_detailed_tracking: Enable detailed per-prediction tracking.
        advanced_metrics_history_hours: Hours of metrics history to keep in memory.
        advanced_metrics_cost_per_1k: Estimated cost per 1000 predictions in USD.
        enable_tracing: Enable distributed tracing.
        tracing_backend: Tracing backend (jaeger, zipkin, otlp, or console).
        service_name: Service name for distributed tracing.
        jaeger_agent_host: Jaeger agent hostname.
        jaeger_agent_port: Jaeger agent port.
        zipkin_endpoint: Zipkin collector endpoint.
        otlp_endpoint: OTLP gRPC endpoint.
        tracing_excluded_urls: Comma-separated list of URLs to exclude from tracing.
    """

    # Metrics settings
    enable_metrics: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )
    metrics_cache_ttl: int = Field(
        default=5,
        description="Seconds to cache generated Prometheus metrics",
        ge=1,
        le=300,
    )

    # Advanced metrics
    advanced_metrics_enabled: bool = Field(
        default=True,
        description="Enable advanced metrics and KPIs tracking",
    )
    advanced_metrics_detailed_tracking: bool = Field(
        default=True,
        description="Enable detailed per-prediction tracking",
    )
    advanced_metrics_history_hours: int = Field(
        default=24,
        description="Hours of metrics history to keep in memory",
        ge=1,
        le=168,
    )
    advanced_metrics_cost_per_1k: float = Field(
        default=0.01,
        description="Estimated cost per 1000 predictions in USD",
        ge=0.0,
        le=100.0,
    )

    # Distributed tracing
    enable_tracing: bool = Field(
        default=True,
        description="Enable distributed tracing",
    )
    tracing_backend: str = Field(
        default="jaeger",
        description="Tracing backend: jaeger, zipkin, otlp, or console",
    )
    service_name: str = Field(
        default="sentiment-analysis-api",
        description="Service name for distributed tracing",
    )

    # Jaeger settings
    jaeger_agent_host: str = Field(
        default="jaeger",
        description="Jaeger agent hostname",
    )
    jaeger_agent_port: int = Field(
        default=6831,
        description="Jaeger agent port",
        ge=1024,
        le=65535,
    )

    # Zipkin settings
    zipkin_endpoint: str = Field(
        default="http://zipkin:9411",
        description="Zipkin collector endpoint",
    )

    # OTLP settings
    otlp_endpoint: str = Field(
        default="jaeger:4317",
        description="OTLP gRPC endpoint",
    )

    # Tracing exclusions
    tracing_excluded_urls: str = Field(
        default="/health,/metrics,/docs,/redoc,/openapi.json",
        description="Comma-separated list of URLs to exclude from tracing",
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
