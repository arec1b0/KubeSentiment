#!/usr/bin/env python3
"""
Script to migrate secrets from GitHub Actions secrets to HashiCorp Vault.

This script helps with the migration process by:
1. Reading secrets from various sources (env, file, interactive input)
2. Validating secret format and strength
3. Uploading secrets to Vault with proper structure
4. Creating backups before migration
5. Verifying successful migration

Usage:
    python scripts/migrate-secrets-to-vault.py --vault-addr http://vault:8200 --environment dev
"""

import argparse
import getpass
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import hvac
    import yaml
except ImportError:
    print("ERROR: Required libraries not found. Install with: pip install hvac pyYAML")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SecretValidator:
    """Validates secret format, strength, and security requirements."""

    @staticmethod
    def validate_api_key(api_key: str) -> Tuple[bool, str]:
        """Validate API key format and strength."""
        if not api_key:
            return False, "API key cannot be empty"

        if len(api_key) < 16:
            return False, "API key must be at least 16 characters long"

        # Check for required character types
        has_upper = bool(re.search(r'[A-Z]', api_key))
        has_lower = bool(re.search(r'[a-z]', api_key))
        has_digit = bool(re.search(r'[0-9]', api_key))
        has_special = bool(re.search(r'[^A-Za-z0-9]', api_key))

        if not (has_upper and has_lower and has_digit):
            return False, "API key must contain uppercase, lowercase, and numeric characters"

        if not has_special:
            logger.warning("API key should include special characters for better security")

        return True, "Valid API key"

    @staticmethod
    def validate_database_url(url: str) -> Tuple[bool, str]:
        """Validate database URL format."""
        if not url:
            return False, "Database URL cannot be empty"

        # Basic URL pattern validation
        url_pattern = re.compile(
            r'^(postgresql://|mysql://|mongodb://|redis://)[^@\s]+@[^@\s]+\.[^@\s]+:\d+/.+$'
        )

        if not url_pattern.match(url):
            return False, "Database URL must be in format: protocol://user:pass@host:port/database"

        return True, "Valid database URL"

    @staticmethod
    def validate_webhook_url(url: str) -> Tuple[bool, str]:
        """Validate webhook URL format."""
        if not url:
            return False, "Webhook URL cannot be empty"

        url_pattern = re.compile(r'^https://hooks\.slack\.com/services/[^/\s]+$')
        if not url_pattern.match(url):
            return False, "Webhook URL must be a valid Slack webhook URL"

        return True, "Valid webhook URL"

    @staticmethod
    def validate_mlflow_uri(uri: str) -> Tuple[bool, str]:
        """Validate MLflow tracking URI."""
        if not uri:
            return False, "MLflow URI cannot be empty"

        # Allow various formats
        valid_formats = [
            r'^http://.+:\d+$',  # HTTP with port
            r'^https://.+:\d+$',  # HTTPS with port
            r'^sqlite:///.*$',   # SQLite file
            r'^postgresql://.*$',  # PostgreSQL
        ]

        for pattern in valid_formats:
            if re.match(pattern, uri):
                return True, "Valid MLflow URI"

        return False, "MLflow URI must be a valid HTTP/HTTPS URL, SQLite path, or PostgreSQL connection"

    def validate_secret(self, key: str, value: str) -> Tuple[bool, str]:
        """Validate a secret based on its key."""
        validators = {
            "api_key": self.validate_api_key,
            "database_url": self.validate_database_url,
            "db_url": self.validate_database_url,
            "webhook_url": self.validate_webhook_url,
            "slack_webhook": self.validate_webhook_url,
            "mlflow_tracking_uri": self.validate_mlflow_uri,
            "mlflow_uri": self.validate_mlflow_uri,
        }

        # Find matching validator
        for secret_type, validator_func in validators.items():
            if secret_type in key.lower():
                return validator_func(value)

        # Generic validation for unknown secrets
        if not value:
            return False, f"Secret '{key}' cannot be empty"

        if len(value) < 8:
            return False, f"Secret '{key}' must be at least 8 characters long"

        return True, f"Valid secret '{key}'"


class ProgressTracker:
    """Track migration progress with visual feedback."""

    def __init__(self, total_items: int):
        self.total = total_items
        self.current = 0
        self.start_time = time.time()

    def update(self, item_name: str = None):
        """Update progress."""
        self.current += 1
        percentage = (self.current / self.total) * 100

        elapsed = time.time() - self.start_time
        rate = self.current / elapsed if elapsed > 0 else 0

        if item_name:
            logger.info(f"Progress: [{self.current:2d}/{self.total}] {percentage:5.1f}% - {item_name}")
        else:
            logger.info(f"Progress: [{self.current}/{self.total}] {percentage:5.1f}%")

    def finish(self):
        """Mark progress as complete."""
        elapsed = time.time() - self.start_time
        logger.info(f"Migration completed in {elapsed".1f"}s ({self.current}/{self.total} items)")


