# GitOps Deployment with ArgoCD

This document describes the GitOps-based deployment architecture for KubeSentiment using ArgoCD.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment Workflow](#deployment-workflow)
- [Operations](#operations)
- [Rollback](#rollback)
- [Troubleshooting](#troubleshooting)
- [Migration from Direct Helm](#migration-from-direct-helm)

## Overview

KubeSentiment uses **GitOps** principles for deployments, with ArgoCD as the continuous delivery tool. This approach provides:

- ✅ **Declarative deployments** - All configuration in Git
- ✅ **Automated synchronization** - ArgoCD automatically applies changes
- ✅ **Audit trail** - Full deployment history in Git commits
- ✅ **Easy rollbacks** - Revert Git commits to rollback deployments
- ✅ **Separation of concerns** - CI builds images, CD deploys them
- ✅ **Multi-environment support** - Separate configurations for dev/staging/prod

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Developer                               │
│                             │                                   │
│                             ▼                                   │
│                     Push code to Git                            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CI Pipeline                                │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │ Build & Test │→ │ Build Image  │→ │ Update GitOps Repo  │  │
│  └──────────────┘  └──────────────┘  └─────────────────────┘  │
│                                                │                │
└────────────────────────────────────────────────┼────────────────┘
                                                 │
                                                 ▼
                                        Git Repository
                                   (infrastructure/gitops/)
                                                 │
                                                 │ Monitors
                                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ArgoCD                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │ Detect Changes │→ │  Sync to K8s   │→ │  Health Check   │  │
│  └────────────────┘  └────────────────┘  └─────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
                    Kubernetes Cluster
              (dev / staging / production)
```

## Installation

### Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3.x
- Git repository access

### Quick Start

1. **Install ArgoCD:**

```bash
cd infrastructure/gitops/argocd
chmod +x bootstrap.sh
./bootstrap.sh install
```

2. **Access ArgoCD UI:**

```bash
# Port forward to access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get initial password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Access at https://localhost:8080
# Username: admin
# Password: (from above)
```

3. **Install ArgoCD CLI (optional but recommended):**

```bash
# Linux
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 555 argocd /usr/local/bin/argocd

# macOS
brew install argocd

# Windows (using Chocolatey)
choco install argocd-cli
```

4. **Login to ArgoCD:**

```bash
argocd login localhost:8080
# Use admin username and password from step 2
```

5. **Change admin password:**

```bash
argocd account update-password
```

## Configuration

### Repository Setup

Update the following files with your repository and registry URLs:

1. **ArgoCD Configuration** (`infrastructure/gitops/argocd/argocd-config.yaml`):

   - Update `repositories.url` with your Git repository URL
   - Add GitHub/GitLab credentials if private repo

2. **Application Manifests**:

   - `infrastructure/gitops/applications/*/mlops-sentiment.yaml`
   - Update `spec.source.repoURL` with your Git repository URL
   - Update `spec.source.helm.parameters[].value` for `image.repository`

3. **Environment Values**:
   - `infrastructure/gitops/environments/*/values.yaml`
   - Update `image.repository` with your container registry

### GitHub Credentials (Private Repo)

```bash
# Create secret for GitHub access
kubectl create secret generic github-credentials \
  -n argocd \
  --from-literal=username=YOUR_GITHUB_USERNAME \
  --from-literal=password=YOUR_GITHUB_PAT

# Apply ArgoCD configuration
kubectl apply -f infrastructure/gitops/argocd/argocd-config.yaml
```

### Bootstrap Applications

```bash
# Create ArgoCD Project
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: kubesentiment
  namespace: argocd
spec:
  description: KubeSentiment MLOps Project
  sourceRepos: ['*']
  destinations:
  - namespace: mlops-sentiment-dev
    server: https://kubernetes.default.svc
  - namespace: mlops-sentiment-staging
    server: https://kubernetes.default.svc
  - namespace: mlops-sentiment
    server: https://kubernetes.default.svc
  clusterResourceWhitelist:
  - group: ''
    kind: Namespace
  namespaceResourceWhitelist:
  - group: '*'
    kind: '*'
EOF

# Deploy applications
kubectl apply -f infrastructure/gitops/applications/development/
kubectl apply -f infrastructure/gitops/applications/staging/
kubectl apply -f infrastructure/gitops/applications/production/
```

## Deployment Workflow

### 1. CI/CD Pipeline Flow

#### GitHub Actions

```yaml
# Build → Push → Update GitOps
1. Build Docker image
2. Push to registry with tag
3. Update infrastructure/gitops/environments/{env}/values.yaml
4. Commit and push to Git
5. ArgoCD detects change and syncs
```

#### GitLab CI

```yaml
# Build → Push → Update GitOps
1. Build Docker image
2. Push to registry with tag
3. Update infrastructure/gitops/environments/{env}/values.yaml
4. Commit and push to Git
5. ArgoCD detects change and syncs
```

### 2. Environment-Specific Behavior

| Environment | Branch    | Auto-Sync | Manual Approval |
| ----------- | --------- | --------- | --------------- |
| Development | `develop` | ✅ Yes    | ❌ No           |
| Staging     | `main`    | ✅ Yes    | ❌ No           |
| Production  | `tags`    | ❌ No     | ✅ Yes          |

### 3. Deployment Process

**Development/Staging (Automatic):**

```bash
# 1. Developer pushes code
git push origin develop

# 2. CI builds and updates GitOps repo
# 3. ArgoCD automatically syncs (no action needed)
# 4. Check deployment status
argocd app get mlops-sentiment-development
```

**Production (Manual):**

```bash
# 1. Tag release
git tag v1.2.3
git push origin v1.2.3

# 2. CI builds and updates GitOps repo
# 3. Manually sync in ArgoCD UI or CLI
argocd app sync mlops-sentiment-production

# 4. Monitor sync progress
argocd app wait mlops-sentiment-production
```

## Operations

### Check Application Status

```bash
# List all applications
argocd app list

# Get detailed status
argocd app get mlops-sentiment-production

# View application in UI
argocd app open mlops-sentiment-production
```

### Manual Sync

```bash
# Sync specific application
argocd app sync mlops-sentiment-staging

# Sync and wait for completion
argocd app sync mlops-sentiment-staging --wait

# Force sync (override sync windows)
argocd app sync mlops-sentiment-staging --force
```

### View Logs

```bash
# View sync logs
argocd app logs mlops-sentiment-production

# View application pod logs
kubectl logs -n mlops-sentiment -l app.kubernetes.io/name=mlops-sentiment -f
```

### Diff Changes

```bash
# See what will change before syncing
argocd app diff mlops-sentiment-production
```

### Health Checks

```bash
# Check application health
argocd app get mlops-sentiment-production --show-operation

# Check resources
kubectl get all -n mlops-sentiment
```

## Rollback

### Git-Based Rollback

```bash
# 1. Find the commit to rollback to
git log infrastructure/gitops/environments/production/values.yaml

# 2. Revert to previous version
git revert <commit-hash>
git push origin main

# 3. ArgoCD will automatically sync the rollback
argocd app sync mlops-sentiment-production
```

### Manual Rollback

```bash
# Rollback to specific version in ArgoCD
argocd app rollback mlops-sentiment-production <history-id>

# Or use Helm directly (emergency only)
helm rollback mlops-sentiment -n mlops-sentiment
```

### Rollback Process

1. **Identify the issue:**

   ```bash
   kubectl get events -n mlops-sentiment --sort-by='.lastTimestamp'
   kubectl logs -n mlops-sentiment -l app.kubernetes.io/name=mlops-sentiment
   ```

2. **Check deployment history:**

   ```bash
   argocd app history mlops-sentiment-production
   ```

3. **Rollback:**

   ```bash
   # Git revert (recommended)
   git revert HEAD
   git push

   # Or ArgoCD rollback
   argocd app rollback mlops-sentiment-production <revision-id>
   ```

4. **Verify:**
   ```bash
   argocd app wait mlops-sentiment-production --health
   kubectl get pods -n mlops-sentiment
   ```

## Troubleshooting

### Application Not Syncing

```bash
# Check sync status
argocd app get mlops-sentiment-production

# Check for errors
argocd app logs mlops-sentiment-production

# Manual refresh
argocd app get mlops-sentiment-production --refresh
```

### Out of Sync

```bash
# Check differences
argocd app diff mlops-sentiment-production

# Hard refresh
argocd app get mlops-sentiment-production --hard-refresh

# Sync with pruning
argocd app sync mlops-sentiment-production --prune
```

### Health Check Failed

```bash
# View application resources
kubectl get all -n mlops-sentiment

# Check pod status
kubectl describe pod -n mlops-sentiment <pod-name>

# View logs
kubectl logs -n mlops-sentiment <pod-name>
```

### Repository Connection Issues

```bash
# Check repository credentials
argocd repo list

# Update repository credentials
kubectl edit secret -n argocd <repo-secret>

# Test connection
argocd repo get https://github.com/arec1b0/KubeSentiment.git
```

### ArgoCD Not Detecting Changes

```bash
# Force refresh
argocd app get mlops-sentiment-production --refresh

# Check repository webhook (if configured)
argocd app list --repo https://github.com/arec1b0/KubeSentiment.git

# Check ArgoCD controller logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
```

## Migration from Direct Helm

If migrating from direct `helm upgrade` deployments:

### 1. Current State Backup

```bash
# Export current Helm values
helm get values mlops-sentiment -n mlops-sentiment > current-values.yaml

# Export current release info
helm list -n mlops-sentiment
```

### 2. Adopt Existing Resources

```bash
# Option 1: Delete and recreate (development only)
helm uninstall mlops-sentiment -n mlops-sentiment
kubectl apply -f infrastructure/gitops/applications/development/

# Option 2: Adopt existing resources (recommended for production)
# Add annotations to existing resources
kubectl annotate deployment mlops-sentiment \
  -n mlops-sentiment \
  argocd.argoproj.io/tracking-id="mlops-sentiment-production:apps/Deployment:mlops-sentiment/mlops-sentiment"

# Then create ArgoCD application
kubectl apply -f infrastructure/gitops/applications/production/
```

### 3. Verify GitOps

```bash
# Check if ArgoCD manages resources
argocd app get mlops-sentiment-production

# Verify sync status
argocd app sync mlops-sentiment-production --dry-run
```

### 4. Deprecate Old Deployment Scripts

The following are now deprecated:

- `scripts/infra/deploy-helm.sh` (kept for reference)
- `.github/workflows/deploy.yml` (converted to emergency-only)
- GitLab CI `deploy:*` jobs (converted to `gitops:*` jobs)

Use only for emergency manual deployments.

## Best Practices

1. **Never modify cluster directly** - All changes via Git
2. **Use feature branches** - Test changes in development first
3. **Tag production releases** - Use semantic versioning (v1.2.3)
4. **Monitor sync status** - Set up alerts for sync failures
5. **Review diffs before sync** - Especially for production
6. **Keep GitOps repo clean** - Use conventional commits
7. **Backup before major changes** - Export Helm values and manifests
8. **Use sync waves** - For complex multi-resource deployments
9. **Set resource quotas** - Prevent runaway deployments
10. **Enable notifications** - Slack/email for sync events

## Additional Resources

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [GitOps Principles](https://www.gitops.tech/)
- [Helm with ArgoCD](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)
- [Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)

## Support

For issues or questions:

1. Check ArgoCD logs: `kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server`
2. Check application status: `argocd app get <app-name>`
3. Review Git commit history
4. Consult team documentation
5. Open an issue in the repository

---

**Last Updated:** 2025-12-16
**Version:** 1.0.0
