"""
Secret management abstraction layer.

This module provides a unified interface for accessing secrets from different
sources (HashiCorp Vault, environment variables, etc.) with automatic caching,
rotation support, and health monitoring.
"""

import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class SecretManager(ABC):
    """Abstract base class for secret management implementations."""

    @abstractmethod
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret by key.

        Args:
            key: Secret key/path
            default: Default value if secret not found

        Returns:
            Secret value or default
        """
        pass

    @abstractmethod
    def list_secrets(self, prefix: str = "") -> list[str]:
        """
        List all available secret keys with optional prefix filter.

        Args:
            prefix: Optional prefix to filter secrets

        Returns:
            List of secret keys
        """
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if the secret manager backend is healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_health_info(self) -> Dict[str, Any]:
        """
        Get detailed health information about the secret backend.

        Returns:
            Dictionary with health metrics
        """
        pass


class EnvSecretManager(SecretManager):
    """
    Environment variable based secret manager.

    This implementation reads secrets from environment variables,
    suitable for local development and simple deployments.
    """

    def __init__(self, prefix: str = "MLOPS_"):
        """
        Initialize environment variable secret manager.

        Args:
            prefix: Prefix for environment variables
        """
        self.prefix = prefix
        logger.info("Initialized environment variable secret manager", prefix=prefix)

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from environment variable."""
        env_key = f"{self.prefix}{key.upper()}"
        value = os.getenv(env_key, default)

        if value is None:
            logger.warning("Secret not found in environment", key=key, env_key=env_key)

        return value

    def list_secrets(self, prefix: str = "") -> list[str]:
        """List all environment variables with the manager's prefix."""
        full_prefix = f"{self.prefix}{prefix.upper()}"
        return [
            key.replace(self.prefix, "").lower()
            for key in os.environ.keys()
            if key.startswith(full_prefix)
        ]

    def is_healthy(self) -> bool:
        """Environment variables are always available."""
        return True

    def get_health_info(self) -> Dict[str, Any]:
        """Get health information."""
        secret_count = len([k for k in os.environ.keys() if k.startswith(self.prefix)])
        return {
            "backend": "environment",
            "healthy": True,
            "secret_count": secret_count,
            "prefix": self.prefix,
        }


