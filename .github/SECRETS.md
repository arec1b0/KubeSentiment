# Secrets Management Guide

This document describes the secrets management architecture using HashiCorp Vault
and GitHub Secrets for CI/CD pipelines.

## Architecture Overview

The project uses a hybrid approach for secrets management:

- **HashiCorp Vault**: Primary secrets storage for runtime application secrets
- **GitHub Secrets**: Bootstrap credentials for CI/CD (Vault address, initial tokens)
- **Environment Variables**: Local development fallback

This provides:
- Centralized secret management
- Automated secret rotation
- Audit logging
- Zero-downtime secret updates
- Environment isolation

## Vault Security Practices

### 1. Secret Lifecycle Management

#### Secret Rotation Strategy

**Automated Rotation:**
- API keys: Every 90 days
- Database credentials: Every 30 days
- TLS certificates: Every 90 days
- Service tokens: Every 7 days

**Manual Rotation Triggers:**
- Security incidents
- Employee departures
- Policy changes
- Compliance requirements

#### Rotation Procedures

```bash
# Rotate a specific secret
python scripts/rotate-secrets.py --secret api_key --environment prod

# Bulk rotation for environment
python scripts/rotate-secrets.py --environment prod --all

# Emergency rotation (immediate effect)
python scripts/rotate-secrets.py --secret api_key --environment prod --emergency
```

### 2. Access Control Policies

#### Principle of Least Privilege

```hcl
# Development environment policy
path "mlops-sentiment/data/dev/*" {
  capabilities = ["read", "list"]
}

# Production environment policy (read-only)
path "mlops-sentiment/data/prod/*" {
  capabilities = ["read", "list"]
}

# Admin policy (for CI/CD and rotation)
path "mlops-sentiment/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
```

#### Environment Isolation

- **Development**: Broad access for testing
- **Staging**: Read-only for most services
- **Production**: Minimal access, audit all operations

#### User and Service Accounts

```bash
# Create service-specific policies
vault policy write mlops-api-dev - <<EOF
path "mlops-sentiment/data/dev/*" {
  capabilities = ["read", "list"]
}
EOF

# Create time-limited tokens
vault token create -policy=mlops-api-dev -ttl=1h
```

### 3. Audit and Monitoring

#### Audit Logging Configuration

```bash
# Enable comprehensive audit logging
vault audit enable file file_path=/vault/logs/audit.log

# Enable syslog for centralized logging
vault audit enable syslog tag="vault-mlops" facility="AUTH"
```

#### Security Events to Monitor

- Authentication failures
- Policy violations
- Secret access patterns
- Unusual access times/locations
- Mass secret retrievals

#### Alerting Rules

```yaml
# Prometheus alerting rules for Vault
groups:
  - name: vault-security
    rules:
      - alert: VaultAuthenticationFailures
        expr: increase(vault_authentication_failures_total[5m]) > 5
        labels:
          severity: critical
        annotations:
          summary: "High number of Vault authentication failures"

      - alert: UnusualSecretAccess
        expr: increase(vault_secret_access_total{status="success"}[1h]) > 1000
        labels:
          severity: warning
        annotations:
          summary: "Unusual spike in secret access"
```

### 4. Compliance and Governance

#### Secret Classification

```yaml
# Secret classification schema
classifications:
  public:
    retention: "90 days"
    access: "read-only"
    audit: "minimal"

  internal:
    retention: "1 year"
    access: "role-based"
    audit: "standard"

  restricted:
    retention: "7 years"
    access: "dual-approval"
    audit: "comprehensive"

  confidential:
    retention: "permanent"
    access: "break-glass"
    audit: "maximum"
```

#### Compliance Checks

```bash
# Automated compliance scanning
python scripts/compliance-check.py --environment prod

# Check for secrets older than policy
vault kv metadata get -format=json mlops-sentiment/prod/ | \
  jq '.data.created_time' | \
  python -c "import sys, json; data=json.load(sys.stdin); print('Compliance check passed')" if data is valid else exit(1)
```

### 5. Emergency Procedures

#### Break-Glass Access

```bash
# Emergency token creation (requires special approval)
vault token create \
  -policy=mlops-emergency-admin \
  -ttl=15m \
  -explicit_max_ttl=1h \
  -orphan

# Document emergency access
echo "$(date): Emergency access granted to $(whoami) for incident #12345" >> /vault/emergency-access.log
```

#### Security Incident Response

1. **Immediate Actions:**
   - Isolate affected systems
   - Revoke compromised tokens
   - Rotate all secrets in affected environments

2. **Investigation:**
   - Review audit logs
   - Identify scope of breach
   - Trace access patterns

3. **Recovery:**
   - Restore from clean backups
   - Re-key encryption if necessary
   - Update security policies

#### Communication Plan

```yaml
incident_response:
  levels:
    low:
      notification: "team-lead"
      timeline: "24 hours"
    medium:
      notification: "security-team"
      timeline: "4 hours"
    high:
      notification: "executive-team"
      timeline: "1 hour"
    critical:
      notification: "all-stakeholders"
      timeline: "immediate"
```

