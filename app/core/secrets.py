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
    """Defines the interface for a secret management system.

    This abstract base class specifies the contract that all secret manager
    implementations must follow. It provides a consistent way to interact with
    different secret backends, such as environment variables or HashiCorp Vault.
    """

    @abstractmethod
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a secret by its key.

        Args:
            key: The key or path identifying the secret.
            default: The value to return if the secret is not found.

        Returns:
            The value of the secret, or the default value if not found.
        """
        pass

    @abstractmethod
    def list_secrets(self, prefix: str = "") -> list[str]:
        """Lists available secret keys, optionally filtered by a prefix.

        Args:
            prefix: An optional prefix to filter the secret keys.

        Returns:
            A list of secret keys.
        """
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Checks the health of the secret manager's backend.

        Returns:
            `True` if the backend is healthy and accessible, `False` otherwise.
        """
        pass

    @abstractmethod
    def get_health_info(self) -> Dict[str, Any]:
        """Retrieves detailed health information about the secret backend.

        Returns:
            A dictionary containing health metrics and status information.
        """
        pass


class EnvSecretManager(SecretManager):
    """A secret manager that retrieves secrets from environment variables.

    This implementation is suitable for local development or simple deployment
    scenarios where secrets are passed to the application through its
    environment.

    Attributes:
        prefix: The prefix used to identify relevant environment variables.
    """

    def __init__(self, prefix: str = "MLOPS_"):
        """Initializes the environment variable secret manager.

        Args:
            prefix: The prefix to look for on environment variables.
        """
        self.prefix = prefix
        logger.info("Initialized environment variable secret manager", prefix=prefix)

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a secret from an environment variable.

        The key is converted to uppercase and prefixed with the configured
        `prefix` to form the environment variable name.

        Args:
            key: The key of the secret to retrieve.
            default: The default value to return if the variable is not set.

        Returns:
            The value of the environment variable, or the default value.
        """
        env_key = f"{self.prefix}{key.upper()}"
        value = os.getenv(env_key, default)

        if value is None:
            logger.warning("Secret not found in environment", key=key, env_key=env_key)

        return value

    def list_secrets(self, prefix: str = "") -> list[str]:
        """Lists environment variables that match the configured prefix.

        Args:
            prefix: An additional prefix to filter the variables.

        Returns:
            A list of secret keys (without the main prefix).
        """
        full_prefix = f"{self.prefix}{prefix.upper()}"
        return [
            key.replace(self.prefix, "").lower()
            for key in os.environ.keys()
            if key.startswith(full_prefix)
        ]

    def is_healthy(self) -> bool:
        """Checks the health of the secret manager.

        For environment variables, this always returns `True` as they are
        inherently available to the process.

        Returns:
            Always returns `True`.
        """
        return True

    def get_health_info(self) -> Dict[str, Any]:
        """Provides health information about the environment secret manager.

        This method returns a dictionary indicating the backend type, its
        health status, and the number of secrets found with the configured
        prefix.

        Returns:
            A dictionary containing health information.
        """
        secret_count = len([k for k in os.environ.keys() if k.startswith(self.prefix)])
        return {
            "backend": "environment",
            "healthy": True,
            "secret_count": secret_count,
            "prefix": self.prefix,
        }


class VaultSecretManager(SecretManager):
    """A secret manager for interacting with HashiCorp Vault.

    This implementation connects to a Vault instance to manage secrets. It
    supports authentication via Kubernetes service accounts or a direct token,
    and includes features like in-memory caching with a configurable TTL.

    Attributes:
        vault_addr: The address of the Vault server.
        namespace: The Vault namespace (for Enterprise versions).
        role: The Kubernetes authentication role.
        mount_point: The mount point of the KV v2 secrets engine.
        secrets_path: The base path for the application's secrets.
        cache_ttl: The time-to-live for the in-memory secret cache.
        client: The `hvac` client instance for communicating with Vault.
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
        """Initializes the Vault secret manager and authenticates with Vault.

        Args:
            vault_addr: The address of the Vault server.
            namespace: The Vault namespace to use (for Enterprise versions).
            role: The Kubernetes service account role for authentication.
            mount_point: The mount point for the KV v2 secrets engine.
            secrets_path: The base path where secrets are stored in Vault.
            token: A Vault token for direct authentication (not for production).
            cache_ttl: The time-to-live in seconds for the in-memory cache.

        Raises:
            ImportError: If the `hvac` library is not installed.
            ValueError: If neither a token nor a role is provided.
            RuntimeError: If authentication with Vault fails.
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
        """Authenticates with Vault using a Kubernetes service account.

        This method reads the service account's JWT from the pod's filesystem
        and uses it to authenticate with Vault against a configured Kubernetes
        authentication role.

        Args:
            role: The Vault role to authenticate against.

        Raises:
            RuntimeError: If the service account token is not found or if
                authentication fails.
        """
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
        """Retrieves a secret from Vault, using an in-memory cache.

        This method first checks its local cache for the secret. If a valid,
        non-expired entry is found, it's returned immediately. Otherwise, it
        fetches the secret from Vault, caches it, and then returns it.

        Args:
            key: The key of the secret to retrieve.
            default: The default value to return if the secret is not found.

        Returns:
            The value of the secret, or the default value.
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
        """Creates or updates a secret in Vault.

        This method writes a secret to the configured path in Vault's KV v2
        secrets engine. If the secret already exists, it creates a new version.
        After a successful write, it invalidates the corresponding entry in
        the local cache.

        Args:
            key: The key of the secret to set.
            value: The value of the secret.
            metadata: Optional metadata to store with the secret.

        Returns:
            `True` if the secret was set successfully, `False` otherwise.
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
        """Lists the keys of secrets stored at a given path in Vault.

        Args:
            prefix: An optional prefix to narrow down the listing.

        Returns:
            A list of secret keys.
        """
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
        """Checks the health of the Vault server and the client's authentication.

        This method checks if the Vault server is unsealed and if the client
        is still authenticated. To avoid excessive requests, the health check
        is rate-limited.

        Returns:
            `True` if Vault is healthy and the client is authenticated, `False`
            otherwise.
        """
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
        """Retrieves detailed health and status information from Vault.

        This method provides a snapshot of the Vault backend's status,
        including its authentication status, whether it's sealed, and cache
        metrics.

        Returns:
            A dictionary containing detailed health information.
        """
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
        """Clears the in-memory secret cache.

        This forces the next call to `get_secret` for any key to fetch the
        latest version from Vault.
        """
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
    """A factory function to create and configure a secret manager.

    This function determines which secret manager to instantiate based on the
    provided configuration. If Vault is enabled and a server address is given,
    it attempts to create a `VaultSecretManager`. If that fails or if Vault is
    not enabled, it falls back to an `EnvSecretManager`.

    The `@lru_cache(maxsize=1)` decorator ensures that this function is executed
    only once, effectively making the secret manager a singleton.

    Args:
        vault_enabled: A flag to enable the Vault secret manager.
        vault_addr: The address of the Vault server.
        vault_namespace: The Vault namespace to use.
        vault_role: The Kubernetes service account role for authentication.
        vault_mount_point: The mount point for the KV v2 secrets engine.
        vault_secrets_path: The base path for secrets in Vault.
        env_prefix: The prefix for environment variables, used by the fallback
            `EnvSecretManager`.

    Returns:
        An instance of a `SecretManager` implementation.
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
