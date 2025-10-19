"""
Tests for HashiCorp Vault integration.

These tests verify the secret management abstraction layer,
Vault client integration, and fallback mechanisms.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.secrets import (
    EnvSecretManager,
    SecretManager,
    VaultSecretManager,
    get_secret_manager,
)
from app.monitoring.vault_health import (
    VaultHealthMonitor,
    get_vault_monitor,
    vault_authentication_failures,
    vault_secret_rotation_warnings,
    vault_token_renewals,
)


class TestEnvSecretManager:
    """Test environment variable based secret manager."""

    def test_initialization(self):
        """Test that EnvSecretManager initializes correctly."""
        manager = EnvSecretManager(prefix="TEST_")
        assert manager.prefix == "TEST_"

    @patch.dict("os.environ", {"MLOPS_API_KEY": "test123key"})
    def test_get_secret_from_env(self):
        """Test retrieving secret from environment variable."""
        manager = EnvSecretManager(prefix="MLOPS_")
        value = manager.get_secret("api_key")
        assert value == "test123key"

    @patch.dict("os.environ", {})
    def test_get_secret_not_found(self):
        """Test retrieving non-existent secret returns default."""
        manager = EnvSecretManager(prefix="MLOPS_")
        value = manager.get_secret("missing_key", default="default_value")
        assert value == "default_value"

    @patch.dict(
        "os.environ", {"MLOPS_KEY1": "value1", "MLOPS_KEY2": "value2", "OTHER_KEY": "value3"}
    )
    def test_list_secrets(self):
        """Test listing secrets with prefix filter."""
        manager = EnvSecretManager(prefix="MLOPS_")
        secrets = manager.list_secrets()
        assert "key1" in secrets
        assert "key2" in secrets
        assert len([s for s in secrets if s.startswith("key")]) == 2

    def test_is_healthy(self):
        """Test that environment manager is always healthy."""
        manager = EnvSecretManager()
        assert manager.is_healthy() is True

    def test_get_health_info(self):
        """Test health info returns correct backend type."""
        manager = EnvSecretManager(prefix="MLOPS_")
        health = manager.get_health_info()
        assert health["backend"] == "environment"
        assert health["healthy"] is True
        assert "secret_count" in health


class TestVaultSecretManager:
    """Test Vault based secret manager."""

    @pytest.fixture
    def mock_hvac_client(self):
        """Create a mock hvac client."""
        with patch("app.core.secrets.hvac.Client") as mock_client:
            client_instance = MagicMock()
            client_instance.is_authenticated.return_value = True
            mock_client.return_value = client_instance
            yield client_instance

    def test_initialization_with_token(self, mock_hvac_client):
        """Test Vault manager initialization with token."""
        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")
        assert manager.vault_addr == "http://vault:8200"
        assert manager.client.token == "test-token"

    @patch("builtins.open", create=True)
    def test_kubernetes_authentication(self, mock_open, mock_hvac_client):
        """Test Kubernetes authentication method."""
        mock_open.return_value.__enter__.return_value.read.return_value = "kubernetes-jwt-token"

        manager = VaultSecretManager(vault_addr="http://vault:8200", role="mlops-sentiment")

        # Verify Kubernetes auth was called
        mock_hvac_client.auth.kubernetes.login.assert_called_once()

    def test_get_secret_from_vault(self, mock_hvac_client):
        """Test retrieving secret from Vault."""
        # Mock Vault response
        mock_hvac_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"value": "secret_value_from_vault"}}
        }

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")

        value = manager.get_secret("api_key")
        assert value == "secret_value_from_vault"

    def test_get_secret_with_caching(self, mock_hvac_client):
        """Test that secrets are cached."""
        mock_hvac_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"value": "cached_value"}}
        }

        manager = VaultSecretManager(
            vault_addr="http://vault:8200", token="test-token", cache_ttl=300
        )

        # First call
        value1 = manager.get_secret("api_key")
        # Second call (should be cached)
        value2 = manager.get_secret("api_key")

        assert value1 == value2
        # Vault should only be called once due to caching
        assert mock_hvac_client.secrets.kv.v2.read_secret_version.call_count == 1

    def test_set_secret(self, mock_hvac_client):
        """Test setting a secret in Vault."""
        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")

        success = manager.set_secret("new_key", "new_value")
        assert success is True

        # Verify Vault client was called
        mock_hvac_client.secrets.kv.v2.create_or_update_secret.assert_called_once()

    def test_list_secrets_from_vault(self, mock_hvac_client):
        """Test listing secrets from Vault."""
        mock_hvac_client.secrets.kv.v2.list_secrets.return_value = {
            "data": {"keys": ["api_key", "database_url", "slack_webhook"]}
        }

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")

        secrets = manager.list_secrets()
        assert len(secrets) == 3
        assert "api_key" in secrets

    def test_is_healthy(self, mock_hvac_client):
        """Test Vault health check."""
        mock_hvac_client.sys.read_health_status.return_value = {
            "sealed": False,
            "initialized": True,
        }

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")

        assert manager.is_healthy() is True

    def test_get_health_info(self, mock_hvac_client):
        """Test getting detailed Vault health information."""
        mock_hvac_client.sys.read_health_status.return_value = {
            "sealed": False,
            "initialized": True,
            "version": "1.15.0",
        }

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")

        health = manager.get_health_info()
        assert health["backend"] == "vault"
        assert health["healthy"] is True
        assert health["version"] == "1.15.0"

    def test_clear_cache(self, mock_hvac_client):
        """Test clearing secret cache."""
        mock_hvac_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"value": "test"}}
        }

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")

        # Populate cache
        manager.get_secret("test_key")
        assert len(manager._cache) > 0

        # Clear cache
        manager.clear_cache()
        assert len(manager._cache) == 0


class TestSecretManagerFactory:
    """Test the secret manager factory function."""

    def test_get_env_secret_manager(self):
        """Test factory returns EnvSecretManager when Vault is disabled."""
        manager = get_secret_manager(vault_enabled=False)
        assert isinstance(manager, EnvSecretManager)

    @patch("app.core.secrets.VaultSecretManager")
    def test_get_vault_secret_manager(self, mock_vault_class):
        """Test factory returns VaultSecretManager when Vault is enabled."""
        mock_instance = Mock(spec=VaultSecretManager)
        mock_vault_class.return_value = mock_instance

        manager = get_secret_manager(vault_enabled=True, vault_addr="http://vault:8200")

        # Should attempt to create VaultSecretManager
        mock_vault_class.assert_called_once()

    @patch("app.core.secrets.VaultSecretManager")
    def test_fallback_to_env_on_vault_failure(self, mock_vault_class):
        """Test fallback to EnvSecretManager if Vault initialization fails."""
        mock_vault_class.side_effect = RuntimeError("Vault connection failed")

        manager = get_secret_manager(vault_enabled=True, vault_addr="http://vault:8200")

        # Should fall back to environment manager
        assert isinstance(manager, EnvSecretManager)

    def test_factory_caching(self):
        """Test that factory function caches the secret manager instance."""
        manager1 = get_secret_manager(vault_enabled=False)
        manager2 = get_secret_manager(vault_enabled=False)

        # Should return the same instance due to lru_cache
        assert manager1 is manager2


class TestSecretManagerIntegration:
    """Integration tests for secret manager."""

    @patch.dict("os.environ", {"MLOPS_API_KEY": "env_value"})
    def test_env_manager_integration(self):
        """Test environment manager in realistic scenario."""
        manager = EnvSecretManager(prefix="MLOPS_")

        # Get secret
        api_key = manager.get_secret("api_key")
        assert api_key == "env_value"

        # Health check
        assert manager.is_healthy()

        # List secrets
        secrets = manager.list_secrets()
        assert "api_key" in secrets

    @patch("app.core.secrets.hvac.Client")
    @patch("builtins.open", create=True)
    def test_vault_manager_error_handling(self, mock_open, mock_hvac):
        """Test Vault manager handles errors gracefully."""
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("Vault error")
        mock_hvac.return_value = mock_client

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")

        # Should return default on error
        value = manager.get_secret("missing_key", default="fallback")
        assert value == "fallback"


class TestVaultErrorScenarios:
    """Test error handling and edge cases in Vault integration."""

    @pytest.fixture
    def mock_hvac_client(self):
        """Create a mock hvac client."""
        with patch("app.core.secrets.hvac.Client") as mock_client:
            client_instance = MagicMock()
            client_instance.is_authenticated.return_value = True
            mock_client.return_value = client_instance
            yield client_instance

    def test_vault_authentication_failure(self):
        """Test handling of Vault authentication failures."""
        with patch("app.core.secrets.hvac.Client") as mock_client:
            client_instance = MagicMock()
            client_instance.is_authenticated.return_value = False
            mock_client.return_value = client_instance

            with pytest.raises(RuntimeError, match="Failed to authenticate to Vault"):
                VaultSecretManager(vault_addr="http://vault:8200", token="invalid-token")

    def test_vault_connection_timeout(self, mock_hvac_client):
        """Test handling of Vault connection timeouts."""
        mock_hvac_client.secrets.kv.v2.read_secret_version.side_effect = Exception(
            "Connection timeout"
        )

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")
        value = manager.get_secret("api_key", default="fallback")

        assert value == "fallback"  # Should return default on error

    def test_vault_secret_not_found(self, mock_hvac_client):
        """Test handling of missing secrets in Vault."""
        mock_hvac_client.secrets.kv.v2.read_secret_version.side_effect = Exception(
            "Secret not found"
        )

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")
        value = manager.get_secret("nonexistent_key", default="default_value")

        assert value == "default_value"

    def test_vault_malformed_response(self, mock_hvac_client):
        """Test handling of malformed Vault responses."""
        # Mock response missing 'data' key
        mock_hvac_client.secrets.kv.v2.read_secret_version.return_value = {"data": {}}

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")
        value = manager.get_secret("malformed_key", default="default")

        assert value == "default"

    def test_vault_health_check_failure(self, mock_hvac_client):
        """Test Vault health check when Vault is sealed."""
        mock_hvac_client.sys.read_health_status.return_value = {
            "sealed": True,
            "initialized": True,
        }

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")
        assert manager.is_healthy() is False

    def test_kubernetes_auth_file_not_found(self):
        """Test Kubernetes authentication when service account token file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError("Token file not found")):
            with pytest.raises(RuntimeError, match="Kubernetes service account token not found"):
                VaultSecretManager(vault_addr="http://vault:8200", role="test-role")

    def test_cache_ttl_expiry(self, mock_hvac_client):
        """Test that cache respects TTL and refetches from Vault."""
        mock_hvac_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"value": "fresh_value"}}
        }

        manager = VaultSecretManager(
            vault_addr="http://vault:8200", token="test-token", cache_ttl=1  # 1 second TTL
        )

        # First call
        value1 = manager.get_secret("api_key")
        assert value1 == "fresh_value"

        # Sleep to expire cache
        import time

        time.sleep(1.1)

        # Second call should refetch
        value2 = manager.get_secret("api_key")
        assert value2 == "fresh_value"

        # Vault should be called twice (once initially, once after cache expiry)
        assert mock_hvac_client.secrets.kv.v2.read_secret_version.call_count == 2

    def test_list_secrets_vault_error(self, mock_hvac_client):
        """Test error handling when listing secrets fails."""
        mock_hvac_client.secrets.kv.v2.list_secrets.side_effect = Exception("List operation failed")

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")
        secrets = manager.list_secrets()

        assert secrets == []  # Should return empty list on error

    def test_set_secret_vault_error(self, mock_hvac_client):
        """Test error handling when setting secrets fails."""
        mock_hvac_client.secrets.kv.v2.create_or_update_secret.side_effect = Exception(
            "Write failed"
        )

        manager = VaultSecretManager(vault_addr="http://vault:8200", token="test-token")
        success = manager.set_secret("test_key", "test_value")

        assert success is False  # Should return False on error