class VaultSecretManager(SecretManager):
    """
    HashiCorp Vault based secret manager.

    This implementation uses hvac to interact with Vault, supporting
    Kubernetes authentication, secret caching, and automatic rotation.
    """

    def __init__(
        self,
        vault_addr: str,
        namespace: Optional[str] = None,
        role: Optional[str] = None,
        mount_point: str = "mlops-sentiment",
        secrets_path: str = "mlops-sentiment",
        token: Optional[str] = None,
        cache_ttl: int = 300,
    ):
        """
        Initialize Vault secret manager.

        Args:
            vault_addr: Vault server address
            namespace: Vault namespace (Enterprise)
            role: Kubernetes auth role
            mount_point: KV v2 mount point
            secrets_path: Base path for secrets
            token: Vault token (if not using Kubernetes auth)
            cache_ttl: Cache TTL in seconds
        """
        try:
            import hvac
        except ImportError:
            raise ImportError(
                "hvac library is required for Vault integration. "
                "Install it with: pip install hvac"
            )

        self.vault_addr = vault_addr
        self.namespace = namespace
        self.role = role
        self.mount_point = mount_point
        self.secrets_path = secrets_path
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple[str, float]] = {}
        self._last_health_check: Optional[float] = None
        self._health_check_interval = 60  # Check every 60 seconds

        # Initialize Vault client
        self.client = hvac.Client(url=vault_addr, namespace=namespace)

        # Authenticate
        if token:
            self.client.token = token
            logger.info("Authenticated to Vault using provided token")
        elif role:
            self._authenticate_kubernetes(role)
        else:
            raise ValueError("Either token or role must be provided for Vault authentication")

        if not self.client.is_authenticated():
            raise RuntimeError("Failed to authenticate to Vault")

        logger.info(
            "Initialized Vault secret manager",
            vault_addr=vault_addr,
            namespace=namespace,
            role=role,
            mount_point=mount_point,
        )

    def _authenticate_kubernetes(self, role: str):
        """Authenticate using Kubernetes service account token."""
        try:
            # Read service account token
            with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as f:
                jwt = f.read().strip()

            # Authenticate with Vault
            self.client.auth.kubernetes.login(role=role, jwt=jwt)
            logger.info("Authenticated to Vault using Kubernetes auth", role=role)

        except FileNotFoundError:
            logger.error("Kubernetes service account token not found")
            raise RuntimeError(
                "Kubernetes service account token not found. "
                "Ensure the pod has a service account configured."
            )
        except Exception as e:
            logger.error("Kubernetes authentication failed", error=str(e), exc_info=True)
            raise RuntimeError(f"Kubernetes authentication failed: {e}")

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret from Vault with caching.

        Args:
            key: Secret key
            default: Default value if not found

        Returns:
            Secret value or default
        """
        # Check cache first
        if key in self._cache:
            cached_value, cached_time = self._cache[key]
            if time.time() - cached_time < self.cache_ttl:
                logger.debug("Returning cached secret", key=key)
                return cached_value

        # Fetch from Vault
        try:
            secret_path = f"{self.secrets_path}/{key}"
            response = self.client.secrets.kv.v2.read_secret_version(
                path=secret_path, mount_point=self.mount_point
            )

            value = response["data"]["data"].get("value")

            if value is not None:
                # Cache the value
                self._cache[key] = (value, time.time())
                logger.info("Retrieved secret from Vault", key=key)
                return value
            else:
                logger.warning("Secret found but has no 'value' field", key=key)
                return default

        except Exception as e:
            logger.error(
                "Failed to retrieve secret from Vault", key=key, error=str(e), exc_info=True
            )
            return default

    def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Set a secret in Vault.

        Args:
            key: Secret key
            value: Secret value
            metadata: Optional metadata

        Returns:
            True if successful
        """
        try:
            secret_path = f"{self.secrets_path}/{key}"
            secret_data = {"value": value}

            if metadata:
                secret_data.update(metadata)

            self.client.secrets.kv.v2.create_or_update_secret(
                path=secret_path, secret=secret_data, mount_point=self.mount_point
            )

            # Invalidate cache
            if key in self._cache:
                del self._cache[key]

            logger.info("Set secret in Vault", key=key)
            return True

        except Exception as e:
            logger.error("Failed to set secret in Vault", key=key, error=str(e), exc_info=True)
            return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        """List all secrets with optional prefix filter."""
        try:
            list_path = f"{self.secrets_path}/{prefix}" if prefix else self.secrets_path
            response = self.client.secrets.kv.v2.list_secrets(
                path=list_path, mount_point=self.mount_point
            )

            keys = response["data"]["keys"]
            logger.info("Listed secrets from Vault", count=len(keys), prefix=prefix)
            return keys

        except Exception as e:
            logger.error(
                "Failed to list secrets from Vault", prefix=prefix, error=str(e), exc_info=True
            )
            return []

    def is_healthy(self) -> bool:
        """Check if Vault is healthy and client is authenticated."""
        now = time.time()

        # Rate limit health checks
        if (
            self._last_health_check
            and (now - self._last_health_check) < self._health_check_interval
        ):
            return True

        try:
            health = self.client.sys.read_health_status(method="GET")
            self._last_health_check = now

            is_healthy = not health.get("sealed", True) and self.client.is_authenticated()

            if not is_healthy:
                logger.warning("Vault health check failed", health_status=health)

            return is_healthy

        except Exception as e:
            logger.error("Vault health check error", error=str(e), exc_info=True)
            return False

    def get_health_info(self) -> Dict[str, Any]:
        """Get detailed Vault health information."""
        try:
            health = self.client.sys.read_health_status(method="GET")

            return {
                "backend": "vault",
                "healthy": self.is_healthy(),
                "vault_addr": self.vault_addr,
                "namespace": self.namespace,
                "authenticated": self.client.is_authenticated(),
                "sealed": health.get("sealed", True),
                "initialized": health.get("initialized", False),
                "version": health.get("version", "unknown"),
                "cache_size": len(self._cache),
                "cache_ttl": self.cache_ttl,
            }

        except Exception as e:
            logger.error("Failed to get Vault health info", error=str(e), exc_info=True)
            return {"backend": "vault", "healthy": False, "error": str(e)}

    def clear_cache(self):
        """Clear all cached secrets."""
        self._cache.clear()
        logger.info("Cleared secret cache")


@lru_cache(maxsize=1)
def get_secret_manager(
    vault_enabled: bool = False,
    vault_addr: Optional[str] = None,
    vault_namespace: Optional[str] = None,
    vault_role: Optional[str] = None,
    vault_mount_point: str = "mlops-sentiment",
    vault_secrets_path: str = "mlops-sentiment",
    env_prefix: str = "MLOPS_",
) -> SecretManager:
    """
    Factory function to get the appropriate secret manager.

    Args:
        vault_enabled: Whether to use Vault
        vault_addr: Vault server address
        vault_namespace: Vault namespace
        vault_role: Kubernetes auth role
        vault_mount_point: KV v2 mount point
        vault_secrets_path: Base path for secrets
        env_prefix: Environment variable prefix

    Returns:
        SecretManager instance
    """
    if vault_enabled and vault_addr:
        try:
            return VaultSecretManager(
                vault_addr=vault_addr,
                namespace=vault_namespace,
                role=vault_role,
                mount_point=vault_mount_point,
                secrets_path=vault_secrets_path,
            )
        except Exception as e:
            logger.error(
                "Failed to initialize Vault secret manager, falling back to environment variables",
                error=str(e),
                exc_info=True,
            )
            return EnvSecretManager(prefix=env_prefix)
    else:
        return EnvSecretManager(prefix=env_prefix)
