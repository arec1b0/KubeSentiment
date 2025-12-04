"""
Application-level Chaos Engineering Middleware

This middleware injects controlled failures at the application level,
complementing infrastructure-level chaos experiments.
"""

import random
import asyncio
import time
from typing import Callable, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

logger = structlog.get_logger(__name__)


class ChaosType(str, Enum):
    """Types of chaos that can be injected"""
    LATENCY = "latency"
    ERROR = "error"
    EXCEPTION = "exception"
    PARTIAL_FAILURE = "partial_failure"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    DATA_CORRUPTION = "data_corruption"


@dataclass
class ChaosConfig:
    """Configuration for chaos injection"""
    enabled: bool = False
    chaos_probability: float = 0.1  # 10% of requests by default
    latency_ms_min: int = 100
    latency_ms_max: int = 5000
    error_codes: list[int] = None
    timeout_ms: int = 30000
    rate_limit_delay_ms: int = 1000
    excluded_paths: list[str] = None
    included_paths: list[str] = None
    chaos_types: list[ChaosType] = None

    def __post_init__(self):
        if self.error_codes is None:
            self.error_codes = [500, 503, 504]
        if self.excluded_paths is None:
            self.excluded_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        if self.chaos_types is None:
            self.chaos_types = [
                ChaosType.LATENCY,
                ChaosType.ERROR,
                ChaosType.EXCEPTION,
            ]