class TestVaultHealthMonitor:
    """Test Vault health monitoring functionality."""

    @pytest.fixture
    def mock_secret_manager(self):
        """Create a mock secret manager."""
        manager = MagicMock()
        manager.is_healthy.return_value = True
        manager.get_health_info.return_value = {
            "backend": "vault",
            "healthy": True,
            "cache_size": 5,
        }
        return manager

    def test_health_monitor_initialization(self, mock_secret_manager):
        """Test VaultHealthMonitor initialization."""
        monitor = VaultHealthMonitor(mock_secret_manager)
        assert monitor.secret_manager == mock_secret_manager
        assert monitor.health_check_interval == 60
        assert len(monitor._secret_expiration_times) == 0

    def test_health_check_caching(self, mock_secret_manager):
        """Test that health checks are cached."""
        monitor = VaultHealthMonitor(mock_secret_manager)

        # First call
        result1 = monitor.check_vault_health()

        # Second call (should use cache)
        result2 = monitor.check_vault_health()

        # Secret manager should only be called once due to caching
        assert mock_secret_manager.is_healthy.call_count == 1
        assert result1 == result2

    def test_secret_expiration_tracking(self, mock_secret_manager):
        """Test tracking of secret expiration times."""
        monitor = VaultHealthMonitor(mock_secret_manager)

        future_time = datetime.now() + timedelta(days=30)
        monitor.set_secret_expiration("api_key", future_time)

        assert "api_key" in monitor._secret_expiration_times
        assert monitor._secret_expiration_times["api_key"] == future_time

    def test_secret_rotation_warning(self, mock_secret_manager):
        """Test secret rotation warnings for expiring secrets."""
        monitor = VaultHealthMonitor(mock_secret_manager)

        # Set expiration time that's close (within 7 days)
        soon_time = datetime.now() + timedelta(days=3)
        monitor.set_secret_expiration("expiring_key", soon_time)

        rotation_status = monitor.check_secret_rotation_status()

        assert "expiring_key" in rotation_status
        assert rotation_status["expiring_key"]["rotation_warning_sent"] is True

    def test_mounts_and_policies_check(self, mock_secret_manager):
        """Test checking Vault mounts and policies."""
        mock_secret_manager.client.sys.list_mounted_secrets_engines.return_value = {
            "data": {
                "secret/": {"type": "kv", "description": "KV v2 secrets engine"},
                "database/": {"type": "database", "description": "Database secrets engine"},
            }
        }
        mock_secret_manager.client.sys.list_policies.return_value = {
            "data": {"policies": ["default", "mlops-sentiment-dev"]}
        }

        monitor = VaultHealthMonitor(mock_secret_manager)
        result = monitor.check_mounts_and_policies()

        assert "mounts_enabled" in result
        assert "total_policies" in result
        assert result["total_policies"] == 2

    def test_authentication_methods_check(self, mock_secret_manager):
        """Test checking available authentication methods."""
        mock_secret_manager.client.sys.list_auth_methods.return_value = {
            "data": {
                "kubernetes/": {"type": "kubernetes"},
                "token/": {"type": "token"},
            }
        }

        monitor = VaultHealthMonitor(mock_secret_manager)
        result = monitor.check_authentication_methods()

        assert "kubernetes_auth_enabled" in result
        assert "jwt_auth_enabled" in result
        assert result["kubernetes_auth_enabled"] is True

    def test_token_status_check(self, mock_secret_manager):
        """Test checking token status."""
        mock_secret_manager.client.auth.token.lookup_self.return_value = {
            "data": {
                "id": "test-token-id",
                "expire_time": (datetime.now() + timedelta(hours=2)).timestamp(),
                "policies": ["default"],
                "renewable": True,
            }
        }

        monitor = VaultHealthMonitor(mock_secret_manager)
        result = monitor.check_token_status()

        assert "token_id" in result
        assert "expire_time" in result
        assert "needs_renewal" in result
        assert result["token_id"] == "test-token-id"

    def test_comprehensive_status(self, mock_secret_manager):
        """Test comprehensive status reporting."""
        monitor = VaultHealthMonitor(mock_secret_manager)

        # Mock all the individual check methods
        monitor.check_mounts_and_policies = MagicMock(return_value={"mounts_enabled": 2})
        monitor.check_authentication_methods = MagicMock(
            return_value={"kubernetes_auth_enabled": True}
        )
        monitor.check_token_status = MagicMock(return_value={"token_id": "test"})
        monitor.check_secret_rotation_status = MagicMock(return_value={"secret1": {"status": "ok"}})

        result = monitor.get_comprehensive_status()

        assert "health" in result
        assert "mounts_and_policies" in result
        assert "authentication" in result
        assert "token" in result
        assert "secret_rotation" in result
        assert "summary" in result

    def test_alert_callbacks(self, mock_secret_manager):
        """Test alert callback registration and triggering."""
        monitor = VaultHealthMonitor(mock_secret_manager)

        callback_called = []

        def test_callback(alert_data):
            callback_called.append(alert_data)

        monitor.register_alert_callback(test_callback)
        monitor._trigger_alert("warning", "Test alert", secret_key="test")

        assert len(callback_called) == 1
        assert callback_called[0]["type"] == "warning"
        assert callback_called[0]["message"] == "Test alert"

    def test_get_vault_monitor_singleton(self, mock_secret_manager):
        """Test that get_vault_monitor returns a singleton instance."""
        with patch("app.monitoring.vault_health.get_settings") as mock_settings:
            mock_settings.return_value.secret_manager = mock_secret_manager

            # First call should create instance
            monitor1 = get_vault_monitor()
            assert isinstance(monitor1, VaultHealthMonitor)

            # Second call should return same instance
            monitor2 = get_vault_monitor()
            assert monitor1 is monitor2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
