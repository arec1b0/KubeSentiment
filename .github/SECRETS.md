# GitHub Secrets Configuration Guide

This document describes all the necessary secrets and variables for the CI/CD pipeline to work.

## 🔐 Repository Secrets

### Required Secrets

#### Kubernetes Configuration

```
KUBE_CONFIG_DEV      # Base64-encoded kubeconfig for the development environment
KUBE_CONFIG_STAGING  # Base64-encoded kubeconfig for the staging environment
KUBE_CONFIG_PROD     # Base64-encoded kubeconfig for the production environment
```

**How to obtain:**

```bash
# Get the kubeconfig and encode it in base64
cat ~/.kube/config | base64 -w 0
```

#### Container Signing (optional, but recommended)

```
COSIGN_PRIVATE_KEY   # Private key for signing Docker images
COSIGN_PASSWORD      # Password for the cosign private key
```

**How to create:**

```bash
# Generate keys for cosign
cosign generate-key-pair
# Save the contents of cosign.key to COSIGN_PRIVATE_KEY
# Save the password to COSIGN_PASSWORD
```

### Integrations (optional)

#### Slack Notifications

```
SLACK_WEBHOOK_URL    # Webhook URL for Slack notifications
```

#### Jira Integration

```
JIRA_API_TOKEN       # API token for Jira integration
```

## 🌍 Repository Variables

### General Variables

```
JIRA_BASE_URL        # Jira instance URL (e.g., https://company.atlassian.net)
JIRA_USER_EMAIL      # Jira user email
JIRA_PROJECT_KEY     # Jira project key (e.g., MLOPS)
```

## 🏢 Environment Secrets

Secrets specific to each environment (configured in Settings > Environments):

### Development Environment

- `KUBE_CONFIG`: Kubeconfig for the dev cluster
- `SLACK_WEBHOOK_URL`: Webhook for dev notifications

### Staging Environment

- `KUBE_CONFIG`: Kubeconfig for the staging cluster
- `SLACK_WEBHOOK_URL`: Webhook for staging notifications

### Production Environment

- `KUBE_CONFIG`: Kubeconfig for the prod cluster
- `SLACK_WEBHOOK_URL`: Webhook for prod notifications

## 📋 Environment Setup

1. Go to `Settings > Environments`
2. Create three environments:
   - `development`
   - `staging`
   - `production`

3. For each environment, configure:
   - **Protection rules**: Require review for production
   - **Environment secrets**: Corresponding KUBE_CONFIG
   - **Deployment branches**: Branch restrictions

### Example Protection Rules Setup

#### Development

- Deployment branches: `develop`
- Required reviewers: 0

#### Staging

- Deployment branches: `main`
- Required reviewers: 1

#### Production

- Deployment branches: `main`, tags `v*`
- Required reviewers: 2
- Wait timer: 5 minutes

## 🔧 Automatic Secret Setup

Create a script for automatic setup:

```bash
#!/bin/bash
# setup-secrets.sh

# Install GitHub CLI if not installed
if ! command -v gh &> /dev/null; then
    echo "Please install GitHub CLI first"
    exit 1
fi

# Authenticate
gh auth login

# Set Kubernetes secrets
echo "Setting up Kubernetes secrets..."
gh secret set KUBE_CONFIG_DEV < ~/.kube/config-dev
gh secret set KUBE_CONFIG_STAGING < ~/.kube/config-staging
gh secret set KUBE_CONFIG_PROD < ~/.kube/config-prod

# Set Slack webhook (replace with your URL)
read -p "Enter Slack Webhook URL: " SLACK_URL
gh secret set SLACK_WEBHOOK_URL -b "$SLACK_URL"

# Generate cosign keys
echo "Generating cosign keys..."
cosign generate-key-pair
gh secret set COSIGN_PRIVATE_KEY < cosign.key
read -s -p "Enter cosign key password: " COSIGN_PASS
gh secret set COSIGN_PASSWORD -b "$COSIGN_PASS"

# Clean up temporary files
rm -f cosign.key cosign.pub

echo "✅ Secrets setup completed!"
```

## 🔍 Configuration Check

Use this workflow to check the settings:

```yaml
name: Verify Secrets
on:
  workflow_dispatch:

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
    - name: Check required secrets
      run: |
        secrets_ok=true
        
        # Check for the presence of required secrets
        if [ -z "${{ secrets.KUBE_CONFIG_DEV }}" ]; then
          echo "❌ KUBE_CONFIG_DEV is missing"
          secrets_ok=false
        fi
        
        if [ -z "${{ secrets.KUBE_CONFIG_STAGING }}" ]; then
          echo "❌ KUBE_CONFIG_STAGING is missing"
          secrets_ok=false
        fi
        
        if [ -z "${{ secrets.KUBE_CONFIG_PROD }}" ]; then
          echo "❌ KUBE_CONFIG_PROD is missing"
          secrets_ok=false
        fi
        
        if [ "$secrets_ok" = true ]; then
          echo "✅ All required secrets are configured"
        else
          echo "❌ Some secrets are missing"
          exit 1
        fi
```

## 🔄 Secret Rotation

Regularly update secrets:

1. **Kubernetes configs**: When clusters are updated
2. **API tokens**: Every 90 days
3. **Cosign keys**: Every 365 days

## 📚 Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Environment Protection Rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Cosign Documentation](https://docs.sigstore.dev/cosign/overview/)