def get_secret_interactive(secret_name: str) -> Optional[str]:
    """Prompt user for secret value interactively."""
    try:
        value = getpass.getpass(f"Enter value for {secret_name} (hidden): ")
        if not value:
            logger.warning(f"No value provided for {secret_name}")
            return None
        return value
    except KeyboardInterrupt:
        logger.info("\nCancelled by user")
        return None


class SecretMigrator:
    """Handles migration of secrets to Vault."""

    def __init__(
        self,
        vault_addr: str,
        vault_token: str,
        mount_point: str = "mlops-sentiment",
        namespace: Optional[str] = None,
    ):
        """
        Initialize the secret migrator.

        Args:
            vault_addr: Vault server address
            vault_token: Vault authentication token
            mount_point: KV v2 mount point
            namespace: Vault namespace (optional)
        """
        self.vault_addr = vault_addr
        self.mount_point = mount_point
        self.validator = SecretValidator()

        self.client = hvac.Client(url=vault_addr, token=vault_token, namespace=namespace)

        if not self.client.is_authenticated():
            raise RuntimeError("Failed to authenticate with Vault")

        logger.info(f"Connected to Vault at {vault_addr}")

    def validate_secret_before_migration(self, key: str, value: str) -> Tuple[bool, str]:
        """Validate a secret before migration."""
        return self.validator.validate_secret(key, value)

    def backup_secrets(self, environment: str, backup_file: str):
        """
        Create a backup of existing secrets.

        Args:
            environment: Environment name (dev, staging, prod)
            backup_file: Path to backup file
        """
        logger.info(f"Backing up secrets for environment: {environment}")

        try:
            secrets_path = f"mlops-sentiment/{environment}"
            response = self.client.secrets.kv.v2.list_secrets(
                path=secrets_path, mount_point=self.mount_point
            )

            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "environment": environment,
                "secrets": {},
            }

            for key in response["data"]["keys"]:
                secret_response = self.client.secrets.kv.v2.read_secret_version(
                    path=f"{secrets_path}/{key}", mount_point=self.mount_point
                )
                backup_data["secrets"][key] = secret_response["data"]["data"]

            with open(backup_file, "w") as f:
                json.dump(backup_data, f, indent=2)

            logger.info(f"Backup saved to {backup_file}")

        except Exception as e:
            logger.warning(f"Could not create backup: {e}")

    def migrate_secret(
        self,
        environment: str,
        secret_key: str,
        secret_value: str,
        metadata: Optional[Dict] = None,
        progress_tracker: Optional[ProgressTracker] = None
    ) -> bool:
        """
        Migrate a single secret to Vault with validation.

        Args:
            environment: Environment name
            secret_key: Secret key/name
            secret_value: Secret value
            metadata: Optional metadata
            progress_tracker: Progress tracker for updates

        Returns:
            True if successful
        """
        # Validate secret before migration
        is_valid, validation_msg = self.validate_secret_before_migration(secret_key, secret_value)

        if not is_valid:
            logger.error(f"✗ Validation failed for {secret_key}: {validation_msg}")
            return False

        logger.info(f"✓ Validation passed for {secret_key}: {validation_msg}")

        try:
            secret_path = f"mlops-sentiment/{environment}/{secret_key}"
            secret_data = {"value": secret_value}

            if metadata:
                secret_data["metadata"] = metadata

            self.client.secrets.kv.v2.create_or_update_secret(
                path=secret_path, secret=secret_data, mount_point=self.mount_point
            )

            logger.info(f"✓ Migrated secret: {secret_key} ({environment})")

            if progress_tracker:
                progress_tracker.update(secret_key)

            return True

        except Exception as e:
            logger.error(f"✗ Failed to migrate {secret_key}: {e}")
            return False

    def verify_secret(self, environment: str, secret_key: str) -> bool:
        """
        Verify that a secret was successfully migrated.

        Args:
            environment: Environment name
            secret_key: Secret key to verify

        Returns:
            True if secret exists and is accessible
        """
        try:
            secret_path = f"mlops-sentiment/{environment}/{secret_key}"
            response = self.client.secrets.kv.v2.read_secret_version(
                path=secret_path, mount_point=self.mount_point
            )

            return "value" in response["data"]["data"]

        except Exception as e:
            logger.error(f"Verification failed for {secret_key}: {e}")
            return False


