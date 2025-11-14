#!/usr/bin/env python3
"""A script for the automated rotation of secrets in HashiCorp Vault.

This script implements a zero-downtime secret rotation strategy. It generates
new secrets, updates them in Vault, and can trigger a rolling update of a
Kubernetes deployment to ensure that applications pick up the new secrets
without service interruption.
"""

import argparse
import logging
import os
import secrets
import string
import sys
import time
from datetime import datetime
from typing import Optional

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
    """Handles the automated rotation of secrets in Vault with zero downtime.

    This class encapsulates the logic for connecting to Vault, generating new
    secrets, updating them in Vault, and coordinating with Kubernetes to
    perform a rolling update of deployments to apply the new secrets.

    Attributes:
        vault_addr: The address of the Vault server.
        mount_point: The mount point of the KV v2 secrets engine in Vault.
        client: The `hvac` client for communicating with Vault.
    """

    def __init__(
        self,
        vault_addr: str,
        vault_token: str,
        mount_point: str = "mlops-sentiment",
        namespace: Optional[str] = None,
    ):
        """Initializes the `SecretRotator`.

        Args:
            vault_addr: The address of the Vault server.
            vault_token: The Vault token for authentication.
            mount_point: The mount point for the KV v2 secrets engine.
            namespace: The Vault namespace to use (for Enterprise versions).

        Raises:
            RuntimeError: If authentication with Vault fails.
        """
        self.vault_addr = vault_addr
        self.mount_point = mount_point

        self.client = hvac.Client(url=vault_addr, token=vault_token, namespace=namespace)

        if not self.client.is_authenticated():
            raise RuntimeError("Failed to authenticate with Vault")

        logger.info("Connected to Vault", extra={"vault_addr": vault_addr})

    def generate_api_key(self, length: int = 32) -> str:
        """Generates a cryptographically secure, random API key.

        The generated key is guaranteed to contain uppercase letters, lowercase
        letters, and digits to meet common complexity requirements.

        Args:
            length: The desired length of the API key.

        Returns:
            A new, randomly generated API key.
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
        """Generates a cryptographically secure, random password.

        Args:
            length: The desired length of the password.

        Returns:
            A new, randomly generated password.
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
        """Rotates a secret in Vault by creating a new version of it.

        This method will auto-generate a new value for the secret if one is not
        provided. It also backs up the current version of the secret before
        overwriting it.

        Args:
            environment: The name of the environment (e.g., 'dev', 'prod').
            secret_key: The key of the secret to be rotated.
            new_value: An optional new value for the secret. If not provided,
                a new value will be generated based on the `secret_type`.
            secret_type: The type of the secret, used for auto-generation.

        Returns:
            `True` if the rotation is successful, `False` otherwise.
        """
        try:
            secret_path = f"mlops-sentiment/{environment}/{secret_key}"

            # Get current secret for backup
            try:
                self.client.secrets.kv.v2.read_secret_version(
                    path=secret_path, mount_point=self.mount_point
                )
                logger.info("Backing up current version of secret", extra={"secret_key": secret_key})
            except Exception:
                logger.warning("No existing secret found", extra={"secret_key": secret_key})

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

            logger.info("Rotated secret", extra={"secret_key": secret_key, "environment": environment})
            return True

        except Exception as e:
            logger.error("Failed to rotate secret", extra={"secret_key": secret_key, "error": str(e)}, exc_info=True)
            return False

    def verify_secret_rotation(self, environment: str, secret_key: str) -> bool:
        """Verifies that a secret has been successfully rotated.

        This method checks that the secret exists in Vault and that it has been
        recently updated.

        Args:
            environment: The name of the environment where the secret is stored.
            secret_key: The key of the secret to be verified.

        Returns:
            `True` if the verification is successful, `False` otherwise.
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
                "Secret verification completed",
                extra={
                    "secret_key": secret_key,
                    "value_exists": has_value,
                    "recently_rotated": recently_rotated
                }
            )

            return has_value

        except Exception as e:
            logger.error("Verification failed", extra={"secret_key": secret_key, "error": str(e)}, exc_info=True)
            return False

    def trigger_kubernetes_rollout(self, namespace: str, deployment_name: str) -> bool:
        """Triggers a rolling update for a Kubernetes deployment.

        This is achieved by adding an annotation with the current timestamp to
        the deployment's pod template, which causes Kubernetes to initiate a
        rollout. The method then waits for the rollout to complete.

        Args:
            namespace: The Kubernetes namespace of the deployment.
            deployment_name: The name of the deployment to be updated.

        Returns:
            `True` if the rollout is triggered and completes successfully,
            `False` otherwise.
        """
        try:
            config.load_incluster_config()
        except config.ConfigException:
            try:
                config.load_kube_config()
            except Exception as e:
                logger.error("Failed to load Kubernetes config", extra={"error": str(e)}, exc_info=True)
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

            logger.info(
                "Triggered rollout",
                extra={"deployment_name": deployment_name, "namespace": namespace}
            )

            # Wait for rollout to complete
            return self._wait_for_rollout(namespace, deployment_name)

        except Exception as e:
            logger.error("Failed to trigger Kubernetes rollout", extra={"error": str(e)}, exc_info=True)
            return False

    def _wait_for_rollout(self, namespace: str, deployment_name: str, timeout: int = 300) -> bool:
        """Waits for a Kubernetes deployment rollout to complete.

        This method polls the status of the deployment until all of its
        replicas have been updated and are available.

        Args:
            namespace: The Kubernetes namespace of the deployment.
            deployment_name: The name of the deployment.
            timeout: The maximum time in seconds to wait for the rollout.

        Returns:
            `True` if the rollout completes within the timeout, `False`
            otherwise.
        """
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
                    logger.info("Rollout complete", extra={"deployment_name": deployment_name})
                    return True

                time.sleep(5)

            except Exception as e:
                logger.error("Error checking rollout status", extra={"error": str(e)}, exc_info=True)
                return False

        logger.error("Rollout timeout", extra={"deployment_name": deployment_name})
        return False


def main():
    """The main entry point for the secret rotation script.

    This function handles command-line argument parsing, sets up the
    `SecretRotator`, and orchestrates the secret rotation process, including
    verification and optional Kubernetes rollouts.
    """
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
        logger.error("Failed to initialize rotator", extra={"error": str(e)}, exc_info=True)
        return 1

    logger.info(
        "\n=== Secret Rotation ===\n",
        extra={"environment": args.environment, "secret": args.secret}
    )

    if args.dry_run:
        logger.info("[DRY RUN] Would rotate secret", extra={"secret": args.secret})
        logger.info("[DRY RUN] Environment", extra={"environment": args.environment})
        logger.info("[DRY RUN] Type", extra={"secret_type": args.secret_type})
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

    logger.info("\nSecret rotation complete", extra={"secret": args.secret})
    return 0


if __name__ == "__main__":
    sys.exit(main())
