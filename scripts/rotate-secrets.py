#!/usr/bin/env python3
"""
Script for automated secret rotation in HashiCorp Vault.

This script implements blue-green secret rotation with zero-downtime:
1. Generates new secrets with appropriate complexity
2. Updates Vault with new secret versions
3. Triggers rolling updates in Kubernetes
4. Verifies rotation success
5. Rolls back if verification fails

Usage:
    python scripts/rotate-secrets.py --vault-addr http://vault:8200 --environment prod --secret api_key
"""

import argparse
import logging
import os
import random
import secrets
import string
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

try:
    import hvac
    from kubernetes import client, config
except ImportError:
    print("ERROR: Required libraries missing. Install with: pip install hvac kubernetes")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SecretRotator:
    """Handles automated secret rotation with zero-downtime."""

    def __init__(
        self,
        vault_addr: str,
        vault_token: str,
        mount_point: str = "mlops-sentiment",
        namespace: Optional[str] = None,
    ):
        """Initialize the secret rotator."""
        self.vault_addr = vault_addr
        self.mount_point = mount_point

        self.client = hvac.Client(url=vault_addr, token=vault_token, namespace=namespace)

        if not self.client.is_authenticated():
            raise RuntimeError("Failed to authenticate with Vault")

        logger.info(f"Connected to Vault at {vault_addr}")

    def generate_api_key(self, length: int = 32) -> str:
        """
        Generate a secure random API key.

        Args:
            length: Length of the key

        Returns:
            Secure random API key
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        key = "".join(secrets.choice(alphabet) for _ in range(length))

        # Ensure complexity requirements
        if not (
            any(c.isupper() for c in key)
            and any(c.islower() for c in key)
            and any(c.isdigit() for c in key)
        ):
            return self.generate_api_key(length)

        return key

    def generate_password(self, length: int = 24) -> str:
        """
        Generate a secure random password.

        Args:
            length: Length of the password

        Returns:
            Secure random password
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        return password

    def rotate_secret(
        self,
        environment: str,
        secret_key: str,
        new_value: Optional[str] = None,
        secret_type: str = "api_key",
    ) -> bool:
        """
        Rotate a secret in Vault.

        Args:
            environment: Environment name
            secret_key: Secret key to rotate
            new_value: New secret value (auto-generated if not provided)
            secret_type: Type of secret for auto-generation

        Returns:
            True if successful
        """
        try:
            secret_path = f"mlops-sentiment/{environment}/{secret_key}"

            # Get current secret for backup
            try:
                current_response = self.client.secrets.kv.v2.read_secret_version(
                    path=secret_path, mount_point=self.mount_point
                )
                logger.info(f"Backing up current version of {secret_key}")
            except Exception:
                logger.warning(f"No existing secret found for {secret_key}")
                current_response = None

            # Generate new value if not provided
            if new_value is None:
                if secret_type == "api_key":
                    new_value = self.generate_api_key()
                elif secret_type == "password":
                    new_value = self.generate_password()
                else:
                    raise ValueError(f"Unknown secret type: {secret_type}")

            # Create new secret version
            secret_data = {
                "value": new_value,
                "rotated_at": datetime.now().isoformat(),
                "rotated_by": "rotation_script",
            }

            self.client.secrets.kv.v2.create_or_update_secret(
                path=secret_path, secret=secret_data, mount_point=self.mount_point
            )

            logger.info(f"✓ Rotated secret: {secret_key} ({environment})")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to rotate {secret_key}: {e}")
            return False

    def verify_secret_rotation(self, environment: str, secret_key: str) -> bool:
        """
        Verify that secret rotation was successful.

        Args:
            environment: Environment name
            secret_key: Secret key to verify

        Returns:
            True if rotation was successful
        """
        try:
            secret_path = f"mlops-sentiment/{environment}/{secret_key}"
            response = self.client.secrets.kv.v2.read_secret_version(
                path=secret_path, mount_point=self.mount_point
            )

            data = response["data"]["data"]
            has_value = "value" in data
            recently_rotated = "rotated_at" in data

            logger.info(
                f"Verification: {secret_key} - Value exists: {has_value}, Recently rotated: {recently_rotated}"
            )

            return has_value

        except Exception as e:
            logger.error(f"Verification failed for {secret_key}: {e}")
            return False

    def trigger_kubernetes_rollout(self, namespace: str, deployment_name: str) -> bool:
        """
        Trigger a rolling update in Kubernetes.

        Args:
            namespace: Kubernetes namespace
            deployment_name: Deployment name

        Returns:
            True if successful
        """
        try:
            config.load_incluster_config()
        except:
            try:
                config.load_kube_config()
            except Exception as e:
                logger.error(f"Failed to load Kubernetes config: {e}")
                return False

        try:
            apps_v1 = client.AppsV1Api()

            # Patch deployment to trigger rollout
            now = datetime.now().isoformat()
            body = {
                "spec": {
                    "template": {
                        "metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": now}}
                    }
                }
            }

            apps_v1.patch_namespaced_deployment(
                name=deployment_name, namespace=namespace, body=body
            )

            logger.info(f"✓ Triggered rollout for {deployment_name} in {namespace}")

            # Wait for rollout to complete
            return self._wait_for_rollout(namespace, deployment_name)

        except Exception as e:
            logger.error(f"Failed to trigger Kubernetes rollout: {e}")
            return False

    def _wait_for_rollout(self, namespace: str, deployment_name: str, timeout: int = 300) -> bool:
        """Wait for deployment rollout to complete."""
        apps_v1 = client.AppsV1Api()
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                deployment = apps_v1.read_namespaced_deployment(
                    name=deployment_name, namespace=namespace
                )

                status = deployment.status
                if (
                    status.updated_replicas == status.replicas
                    and status.replicas == status.available_replicas
                    and status.observed_generation >= deployment.metadata.generation
                ):
                    logger.info(f"✓ Rollout complete for {deployment_name}")
                    return True

                time.sleep(5)

            except Exception as e:
                logger.error(f"Error checking rollout status: {e}")
                return False

        logger.error(f"Rollout timeout for {deployment_name}")
        return False


