"""
Vault health monitoring and metrics collection for the MLOps sentiment analysis service.

This module provides a dedicated `VaultHealthMonitor` class for monitoring the
health and performance of the HashiCorp Vault integration. It includes health
checks, Prometheus metrics, and detailed status reporting for various aspects
of Vault, such as connection status, secret access, and token expiration.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from prometheus_client import Counter, Gauge, Histogram

from app.core.logging import get_logger

logger = get_logger(__name__)

# --- Prometheus Metric Definitions for Vault Monitoring ---

vault_connection_status = Gauge(
    "vault_connection_status", "Vault connection health (1=healthy, 0=unhealthy)"
)
vault_secret_access_total = Counter(
    "vault_secret_access_total", "Total secret accesses from Vault", ["secret_key", "status"]
)
vault_secret_access_duration = Histogram(
    "vault_secret_access_duration_seconds", "Secret access duration", ["secret_key"]
)
vault_secret_cache_hits = Counter("vault_secret_cache_hits_total", "Total secret cache hits")
vault_secret_cache_misses = Counter("vault_secret_cache_misses_total", "Total secret cache misses")
vault_token_renewals = Counter("vault_token_renewals_total", "Total Vault token renewals")


class VaultHealthMonitor:
    """Monitors the health of a Vault instance and tracks related metrics.

    This class provides a comprehensive suite of tools for monitoring a
    HashiCorp Vault secret manager. It periodically checks Vault's health,
    tracks secret access patterns, and provides detailed status information
    about the Vault instance, making it easier to operate and debug in a
    production environment.
    """

    def __init__(self, secret_manager):
        """Initializes the Vault health monitor.

        Args:
            secret_manager: An instance of a `SecretManager` to monitor. This
                should typically be a `VaultSecretManager`.
        """
        self.secret_manager = secret_manager
        self.last_health_check: Optional[datetime] = None
        self.health_check_interval = 60  # in seconds

    def check_vault_health(self) -> Dict[str, Any]:
        """Performs a health check on the Vault connection.

        This method queries the secret manager for its health status and updates
        the `vault_connection_status` Prometheus gauge. To avoid excessive
        requests, the result is cached for a configurable interval.

        Returns:
            A dictionary containing the health status and other details.
        """
        now = datetime.now()
        if (
            self.last_health_check
            and (now - self.last_health_check).seconds < self.health_check_interval
        ):
            return {"healthy": vault_connection_status._value.get(), "cached": True}

        try:
            is_healthy = self.secret_manager.is_healthy()
            vault_connection_status.set(1 if is_healthy else 0)
            self.last_health_check = now
            return {"healthy": is_healthy, "last_check": now.isoformat()}
        except Exception as e:
            vault_connection_status.set(0)
            logger.error("Vault health check error", error=str(e), exc_info=True)
            return {"healthy": False, "error": str(e)}

    def track_secret_access(
        self, secret_key: str, duration: float, success: bool, cached: bool = False
    ):
        """Tracks metrics for a single secret access operation.

        This method updates several Prometheus metrics related to secret access,
        including the total count, duration, and cache hit/miss rates. This
        provides valuable insights into secret usage patterns and performance.

        Args:
            secret_key: The key of the secret that was accessed.
            duration: The duration of the access operation in seconds.
            success: A flag indicating whether the access was successful.
            cached: A flag indicating whether the result was served from the cache.
        """
        status = "success" if success else "failure"
        vault_secret_access_total.labels(secret_key=secret_key, status=status).inc()
        vault_secret_access_duration.labels(secret_key=secret_key).observe(duration)
        if cached:
            vault_secret_cache_hits.inc()
        else:
            vault_secret_cache_misses.inc()

    def check_token_status(self) -> Dict[str, Any]:
        """Checks the status of the current Vault authentication token.

        This method provides information about the current token, such as its
        expiration time and whether it needs to be renewed. This is important
        for ensuring that the application can maintain its authenticated
        session with Vault.

        Returns:
            A dictionary containing the token's status information.
        """
        try:
            if hasattr(self.secret_manager, "client"):
                token_info = self.secret_manager.client.auth.token.lookup_self()
                token_data = token_info.get("data", {})
                expire_time = datetime.fromtimestamp(token_data.get("expire_time", 0))
                needs_renewal = (expire_time - datetime.now()).total_seconds() < 3600
                if needs_renewal:
                    vault_token_renewals.inc()
                return {
                    "renewable": token_data.get("renewable", False),
                    "needs_renewal": needs_renewal,
                }
        except Exception as e:
            logger.error("Failed to check token status", error=str(e), exc_info=True)
            return {"error": str(e)}
        return {}

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Provides a comprehensive status report of the Vault integration.

        This method aggregates the results from several other check methods to
        give a complete overview of the Vault's status, which is useful for
        debugging and monitoring.

        Returns:
            A dictionary containing a detailed status report.
        """
        health = self.check_vault_health()
        token_status = self.check_token_status()
        return {"health": health, "token_status": token_status}


_vault_monitor: Optional[VaultHealthMonitor] = None


def get_vault_monitor() -> VaultHealthMonitor:
    """Retrieves a singleton instance of the `VaultHealthMonitor`.

    This factory function ensures that only one instance of the monitor is
    created and used throughout the application, providing a single, consistent
    source for all Vault-related monitoring.

    Returns:
        The singleton `VaultHealthMonitor` instance.
    """
    global _vault_monitor
    if _vault_monitor is None:
        from app.core.config import get_settings

        settings = get_settings()
        _vault_monitor = VaultHealthMonitor(settings.secret_manager)
    return _vault_monitor
