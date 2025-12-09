# Scripts Directory

This directory contains utility scripts for development, testing, and operations.

## Profile Validation

- `test_profiles.py`: Tests the profile loading mechanism to ensure configuration defaults are applied correctly.
- `validate_profiles.py`: Validates that all defined profiles adhere to the schema and environment variable overrides work as expected.

## Deployment & Setup

- `setup-monitoring.sh`: Deploys the full observability stack (Prometheus, Grafana, etc.) to Kubernetes.
- `setup-kind.sh`: Sets up a local KIND (Kubernetes in Docker) cluster.
- `deploy-helm.sh`: Helper script to deploy the application via Helm.

## Maintenance

- `cleanup.sh`: Removes temporary files and build artifacts.
- `format_code.sh`: Runs linters and formatters.
- `rotate-secrets.py`: Utility for rotating secrets in Vault/Kubernetes.
