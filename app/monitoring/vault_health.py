"""
Vault health monitoring and metrics collection.

This module provides health checks, metrics, and monitoring
for HashiCorp Vault integration.
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from prometheus_client import Counter, Gauge, Histogram

from app.core.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics for Vault monitoring
vault_connection_status = Gauge(
    "vault_connection_status", "Vault connection health status (1=healthy, 0=unhealthy)"
)

vault_secret_access_total = Counter(
    "vault_secret_access_total",
    "Total number of secret accesses from Vault",
    ["secret_key", "status"],
)

vault_secret_access_duration = Histogram(
    "vault_secret_access_duration_seconds",
    "Time spent accessing secrets from Vault",
    ["secret_key"],
)

vault_secret_cache_hits = Counter(
    "vault_secret_cache_hits_total", "Total number of secret cache hits"
)

vault_secret_cache_misses = Counter(
    "vault_secret_cache_misses_total", "Total number of secret cache misses"
)

vault_secret_expiration_time = Gauge(
    "vault_secret_expiration_seconds", "Time until secret expiration in seconds", ["secret_key"]
)

# Additional Vault monitoring metrics
vault_authentication_failures = Counter(
    "vault_authentication_failures_total", "Total number of Vault authentication failures"
)

vault_token_renewals = Counter("vault_token_renewals_total", "Total number of token renewals")

vault_secret_rotation_warnings = Counter(
    "vault_secret_rotation_warnings_total", "Total number of secret rotation warnings"
)

vault_mount_status = Gauge(
    "vault_mount_status", "Status of Vault mounts (1=enabled, 0=disabled)", ["mount_path"]
)

vault_policy_violations = Counter(
    "vault_policy_violations_total", "Total number of policy violations", ["policy_name"]
)


class VaultHealthMonitor:
    """Monitors the health of a Vault instance and tracks related metrics.

    This class provides a comprehensive suite of tools for monitoring a
    HashiCorp Vault secret manager. It periodically checks Vault's health,
    tracks secret access patterns, monitors for secret expirations, and
    provides detailed status information about the Vault instance.

    Attributes:
        secret_manager: An instance of a secret manager to be monitored.
        last_health_check: The timestamp of the last health check.
        health_check_interval: The interval in seconds between health checks.
    """

    def __init__(self, secret_manager):
        """Initializes the Vault health monitor.

        Args:
            secret_manager: An instance of a `SecretManager` to monitor.
                This should typically be a `VaultSecretManager`.
        """
        self.secret_manager = secret_manager
        self.last_health_check: Optional[datetime] = None
        self.health_check_interval = 60  # seconds
        self._cached_health_info: Optional[Dict[str, Any]] = None
        self._secret_expiration_times: Dict[str, datetime] = {}
        self._rotation_warnings_sent: Dict[str, datetime] = {}
        self._alert_callbacks = []

    def check_vault_health(self) -> Dict[str, Any]:
        """Performs a health check on the Vault connection.

        This method queries the secret manager for its health status. To avoid
        excessive requests, the result is cached for a configurable interval.

        Returns:
            A dictionary containing the health status and other details.
        """
        now = datetime.now()

        # Use cached result if recent enough
        if (
            self.last_health_check
            and (now - self.last_health_check).seconds < self.health_check_interval
        ):
            return self._cached_health_info

        try:
            is_healthy = self.secret_manager.is_healthy()
            health_info = self.secret_manager.get_health_info()

            # Update Prometheus metric
            vault_connection_status.set(1 if is_healthy else 0)

            self.last_health_check = now
            self._cached_health_info = {
                "healthy": is_healthy,
                "last_check": now.isoformat(),
                "details": health_info,
            }

            if is_healthy:
                logger.debug("Vault health check passed", **health_info)
            else:
                logger.warning("Vault health check failed", **health_info)

            return self._cached_health_info

        except Exception as e:
            logger.error("Vault health check error", error=str(e), exc_info=True)
            vault_connection_status.set(0)

            return {"healthy": False, "last_check": now.isoformat(), "error": str(e)}

    def track_secret_access(
        self, secret_key: str, duration: float, success: bool, cached: bool = False
    ):
        """Tracks metrics for a single secret access operation.

        This method updates several Prometheus metrics related to secret
        access, including the total count, duration, and cache hit/miss rates.

        Args:
            secret_key: The key of the secret that was accessed.
            duration: The duration of the access operation in seconds.
            success: A flag indicating whether the access was successful.
            cached: A flag indicating whether the result was from the cache.
        """
        # Track access count
        status = "success" if success else "failure"
        vault_secret_access_total.labels(secret_key=secret_key, status=status).inc()

        # Track duration
        vault_secret_access_duration.labels(secret_key=secret_key).observe(duration)

        # Track cache hits/misses
        if cached:
            vault_secret_cache_hits.inc()
        else:
            vault_secret_cache_misses.inc()

    def check_secret_expiration(self, secret_key: str, expiration_time: Optional[datetime] = None):
        """Monitors the expiration time of a secret.

        If a secret is nearing its expiration, this method will log a warning.
        It also updates a Prometheus gauge with the time until expiration.

        Args:
            secret_key: The key of the secret to check.
            expiration_time: The expiration time of the secret.
        """
        if expiration_time:
            seconds_until_expiration = (expiration_time - datetime.now()).total_seconds()
            vault_secret_expiration_time.labels(secret_key=secret_key).set(
                max(0, seconds_until_expiration)
            )

            # Log warning if expiration is soon
            if seconds_until_expiration < 86400 * 7:  # 7 days
                logger.warning(
                    "Secret expiring soon",
                    secret_key=secret_key,
                    days_until_expiration=seconds_until_expiration / 86400,
                )

    def check_mounts_and_policies(self) -> Dict[str, Any]:
        """Checks the status of mounts and lists policies in Vault.

        Returns:
            A dictionary containing information about the enabled and disabled
            mounts, as well as a list of all policies.
        """
        try:
            if hasattr(self.secret_manager, "client"):
                client = self.secret_manager.client

                # Check mount status
                mounts = client.sys.list_mounted_secrets_engines()
                mount_status = {}

                for mount_path, mount_info in mounts.get("data", {}).items():
                    is_enabled = mount_info.get("type", "generic") != "generic" or mount_path in [
                        "secret/",
                        "sys/",
                    ]
                    mount_status[mount_path] = is_enabled
                    vault_mount_status.labels(mount_path=mount_path).set(1 if is_enabled else 0)

                # Check policies
                policies = client.sys.list_policies()
                policy_list = policies.get("data", {}).get("policies", [])

                return {
                    "mounts_enabled": len([m for m, status in mount_status.items() if status]),
                    "mounts_disabled": len([m for m, status in mount_status.items() if not status]),
                    "total_policies": len(policy_list),
                    "mount_status": mount_status,
                    "policies": policy_list,
                }

            return {"error": "Vault client not available"}

        except Exception as e:
            logger.error("Failed to check mounts and policies", error=str(e), exc_info=True)
            return {"error": str(e)}

    def check_authentication_methods(self) -> Dict[str, Any]:
        """Checks the enabled authentication methods in Vault.

        Returns:
            A dictionary listing the available authentication methods.
        """
        try:
            if hasattr(self.secret_manager, "client"):
                client = self.secret_manager.client
                auth_methods = client.sys.list_auth_methods()

                return {
                    "auth_methods": list(auth_methods.get("data", {}).keys()),
                    "kubernetes_auth_enabled": "kubernetes/" in auth_methods.get("data", {}),
                    "jwt_auth_enabled": "jwt/" in auth_methods.get("data", {}),
                }

            return {"error": "Vault client not available"}

        except Exception as e:
            logger.error("Failed to check authentication methods", error=str(e), exc_info=True)
            return {"error": str(e)}

    def check_token_status(self) -> Dict[str, Any]:
        """Checks the status of the current Vault authentication token.

        This method provides information about the current token, such as its
        expiration time and whether it needs to be renewed.

        Returns:
            A dictionary containing the token's status information.
        """
        try:
            if hasattr(self.secret_manager, "client"):
                client = self.secret_manager.client

                token_info = client.auth.token.lookup_self()
                token_data = token_info.get("data", {})

                # Check if token needs renewal (less than 1 hour remaining)
                expire_time = datetime.fromtimestamp(token_data.get("expire_time", 0))
                now = datetime.now()
                time_until_expiry = (expire_time - now).total_seconds()

                needs_renewal = time_until_expiry < 3600  # 1 hour

                if needs_renewal:
                    vault_token_renewals.inc()
                    logger.info("Token needs renewal", time_until_expiry=time_until_expiry)

                return {
                    "token_id": token_data.get("id", "unknown"),
                    "expire_time": expire_time.isoformat(),
                    "time_until_expiry_seconds": time_until_expiry,
                    "needs_renewal": needs_renewal,
                    "policies": token_data.get("policies", []),
                    "renewable": token_data.get("renewable", False),
                }

            return {"error": "Vault client not available"}

        except Exception as e:
            vault_authentication_failures.inc()
            logger.error("Failed to check token status", error=str(e), exc_info=True)
            return {"error": str(e)}

    def register_alert_callback(self, callback):
        """Registers a callback function to be called when an alert is triggered.

        Args:
            callback: A function that accepts a dictionary as its single
                argument. This dictionary will contain the alert data.
        """
        self._alert_callbacks.append(callback)

    def _trigger_alert(self, alert_type: str, message: str, **kwargs):
        """Triggers an alert and notifies all registered callbacks.

        Args:
            alert_type: The type of the alert (e.g., 'error', 'warning').
            message: The alert message.
            **kwargs: Additional data to include in the alert.
        """
        alert_data = {
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }

        logger.warning("Vault alert triggered", alert_type=alert_type, message=message, **kwargs)

        for callback in self._alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error("Alert callback failed", error=str(e), exc_info=True)

    def check_secret_rotation_status(self) -> Dict[str, Any]:
        """Checks the rotation status of all tracked secrets.

        If a secret is nearing its expiration, this method will trigger a
        warning alert.

        Returns:
            A dictionary containing the rotation status of each tracked secret.
        """
        try:
            rotation_info = {}

            for secret_key, expiration_time in self._secret_expiration_times.items():
                now = datetime.now()
                time_until_expiry = (expiration_time - now).total_seconds()

                # Check if secret is expiring soon (within 7 days)
                if time_until_expiry < 86400 * 7 and secret_key not in self._rotation_warnings_sent:
                    vault_secret_rotation_warnings.inc()
                    self._rotation_warnings_sent[secret_key] = now
                    self._trigger_alert(
                        "warning",
                        f"Secret {secret_key} expires soon",
                        secret_key=secret_key,
                        days_until_expiry=time_until_expiry / 86400,
                    )

                rotation_info[secret_key] = {
                    "expiration_time": expiration_time.isoformat(),
                    "time_until_expiry_seconds": time_until_expiry,
                    "rotation_warning_sent": secret_key in self._rotation_warnings_sent,
                }

            return rotation_info

        except Exception as e:
            logger.error("Failed to check secret rotation status", error=str(e), exc_info=True)
            return {"error": str(e)}

    def set_secret_expiration(self, secret_key: str, expiration_time: datetime):
        """Sets the expiration time for a secret to be monitored.

        Args:
            secret_key: The key of the secret.
            expiration_time: The `datetime` object representing when the
                secret will expire.
        """
        self._secret_expiration_times[secret_key] = expiration_time
        self.check_secret_expiration(secret_key, expiration_time)

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Provides a comprehensive status report of the Vault integration.

        This method aggregates the results from several other check methods to
        give a complete overview of the Vault's status.

        Returns:
            A dictionary containing a detailed status report.
        """
        health_info = self.check_vault_health()
        mounts_info = self.check_mounts_and_policies()
        auth_info = self.check_authentication_methods()
        token_info = self.check_token_status()
        rotation_info = self.check_secret_rotation_status()

        return {
            "health": health_info,
            "mounts_and_policies": mounts_info,
            "authentication": auth_info,
            "token": token_info,
            "secret_rotation": rotation_info,
            "summary": {
                "overall_healthy": health_info.get("healthy", False),
                "total_mounts": mounts_info.get("mounts_enabled", 0)
                + mounts_info.get("mounts_disabled", 0),
                "auth_methods_count": len(auth_info.get("auth_methods", [])),
                "secrets_tracked": len(self._secret_expiration_times),
                "rotation_warnings": len(self._rotation_warnings_sent),
            },
        }

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Provides a summary of key metrics related to the Vault integration.

        Returns:
            A dictionary containing a summary of Vault metrics.
        """
        health_info = self.check_vault_health()

        return {
            "vault_healthy": health_info["healthy"],
            "last_health_check": health_info["last_check"],
            "backend": health_info.get("details", {}).get("backend", "unknown"),
            "cache_size": health_info.get("details", {}).get("cache_size", 0),
            "secrets_tracked": len(self._secret_expiration_times),
            "rotation_warnings_sent": len(self._rotation_warnings_sent),
        }


def get_vault_monitor():
    """Retrieves a singleton instance of the `VaultHealthMonitor`.

    This factory function ensures that only one instance of the monitor is
    created and used throughout the application.

    Returns:
        The singleton `VaultHealthMonitor` instance.
    """
    from app.core.config import get_settings

    settings = get_settings()

    if not hasattr(get_vault_monitor, "_monitor"):
        get_vault_monitor._monitor = VaultHealthMonitor(settings.secret_manager)

    return get_vault_monitor._monitor