## 🔐 Repository Secrets

### Required Bootstrap Secrets

These secrets are stored in GitHub Secrets and used to bootstrap Vault access:

#### Vault Configuration

```
VAULT_ADDR          # Vault server address (e.g., https://vault.example.com:8200)
VAULT_TOKEN         # Initial Vault token for GitHub Actions (rotate regularly)
VAULT_NAMESPACE     # Vault namespace if using Enterprise (optional)
```

**How to obtain:**

```bash
# After deploying Vault, get the address
kubectl get svc vault -n vault-system

# Create a token with appropriate policies
vault token create -policy=github-actions-rotation -ttl=30d
```

#### Kubernetes Configuration (Optional - can be stored in Vault)

```
KUBE_CONFIG_DEV      # Base64-encoded kubeconfig for development (optional)
KUBE_CONFIG_STAGING  # Base64-encoded kubeconfig for staging (optional)
KUBE_CONFIG_PROD     # Base64-encoded kubeconfig for production (optional)
```

**Recommended:** Store kubeconfigs in Vault instead of GitHub Secrets

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

## 🔄 Secret Rotation with Vault

### Automated Rotation

The project includes automated secret rotation via GitHub Actions workflow:

```bash
# Trigger manual rotation
gh workflow run vault-secret-rotation.yml \
  -f environment=prod \
  -f secret_name=api_key

# Scheduled rotation runs weekly (Sundays at midnight UTC)
```

### Manual Rotation

Use the rotation script for manual secret rotation:

```bash
# Rotate a specific secret
python scripts/rotate-secrets.py \
  --vault-addr https://vault.example.com:8200 \
  --environment prod \
  --secret api_key \
  --k8s-namespace mlops-prod \
  --k8s-deployment mlops-sentiment

# Dry run to preview changes
python scripts/rotate-secrets.py \
  --vault-addr https://vault.example.com:8200 \
  --environment staging \
  --secret database_password \
  --dry-run
```

### Rotation Schedule

Recommended rotation intervals:

1. **API keys**: Every 90 days (automated)
2. **Database passwords**: Every 90 days (automated)
3. **Kubernetes configs**: When clusters are updated (manual)
4. **Vault tokens**: Every 30 days (automated)
5. **Cosign keys**: Every 365 days (manual)

## 🗂️ Vault Secret Organization

Secrets in Vault are organized by environment:

```
mlops-sentiment/data/
├── common/              # Shared across all environments
│   ├── mlflow_uri
│   └── slack_webhook
├── dev/                 # Development secrets
│   ├── api_key
│   ├── database_url
│   └── kubernetes/kubeconfig
├── staging/             # Staging secrets
│   ├── api_key
│   ├── database_url
│   └── kubernetes/kubeconfig
└── prod/                # Production secrets
    ├── api_key
    ├── database_url
    └── kubernetes/kubeconfig
```

## 🔧 Local Development with Vault

For local development, you can either:

### Option 1: Use Environment Variables (Recommended for Local Dev)

```bash
# Create .env file
cat > .env << EOF
MLOPS_VAULT_ENABLED=false
MLOPS_API_KEY=local-dev-key
MLOPS_DEBUG=true
EOF
```

### Option 2: Use Local Vault Instance

```bash
# Start Vault in dev mode
docker run -d --name vault -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=dev-token' \
  hashicorp/vault:1.15.0

# Configure application
export MLOPS_VAULT_ENABLED=true
export MLOPS_VAULT_ADDR=http://localhost:8200
export MLOPS_VAULT_TOKEN=dev-token

# Add secrets
vault kv put mlops-sentiment/mlops-sentiment/dev/api_key value="dev-api-key"
```

## 🔍 Troubleshooting

### Vault Connection Issues

```bash
# Check Vault health
curl -k $VAULT_ADDR/v1/sys/health

# Verify authentication
vault token lookup

# Check policy permissions
vault token capabilities mlops-sentiment/data/prod/api_key
```

### Secret Access Issues

```bash
# List available secrets
vault kv list mlops-sentiment/mlops-sentiment/prod

# Read a specific secret
vault kv get mlops-sentiment/mlops-sentiment/prod/api_key

# Check secret metadata and versions
vault kv metadata get mlops-sentiment/mlops-sentiment/prod/api_key
```

### Kubernetes Authentication Issues

```bash
# Verify service account exists
kubectl get sa mlops-sentiment-vault -n mlops-prod

# Check Vault role binding
vault read auth/kubernetes/role/mlops-sentiment-prod

# Test authentication from pod
kubectl exec -it <pod-name> -n mlops-prod -- \
  cat /var/run/secrets/kubernetes.io/serviceaccount/token
```

## 📚 Additional Resources

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Vault Kubernetes Auth Method](https://www.vaultproject.io/docs/auth/kubernetes)
- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Environment Protection Rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Vault Best Practices](https://www.vaultproject.io/docs/internals/security)