def get_secret_interactive(secret_name: str) -> Optional[str]:
    """Prompt user for secret value interactively."""
    try:
        value = getpass.getpass(f"Enter value for {secret_name} (hidden): ")
        if not value:
            logger.warning(f"No value provided for {secret_name}")
            return None
        return value
    except KeyboardInterrupt:
        logger.info("\nCancelled by user")
        return None


def main():
    """Main migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate secrets from GitHub Actions to HashiCorp Vault"
    )
    parser.add_argument(
        "--vault-addr", required=True, help="Vault server address (e.g., http://vault:8200)"
    )
    parser.add_argument("--vault-token", help="Vault token (will prompt if not provided)")
    parser.add_argument(
        "--environment",
        required=True,
        choices=["dev", "staging", "prod", "common"],
        help="Target environment for secrets",
    )
    parser.add_argument("--secrets-file", help="JSON file containing secrets to migrate")
    parser.add_argument("--backup-dir", default="./backups", help="Directory for secret backups")
    parser.add_argument("--namespace", help="Vault namespace (Enterprise feature)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating",
    )

    args = parser.parse_args()

    # Get Vault token
    vault_token = args.vault_token or os.getenv("VAULT_TOKEN")
    if not vault_token:
        vault_token = getpass.getpass("Enter Vault token: ")

    # Create backup directory
    os.makedirs(args.backup_dir, exist_ok=True)
    backup_file = os.path.join(
        args.backup_dir,
        f"secrets-backup-{args.environment}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
    )

    # Initialize migrator
    try:
        migrator = SecretMigrator(
            vault_addr=args.vault_addr, vault_token=vault_token, namespace=args.namespace
        )
    except Exception as e:
        logger.error(f"Failed to initialize migrator: {e}")
        return 1

    # Create backup
    if not args.dry_run:
        migrator.backup_secrets(args.environment, backup_file)

    # Define secrets to migrate
    secrets_to_migrate = {}

    if args.secrets_file:
        # Load from file
        with open(args.secrets_file, "r") as f:
            secrets_to_migrate = json.load(f)
    else:
        # Interactive mode
        logger.info(f"\n=== Interactive Secret Migration for {args.environment} ===\n")

        default_secrets = [
            ("api_key", "API key for authentication"),
            ("database_url", "Database connection URL"),
            ("mlflow_tracking_uri", "MLflow tracking server URI"),
            ("slack_webhook_url", "Slack webhook for notifications"),
        ]

        for key, description in default_secrets:
            logger.info(f"\n{description}")
            value = get_secret_interactive(key)
            if value:
                secrets_to_migrate[key] = value

    # Initialize progress tracker
    progress_tracker = ProgressTracker(len(secrets_to_migrate)) if not args.dry_run else None

    # Perform migration
    logger.info(f"\n=== Migrating {len(secrets_to_migrate)} secrets to {args.environment} ===\n")

    success_count = 0
    failed_secrets = []
    skipped_secrets = []

    for key, value in secrets_to_migrate.items():
        if args.dry_run:
            logger.info(f"[DRY RUN] Would migrate: {key}")
            success_count += 1
            if progress_tracker:
                progress_tracker.update(key)
        else:
            # Validate before migration
            is_valid, validation_msg = migrator.validate_secret_before_migration(key, value)

            if not is_valid:
                logger.error(f"✗ Skipping {key} due to validation failure: {validation_msg}")
                skipped_secrets.append(key)
                continue

            if migrator.migrate_secret(args.environment, key, value, progress_tracker=progress_tracker):
                # Verify migration
                if migrator.verify_secret(args.environment, key):
                    success_count += 1
                    logger.info(f"✓ Successfully migrated and verified: {key}")
                else:
                    failed_secrets.append(key)
                    logger.error(f"✗ Verification failed for {key}")
            else:
                failed_secrets.append(key)

    # Finish progress tracking
    if progress_tracker:
        progress_tracker.finish()

    # Summary
    logger.info(f"\n=== Migration Summary ===")
    logger.info(f"Total secrets: {len(secrets_to_migrate)}")
    logger.info(f"Successfully migrated: {success_count}")
    logger.info(f"Failed: {len(failed_secrets)}")
    logger.info(f"Skipped (validation failed): {len(skipped_secrets)}")

    if failed_secrets:
        logger.error(f"Failed secrets: {', '.join(failed_secrets)}")

    if skipped_secrets:
        logger.warning(f"Skipped secrets: {', '.join(skipped_secrets)}")

    if not args.dry_run:
        logger.info(f"\n✓ Migration complete!")
        logger.info(f"Backup saved to: {backup_file}")

    # Return appropriate exit code
    if failed_secrets or skipped_secrets:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