class ChaosMiddleware(BaseHTTPMiddleware):
    """
    Middleware for injecting chaos at the application level.

    Features:
    - Random latency injection
    - HTTP error responses
    - Raised exceptions
    - Partial failures
    - Timeout simulation
    - Rate limiting simulation

    Usage:
        app.add_middleware(
            ChaosMiddleware,
            config=ChaosConfig(
                enabled=True,
                chaos_probability=0.2,
                latency_ms_max=3000
            )
        )
    """

    def __init__(self, app: ASGIApp, config: ChaosConfig = None):
        """Initializes the ChaosMiddleware.

        Args:
            app: The ASGI application.
            config: Configuration for chaos injection.
        """
        super().__init__(app)
        self.config = config or ChaosConfig()
        self.request_count = 0
        self.chaos_count = 0
        logger.info(
            "chaos_middleware_initialized",
            enabled=self.config.enabled,
            probability=self.config.chaos_probability,
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request with potential chaos injection"""

        # Skip if chaos is disabled
        if not self.config.enabled:
            return await call_next(request)

        # Skip excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Check if path is in included list (if specified)
        if self.config.included_paths and not self._is_included_path(request.url.path):
            return await call_next(request)

        self.request_count += 1

        # Decide whether to inject chaos
        if not self._should_inject_chaos():
            return await call_next(request)

        self.chaos_count += 1
        chaos_type = self._select_chaos_type()

        logger.warning(
            "chaos_injected",
            chaos_type=chaos_type,
            path=request.url.path,
            method=request.method,
            chaos_count=self.chaos_count,
            total_requests=self.request_count,
        )

        try:
            return await self._inject_chaos(chaos_type, request, call_next)
        except Exception as e:
            logger.error(
                "chaos_injection_failed",
                chaos_type=chaos_type,
                error=str(e),
                exc_info=True,
            )
            # If chaos injection itself fails, continue normally
            return await call_next(request)

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should be excluded from chaos"""
        return any(excluded in path for excluded in self.config.excluded_paths)

    def _is_included_path(self, path: str) -> bool:
        """Check if path is in included list"""
        return any(included in path for included in self.config.included_paths)

    def _should_inject_chaos(self) -> bool:
        """Determine if chaos should be injected for this request"""
        return random.random() < self.config.chaos_probability

    def _select_chaos_type(self) -> ChaosType:
        """Randomly select a chaos type from configured types"""
        return random.choice(self.config.chaos_types)

    async def _inject_chaos(
        self, chaos_type: ChaosType, request: Request, call_next: Callable
    ) -> Response:
        """Inject the selected chaos type"""

        if chaos_type == ChaosType.LATENCY:
            return await self._inject_latency(request, call_next)

        elif chaos_type == ChaosType.ERROR:
            return await self._inject_error(request)

        elif chaos_type == ChaosType.EXCEPTION:
            return await self._inject_exception(request)

        elif chaos_type == ChaosType.TIMEOUT:
            return await self._inject_timeout(request, call_next)

        elif chaos_type == ChaosType.RATE_LIMIT:
            return await self._inject_rate_limit(request, call_next)

        elif chaos_type == ChaosType.PARTIAL_FAILURE:
            return await self._inject_partial_failure(request, call_next)

        else:
            # Fallback to normal processing
            return await call_next(request)

    async def _inject_latency(self, request: Request, call_next: Callable) -> Response:
        """Inject random latency"""
        delay_ms = random.randint(
            self.config.latency_ms_min, self.config.latency_ms_max
        )
        logger.info("chaos_latency_injected", delay_ms=delay_ms)
        await asyncio.sleep(delay_ms / 1000.0)
        return await call_next(request)

    async def _inject_error(self, request: Request) -> Response:
        """Inject an HTTP error response"""
        error_code = random.choice(self.config.error_codes)
        logger.info("chaos_error_injected", status_code=error_code)
        return Response(
            content=f'{{"error": "Chaos injected error", "code": "{error_code}"}}',
            status_code=error_code,
            media_type="application/json",
        )

    async def _inject_exception(self, request: Request) -> Response:
        """Inject an exception"""
        logger.info("chaos_exception_injected")
        raise HTTPException(
            status_code=500,
            detail="Chaos injected exception: Simulated application failure",
        )

    async def _inject_timeout(self, request: Request, call_next: Callable) -> Response:
        """Inject a timeout"""
        timeout_ms = self.config.timeout_ms
        logger.info("chaos_timeout_injected", timeout_ms=timeout_ms)

        try:
            return await asyncio.wait_for(
                call_next(request), timeout=timeout_ms / 1000.0
            )
        except asyncio.TimeoutError:
            return Response(
                content='{"error": "Chaos injected timeout"}',
                status_code=504,
                media_type="application/json",
            )

    async def _inject_rate_limit(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Inject rate limiting delay"""
        delay_ms = self.config.rate_limit_delay_ms
        logger.info("chaos_rate_limit_injected", delay_ms=delay_ms)
        await asyncio.sleep(delay_ms / 1000.0)
        return Response(
            content='{"error": "Rate limit exceeded (chaos injected)"}',
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": str(delay_ms // 1000)},
        )

    async def _inject_partial_failure(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Inject partial failure (successful but with degraded data)"""
        logger.info("chaos_partial_failure_injected")
        response = await call_next(request)

        # Add header to indicate degraded response
        response.headers["X-Chaos-Partial-Failure"] = "true"
        response.headers["X-Chaos-Quality"] = "degraded"

        return response

    def get_stats(self) -> Dict[str, Any]:
        """Get chaos injection statistics"""
        chaos_rate = (
            self.chaos_count / self.request_count if self.request_count > 0 else 0
        )
        return {
            "enabled": self.config.enabled,
            "total_requests": self.request_count,
            "chaos_injected": self.chaos_count,
            "chaos_rate": chaos_rate,
            "configured_probability": self.config.chaos_probability,
        }


class TargetedChaosMiddleware(BaseHTTPMiddleware):
    """
    More targeted chaos injection based on specific conditions.

    Example use cases:
    - Inject errors only for specific sentiment scores
    - Add latency only during batch processing
    - Fail requests from specific user agents
    """

    def __init__(
        self,
        app: ASGIApp,
        chaos_config: ChaosConfig = None,
        target_conditions: Optional[Dict[str, Any]] = None,
    ):
        """Initializes the TargetedChaosMiddleware.

        Args:
            app: The ASGI application.
            chaos_config: Chaos configuration.
            target_conditions: Dictionary of conditions to match.
        """
        super().__init__(app)
        self.chaos_config = chaos_config or ChaosConfig()
        self.target_conditions = target_conditions or {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with conditional chaos injection"""

        if not self.chaos_config.enabled:
            return await call_next(request)

        # Check if conditions are met for chaos injection
        if not self._conditions_met(request):
            return await call_next(request)

        # Inject chaos similar to base middleware
        chaos_middleware = ChaosMiddleware(self.app, self.chaos_config)
        return await chaos_middleware.dispatch(request, call_next)

    def _conditions_met(self, request: Request) -> bool:
        """Check if chaos should be injected based on conditions"""

        # Example condition checks
        if "user_agent" in self.target_conditions:
            user_agent = request.headers.get("user-agent", "")
            if self.target_conditions["user_agent"] not in user_agent:
                return False

        if "method" in self.target_conditions:
            if request.method not in self.target_conditions["method"]:
                return False

        if "header" in self.target_conditions:
            header_name, header_value = self.target_conditions["header"]
            if request.headers.get(header_name) != header_value:
                return False

        return True


# Utility functions for enabling/disabling chaos at runtime
_chaos_middleware_instance: Optional[ChaosMiddleware] = None


def set_chaos_middleware(instance: ChaosMiddleware):
    """Store reference to chaos middleware for runtime control"""
    global _chaos_middleware_instance
    _chaos_middleware_instance = instance


def enable_chaos():
    """Enable chaos injection at runtime"""
    if _chaos_middleware_instance:
        _chaos_middleware_instance.config.enabled = True
        logger.info("chaos_enabled_at_runtime")


def disable_chaos():
    """Disable chaos injection at runtime"""
    if _chaos_middleware_instance:
        _chaos_middleware_instance.config.enabled = False
        logger.info("chaos_disabled_at_runtime")


def get_chaos_stats() -> Optional[Dict[str, Any]]:
    """Get chaos injection statistics"""
    if _chaos_middleware_instance:
        return _chaos_middleware_instance.get_stats()
    return None


def update_chaos_config(**kwargs):
    """Update chaos configuration at runtime"""
    if _chaos_middleware_instance:
        for key, value in kwargs.items():
            if hasattr(_chaos_middleware_instance.config, key):
                setattr(_chaos_middleware_instance.config, key, value)
        logger.info("chaos_config_updated", **kwargs)