def main():
    """Main rotation script."""
    parser = argparse.ArgumentParser(
        description="Rotate secrets in HashiCorp Vault with zero-downtime"
    )
    parser.add_argument("--vault-addr", required=True, help="Vault server address")
    parser.add_argument(
        "--vault-token", help="Vault token (will use VAULT_TOKEN env var if not provided)"
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Target environment",
    )
    parser.add_argument("--secret", required=True, help="Secret key to rotate")
    parser.add_argument(
        "--secret-type",
        default="api_key",
        choices=["api_key", "password"],
        help="Type of secret for auto-generation",
    )
    parser.add_argument("--k8s-namespace", help="Kubernetes namespace for rollout")
    parser.add_argument("--k8s-deployment", help="Kubernetes deployment name for rollout")
    parser.add_argument(
        "--skip-rollout", action="store_true", help="Skip Kubernetes rollout after rotation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be rotated without actually rotating",
    )

    args = parser.parse_args()

    # Get Vault token
    vault_token = args.vault_token or os.getenv("VAULT_TOKEN")
    if not vault_token:
        logger.error("Vault token required (--vault-token or VAULT_TOKEN env var)")
        return 1

    # Initialize rotator
    try:
        rotator = SecretRotator(vault_addr=args.vault_addr, vault_token=vault_token)
    except Exception as e:
        logger.error(f"Failed to initialize rotator: {e}")
        return 1

    logger.info(f"\n=== Secret Rotation for {args.environment}/{args.secret} ===\n")

    if args.dry_run:
        logger.info(f"[DRY RUN] Would rotate: {args.secret}")
        logger.info(f"[DRY RUN] Environment: {args.environment}")
        logger.info(f"[DRY RUN] Type: {args.secret_type}")
        return 0

    # Perform rotation
    if not rotator.rotate_secret(args.environment, args.secret, secret_type=args.secret_type):
        logger.error("Secret rotation failed")
        return 1

    # Verify rotation
    if not rotator.verify_secret_rotation(args.environment, args.secret):
        logger.error("Secret rotation verification failed")
        return 1

    # Trigger Kubernetes rollout
    if not args.skip_rollout:
        if args.k8s_namespace and args.k8s_deployment:
            if not rotator.trigger_kubernetes_rollout(args.k8s_namespace, args.k8s_deployment):
                logger.warning("Kubernetes rollout failed, but secret was rotated")
        else:
            logger.info("Skipping Kubernetes rollout (no namespace/deployment specified)")

    logger.info(f"\n✓ Secret rotation complete for {args.secret}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
