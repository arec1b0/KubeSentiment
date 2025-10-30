# HashiCorp Vault Setup Guide

Complete guide for setting up and integrating HashiCorp Vault with the MLOps Sentiment Analysis application.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Vault Installation](#vault-installation)
3. [Vault Configuration](#vault-configuration)
4. [Application Integration](#application-integration)
5. [Secret Migration](#secret-migration)
6. [Testing](#testing)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Configuration](#advanced-configuration)

## Prerequisites

- Kubernetes cluster (1.20+)
- Helm 3.x
- kubectl configured
- Python 3.11+
- Terraform (optional, for infrastructure as code)

## Vault Installation

### Option 1: Using Helm (Recommended)

```bash
# Add HashiCorp Helm repository
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

# Create namespace
kubectl create namespace vault-system

# Install Vault with HA configuration
helm install vault hashicorp/vault \
  --namespace vault-system \
  --set='server.ha.enabled=true' \
  --set='server.ha.replicas=3' \
  --set='ui.enabled=true' \
  --set='ui.serviceType=LoadBalancer'

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=vault \
  -n vault-system --timeout=5m
```

### Option 2: Using Terraform

```bash
cd infrastructure/
terraform init
terraform plan -target=module.vault
terraform apply -target=module.vault
```

## Vault Initialization

### Initialize and Unseal Vault

```bash
# Initialize Vault (run once)
kubectl exec vault-0 -n vault-system -- vault operator init \
  -key-shares=5 \
  -key-threshold=3 \
  -format=json > vault-keys.json

# IMPORTANT: Store vault-keys.json securely (e.g., in a password manager)
# Never commit this file to version control!

# Extract unseal keys and root token
UNSEAL_KEY_1=$(cat vault-keys.json | jq -r '.unseal_keys_b64[0]')
UNSEAL_KEY_2=$(cat vault-keys.json | jq -r '.unseal_keys_b64[1]')
UNSEAL_KEY_3=$(cat vault-keys.json | jq -r '.unseal_keys_b64[2]')
ROOT_TOKEN=$(cat vault-keys.json | jq -r '.root_token')

# Unseal Vault (requires 3 of 5 keys)
kubectl exec vault-0 -n vault-system -- vault operator unseal $UNSEAL_KEY_1
kubectl exec vault-0 -n vault-system -- vault operator unseal $UNSEAL_KEY_2
kubectl exec vault-0 -n vault-system -- vault operator unseal $UNSEAL_KEY_3

# Repeat for other Vault pods (vault-1, vault-2) in HA setup
```

### Configure Vault CLI

```bash
# Get Vault address
export VAULT_ADDR=$(kubectl get svc vault -n vault-system \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):8200

# Or if using hostname
export VAULT_ADDR=$(kubectl get svc vault -n vault-system \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'):8200

# Login with root token
export VAULT_TOKEN=$ROOT_TOKEN
vault login $ROOT_TOKEN

# Verify Vault is operational
vault status
```

## Vault Configuration

### 1. Apply Terraform Configuration

```bash
cd infrastructure/modules/vault-integration

# Configure variables
cat > terraform.tfvars << EOF
kubernetes_host = "https://kubernetes.default.svc"
kubernetes_ca_cert = "$(kubectl get secret -n default \
  $(kubectl get sa default -n default -o jsonpath='{.secrets[0].name}') \
  -o jsonpath='{.data.ca\.crt}')"
kubernetes_token_reviewer_jwt = "$(kubectl get secret -n default \
  $(kubectl get sa default -n default -o jsonpath='{.secrets[0].name}') \
  -o jsonpath='{.data.token}' | base64 -d)"
github_org = "arec1b0"
github_repository = "arec1b0/KubeSentiment"
EOF

# Apply Terraform configuration
terraform init
terraform plan
terraform apply
```

### 2. Manual Configuration (Alternative)

```bash
# Enable KV v2 secrets engine
vault secrets enable -path=mlops-sentiment kv-v2

# Enable Kubernetes authentication
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
  token_reviewer_jwt=@/var/run/secrets/kubernetes.io/serviceaccount/token

# Create policies for each environment
vault policy write mlops-sentiment-dev - << EOF
path "mlops-sentiment/data/mlops-sentiment/dev/*" {
  capabilities = ["read", "list"]
}
path "mlops-sentiment/data/mlops-sentiment/common/*" {
  capabilities = ["read", "list"]
}
EOF

vault policy write mlops-sentiment-staging - << EOF
path "mlops-sentiment/data/mlops-sentiment/staging/*" {
  capabilities = ["read", "list"]
}
path "mlops-sentiment/data/mlops-sentiment/common/*" {
  capabilities = ["read", "list"]
}
EOF

vault policy write mlops-sentiment-prod - << EOF
path "mlops-sentiment/data/mlops-sentiment/prod/*" {
  capabilities = ["read", "list"]
}
path "mlops-sentiment/data/mlops-sentiment/common/*" {
  capabilities = ["read", "list"]
}
EOF

# Create Kubernetes auth roles
vault write auth/kubernetes/role/mlops-sentiment-dev \
  bound_service_account_names=mlops-sentiment-vault \
  bound_service_account_namespaces=mlops-dev \
  policies=mlops-sentiment-dev \
  ttl=1h

vault write auth/kubernetes/role/mlops-sentiment-staging \
  bound_service_account_names=mlops-sentiment-vault \
  bound_service_account_namespaces=mlops-staging \
  policies=mlops-sentiment-staging \
  ttl=1h

vault write auth/kubernetes/role/mlops-sentiment-prod \
  bound_service_account_names=mlops-sentiment-vault \
  bound_service_account_namespaces=mlops-prod \
  policies=mlops-sentiment-prod \
  ttl=1h
```

### 3. Enable GitHub Actions Authentication

```bash
# Enable JWT auth for GitHub Actions
vault auth enable -path=jwt-github jwt

vault write auth/jwt-github/config \
  bound_issuer="https://token.actions.githubusercontent.com" \
  oidc_discovery_url="https://token.actions.githubusercontent.com"

# Create role for GitHub Actions
vault write auth/jwt-github/role/github-actions \
  role_type="jwt" \
  bound_audiences="https://github.com/arec1b0" \
  bound_claims=repository="arec1b0/KubeSentiment" \
  user_claim="actor" \
  policies="mlops-sentiment-admin" \
  ttl=1h
```

## Application Integration

### 1. Deploy with Helm

```bash
# Update values for Vault integration
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-prod \
  --create-namespace \
  --set vault.enabled=true \
  --set vault.address="http://vault.vault-system:8200" \
  --set vault.role="mlops-sentiment-prod" \
  --set vault.namespace="mlops"
```

### 2. Configure Application Environment Variables

For Kubernetes deployments, set these in your deployment manifest or Helm values:

```yaml
env:
  - name: MLOPS_VAULT_ENABLED
    value: "true"
  - name: MLOPS_VAULT_ADDR
    value: "http://vault.vault-system:8200"
  - name: MLOPS_VAULT_ROLE
    value: "mlops-sentiment-prod"
  - name: MLOPS_VAULT_NAMESPACE
    value: "mlops"
```

### 3. Verify Integration

```bash
# Check pod logs
kubectl logs -l app=mlops-sentiment -n mlops-prod --tail=100

# Should see: "Initialized Vault secret manager"
```

## Secret Migration

### Migrate Secrets from GitHub to Vault

```bash
# Install dependencies
pip install hvac

# Run migration script
python scripts/migrate-secrets-to-vault.py \
  --vault-addr $VAULT_ADDR \
  --vault-token $VAULT_TOKEN \
  --environment prod \
  --backup-dir ./backups

# Follow interactive prompts to enter secrets
```

### Migrate Secrets from JSON File

```bash
# Create secrets file
cat > secrets-prod.json << EOF
{
  "api_key": "your-production-api-key",
  "database_url": "postgresql://user:pass@host:5432/db",
  "mlflow_tracking_uri": "http://mlflow:5000",
  "slack_webhook_url": "https://hooks.slack.com/services/XXX"
}
EOF

# Run migration
python scripts/migrate-secrets-to-vault.py \
  --vault-addr $VAULT_ADDR \
  --vault-token $VAULT_TOKEN \
  --environment prod \
  --secrets-file secrets-prod.json

# Remove secrets file securely
shred -u secrets-prod.json
```

## Testing

### Test Vault Connection

```bash
# Test from local machine
export MLOPS_VAULT_ENABLED=true
export MLOPS_VAULT_ADDR=$VAULT_ADDR
export MLOPS_VAULT_TOKEN=$VAULT_TOKEN

python -c "
from app.core.config import get_settings
settings = get_settings()
print('Vault enabled:', settings.vault_enabled)
print('Secret manager healthy:', settings.secret_manager.is_healthy())
"
```

### Test Secret Retrieval

```bash
# Test API key retrieval
vault kv get mlops-sentiment/mlops-sentiment/prod/api_key

# Test from application
python -c "
from app.core.config import get_settings
settings = get_settings()
api_key = settings.get_secret('api_key')
print('API key retrieved:', api_key is not None)
"
```

### Run Integration Tests

```bash
# Run Vault integration tests
pytest tests/test_vault_integration.py -v

# Run with actual Vault (optional)
pytest tests/test_vault_integration.py -v --vault-integration
```

## Production Deployment

### 1. Enable Audit Logging

```bash
vault audit enable file file_path=/vault/logs/audit.log
```

### 2. Set Up Secret Rotation

```bash
# Configure automated rotation in GitHub
gh secret set VAULT_ADDR -b "$VAULT_ADDR"
gh secret set VAULT_TOKEN -b "$ROTATION_TOKEN"

# Test rotation workflow
gh workflow run vault-secret-rotation.yml \
  -f environment=dev \
  -f secret_name=api_key \
  -f dry_run=true
```

### 3. Configure Monitoring

```bash
# Deploy Prometheus ServiceMonitor
kubectl apply -f helm/mlops-sentiment/templates/servicemonitor-vault.yaml

# Check Vault metrics
curl $VAULT_ADDR/v1/sys/metrics?format=prometheus
```

### 4. Backup Vault Data

```bash
# Create backup
vault operator raft snapshot save vault-backup-$(date +%Y%m%d).snap

# Store backup securely (e.g., S3, GCS)
aws s3 cp vault-backup-*.snap s3://your-backup-bucket/vault/
```

## Security Best Practices

1. **Token Management**
   - Use short-lived tokens (1h TTL for apps, 30d for CI/CD)
   - Rotate tokens regularly
   - Never log tokens or store in plaintext

2. **Network Security**
   - Use TLS for Vault communication in production
   - Restrict network access to Vault
   - Use Kubernetes NetworkPolicies

3. **Audit Logging**
   - Enable audit logging
   - Monitor for suspicious activity
   - Integrate with SIEM systems

4. **Backup and Recovery**
   - Regular automated backups
   - Test recovery procedures
   - Store backups encrypted

5. **Access Control**
   - Follow principle of least privilege
   - Use environment-specific policies
   - Regular policy audits

## Troubleshooting

### Common Issues and Solutions

#### 1. Vault Authentication Failures

**Problem**: `Failed to authenticate to Vault` error

**Solutions**:
```bash
# Check Vault health
vault status

# Verify token is valid
vault token lookup

# Check Kubernetes service account token
kubectl get serviceaccount mlops-sentiment-vault -o yaml
```

**Problem**: `Kubernetes service account token not found`

**Solutions**:
```bash
# Check if service account exists
kubectl get serviceaccount mlops-sentiment-vault

# Check if token is mounted
kubectl exec <pod-name> -- ls /var/run/secrets/kubernetes.io/serviceaccount/

# Verify RBAC permissions
kubectl auth can-i get secrets --as=system:serviceaccount:mlops:mlops-sentiment-vault
```

#### 2. Secret Access Issues

**Problem**: `Permission denied` when accessing secrets

**Solutions**:
```bash
# Check policy permissions
vault policy read mlops-sentiment-dev

# Verify token policies
vault token lookup

# Check if secrets exist
vault kv list mlops-sentiment/dev
```

**Problem**: `Secret not found` errors in application

**Solutions**:
```bash
# Check secret path
vault kv get mlops-sentiment/dev/api_key

# Verify environment configuration
kubectl get configmap mlops-sentiment -o yaml

# Check application logs for Vault connection errors
kubectl logs <pod-name> | grep -i vault
```

#### 3. Agent Injection Problems

**Problem**: Vault Agent sidecar not starting

**Solutions**:
```bash
# Check agent configuration
kubectl describe configmap mlops-sentiment-vault-agent-config

# Verify Vault Agent logs
kubectl logs <pod-name> -c vault-agent

# Check service account permissions
kubectl auth can-i get secrets --as=system:serviceaccount:mlops:mlops-sentiment-vault
```

#### 4. Performance Issues

**Problem**: Slow secret retrieval

**Solutions**:
```bash
# Enable caching in application
export MLOPS_VAULT_CACHE_TTL=300

# Check Vault performance
vault status -format=json

# Monitor Vault metrics
kubectl port-forward svc/vault 8200:8200
# Then visit http://localhost:8200/v1/sys/metrics
```

#### 5. Migration Issues

**Problem**: Secret migration script fails

**Solutions**:
```bash
# Test Vault connectivity first
python -c "import hvac; c = hvac.Client(url='http://vault:8200', token='your-token'); print(c.is_authenticated())"

# Run migration in dry-run mode first
python scripts/migrate-secrets-to-vault.py --dry-run --vault-addr http://vault:8200 --environment dev

# Check script logs for specific errors
python scripts/migrate-secrets-to-vault.py --vault-addr http://vault:8200 --environment dev 2>&1 | tee migration.log
```

#### 6. Health Check Failures

**Problem**: Vault health checks failing

**Solutions**:
```bash
# Check Vault cluster status
vault status

# Verify all Vault pods are running
kubectl get pods -n vault-system

# Check Vault logs
kubectl logs vault-0 -n vault-system

# Test application health endpoint
curl http://your-app:8000/health
```

## Advanced Configuration

### 1. Custom Secret Engines

#### Database Secrets Engine

```bash
# Enable database secrets engine
vault secrets enable database

# Configure PostgreSQL connection
vault write database/config/postgresql \
  plugin_name=postgresql-database-plugin \
  allowed_roles="readonly,readwrite" \
  connection_url="postgresql://{{username}}:{{password}}@db-host:5432/mlops?sslmode=require" \
  username="vault_user" \
  password="vault_password"

# Create roles
vault write database/roles/readonly \
  db_name=postgresql \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT CONNECT ON DATABASE mlops TO \"{{name}}\"; GRANT USAGE ON SCHEMA public TO \"{{name}}\"; GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}';" \
  revocation_statements="DROP ROLE IF EXISTS \"{{name}}\";"

# Use dynamic secrets in application
vault read database/creds/readonly
```

#### AWS Secrets Engine

```bash
# Enable AWS secrets engine
vault secrets enable aws

# Configure AWS credentials
vault write aws/config/root \
  access_key=AKIAIOSFODNN7EXAMPLE \
  secret_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
  region=us-east-1

# Create role for EC2 access
vault write aws/roles/ec2-admin \
  credential_type=assumed_role \
  role_arns="arn:aws:iam::123456789012:role/MyRole" \
  default_sts_ttl=3600 \
  max_sts_ttl=43200
```

### 2. Advanced Policies

#### Time-based Access Policies

```hcl
# Policy for time-limited access
path "mlops-sentiment/data/dev/*" {
  capabilities = ["read", "list"]

  # Only allow access during business hours (9 AM - 5 PM UTC)
  required_parameters = ["valid_time"]
  allowed_parameter = {
    valid_time = ["09:00-17:00"]
  }
}
```

#### IP-based Restrictions

```hcl
# Policy restricting access to specific IP ranges
path "mlops-sentiment/data/prod/*" {
  capabilities = ["read", "list"]

  # Only allow access from trusted networks
  required_parameters = ["client_ip"]
  allowed_parameter = {
    client_ip = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  }
}
```

### 3. Audit and Monitoring

#### Enhanced Audit Logging

```bash
# Enable file audit device
vault audit enable file file_path=/vault/logs/audit.log

# Enable syslog audit device
vault audit enable syslog tag="vault" facility="AUTH"
```

#### Custom Monitoring Scripts

```bash
#!/bin/bash
# Vault health monitoring script

VAULT_ADDR="http://vault:8200"
VAULT_TOKEN="your-token"

# Check Vault status
STATUS=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/sys/health" | jq -r '.sealed')

if [ "$STATUS" = "true" ]; then
  echo "CRITICAL: Vault is sealed"
  exit 2
else
  echo "OK: Vault is unsealed"
  exit 0
fi
```

### 4. Backup and Recovery

#### Automated Backup

```bash
#!/bin/bash
# Automated Vault backup script

BACKUP_DIR="/vault/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Create Raft snapshot (for HA deployments)
vault operator raft snapshot save $BACKUP_DIR/vault-backup-$TIMESTAMP.snap

# Encrypt backup
gpg --encrypt --recipient backup@company.com $BACKUP_DIR/vault-backup-$TIMESTAMP.snap

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "*.snap.gpg" -mtime +7 -delete
```

#### Recovery Procedures

```bash
# Restore from backup
vault operator raft snapshot restore vault-backup-20231201_120000.snap

# Manual unseal after restore
vault operator unseal <unseal-key-1>
vault operator unseal <unseal-key-2>
vault operator unseal <unseal-key-3>
```

## Additional Resources

- [Vault Documentation](https://www.vaultproject.io/docs)
- [Kubernetes Auth Method](https://www.vaultproject.io/docs/auth/kubernetes)
- [Best Practices](https://www.vaultproject.io/docs/internals/security)
- [Production Hardening](https://www.vaultproject.io/docs/concepts/production)
- [Security Considerations](https://www.vaultproject.io/docs/internals/security)

