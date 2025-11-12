"""HashiCorp Vault secrets management configuration."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class VaultConfig(BaseSettings):
    """HashiCorp Vault secrets management configuration.

    Attributes:
        vault_enabled: Enable HashiCorp Vault for secrets management.
        vault_addr: Vault server address.
        vault_namespace: Vault namespace for multi-tenancy (Enterprise feature).
        vault_role: Kubernetes service account role for Vault authentication.
        vault_mount_point: KV v2 secrets engine mount point in Vault.
        vault_secrets_path: Base path for secrets in Vault.
        vault_token: Vault token for direct authentication (not recommended for production).
    """

    vault_enabled: bool = Field(
        default=False,
        description="Enable HashiCorp Vault for secrets management",
    )
    vault_addr: Optional[str] = Field(
        default=None,
        description="Vault server address (e.g., http://vault:8200)",
    )
    vault_namespace: Optional[str] = Field(
        default="mlops",
        description="Vault namespace for multi-tenancy (Enterprise feature)",
    )
    vault_role: Optional[str] = Field(
        default=None,
        description="Kubernetes service account role for Vault authentication",
    )
    vault_mount_point: str = Field(
        default="mlops-sentiment",
        description="KV v2 secrets engine mount point in Vault",
    )
    vault_secrets_path: str = Field(
        default="mlops-sentiment",
        description="Base path for secrets in Vault",
    )
    vault_token: Optional[str] = Field(
        default=None,
        description="Vault token for direct authentication (not recommended for production)",
        exclude=True,  # Don't include in API responses
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
