# CI/CD Quick Reference Guide

## 🚀 Quick Start

### Trigger Deployments

| Action | Trigger | Deploys To |
|--------|---------|------------|
| Push to `develop` | `git push origin develop` | Development |
| Push to `main` | `git push origin main` | Staging |
| Create tag `v*` | `git tag v1.0.0 && git push origin v1.0.0` | Production |
| Pull Request | `Create PR` | Tests only (no deploy) |

---

## 📋 Pipeline Stages

### 1. Test Stage (All Branches)

```bash
# What runs:
- Code quality checks (black, isort, ruff, flake8, mypy)
- Unit tests
- Integration tests
- Coverage report
```

**Duration**: ~3-5 minutes

### 2. Build Stage (Push only)

```bash
# What runs:
- Docker image build
- Push to GitHub Container Registry
- Tag with branch/version/sha
```

**Duration**: ~2-4 minutes

### 3. Security Stage (Push only)

```bash
# What runs:
- Trivy vulnerability scan
- SARIF upload to GitHub Security
```

**Duration**: ~1-2 minutes

### 4. Deploy Stage (Environment-specific)

```bash
# What runs:
- Helm chart deployment
- Health checks
- Deployment summary
```

**Duration**: ~5-10 minutes

---

## 🔧 Common Commands

### Local Testing (Before Push)

```bash
# Run all checks locally
make lint          # Code quality checks
make test          # Run tests
make format        # Auto-format code

# Or individually
black app/ tests/
isort app/ tests/
ruff check app/ tests/
pytest tests/ -v
```

### Manual Workflow Triggers

```bash
# Using GitHub CLI
gh workflow run ci.yml --ref main

# Terraform workflow
gh workflow run terraform-apply.yml \
  -f environment=dev \
  -f action=plan
```

### Check Pipeline Status

```bash
# List workflow runs
gh run list --workflow=ci.yml

# View specific run
gh run view <run-id>

# Watch latest run
gh run watch
```

---

## 🐛 Troubleshooting

### Build Failures

```bash
# Check workflow logs
gh run view --log

# Common fixes:
1. Run `make lint` locally first
2. Ensure tests pass: `pytest tests/`
3. Check Python version (3.11)
4. Verify requirements.txt is up to date
```

### Deployment Failures

```bash
# Check pod status
kubectl get pods -n mlops-sentiment-dev

# View pod logs
kubectl logs -f deployment/mlops-sentiment -n mlops-sentiment-dev

# Check events
kubectl get events -n mlops-sentiment-dev --sort-by='.lastTimestamp'

# Describe deployment
kubectl describe deployment mlops-sentiment -n mlops-sentiment-dev
```

### Health Check Failures

```bash
# Test health endpoint locally
curl http://localhost:8000/health

# In Kubernetes
kubectl port-forward -n mlops-sentiment-dev svc/mlops-sentiment 8000:80
curl http://localhost:8000/health

# Check ingress
kubectl get ingress -n mlops-sentiment-dev
kubectl describe ingress mlops-sentiment -n mlops-sentiment-dev
```

---

## 📊 Environment Configuration

### Development

```yaml
Branch: develop
Namespace: mlops-sentiment-dev
Replicas: 1
Resources: 250m CPU / 512Mi Memory
Domain: mlops-sentiment-dev.local
Auto-deploy: Yes
```

### Staging

```yaml
Branch: main
Namespace: mlops-sentiment-staging
Replicas: 2
Resources: 500m CPU / 1Gi Memory
Domain: staging.mlops-sentiment.com
Auto-deploy: Yes
HPA: 2-10 pods
```

### Production

```yaml
Branch: main (tag required)
Namespace: mlops-sentiment
Replicas: 3
Resources: 1000m CPU / 2Gi Memory
Domain: api.mlops-sentiment.com
Auto-deploy: Tag v* only
HPA: 3-20 pods
PDB: Min 2 available
```

---

## 🔐 Required Secrets

### Repository Secrets

```bash
# Per environment (Settings > Environments > <env> > Secrets)
KUBE_CONFIG          # Base64-encoded kubeconfig

# Optional
SLACK_WEBHOOK_URL    # For notifications
TF_STATE_BUCKET      # For Terraform state
```

### Setting Secrets

```bash
# Encode kubeconfig
cat ~/.kube/config | base64 -w 0

# Set via GitHub CLI
gh secret set KUBE_CONFIG --env development
gh secret set KUBE_CONFIG --env staging
gh secret set KUBE_CONFIG --env production
```

---

## 📈 Monitoring Deployments

### GitHub Actions UI

1. Go to **Actions** tab
2. Select workflow run
3. View logs for each job
4. Check deployment summary

### Kubernetes Dashboard

```bash
# Port forward to dashboard
kubectl proxy

# Or use k9s
k9s -n mlops-sentiment-dev
```

### Check Deployed Version

```bash
# Get deployed image
kubectl get deployment mlops-sentiment -n mlops-sentiment-dev \
  -o jsonpath='{.spec.template.spec.containers[0].image}'

# Get pod labels
kubectl get pods -n mlops-sentiment-dev \
  -l app.kubernetes.io/name=mlops-sentiment \
  --show-labels
```

---

## 🔄 Rollback Procedures

### Quick Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/mlops-sentiment -n mlops-sentiment

# Rollback to specific revision
kubectl rollout undo deployment/mlops-sentiment -n mlops-sentiment --to-revision=2

# Check rollout status
kubectl rollout status deployment/mlops-sentiment -n mlops-sentiment
```

### Manual Helm Rollback

```bash
# List releases
helm list -n mlops-sentiment

# Rollback
helm rollback mlops-sentiment -n mlops-sentiment

# Rollback to specific revision
helm rollback mlops-sentiment 2 -n mlops-sentiment
```

---

## 📝 Release Process

### Patch Release (v1.0.1)

```bash
git checkout main
git pull
git tag v1.0.1
git push origin v1.0.1
# ✅ Automatically deploys to production
```

### Minor Release (v1.1.0)

```bash
git checkout main
git pull
git tag v1.1.0 -m "Release v1.1.0: New features"
git push origin v1.1.0
# ✅ Automatically deploys to production
```

### Major Release (v2.0.0)

```bash
git checkout main
git pull
git tag v2.0.0 -m "Release v2.0.0: Breaking changes"
git push origin v2.0.0
# ✅ Automatically deploys to production
# ⚠️  Requires 2 approvers (configured in GitHub)
```

---

## 🎯 Best Practices

### Before Committing

```bash
✅ Run `make lint` and fix all issues
✅ Run `make test` and ensure all pass
✅ Run `make format` to auto-fix formatting
✅ Update tests for new features
✅ Update documentation
```

### Before Tagging for Production

```bash
✅ Verify staging deployment is stable
✅ Run integration tests
✅ Check monitoring dashboards
✅ Update CHANGELOG.md
✅ Create release notes
```

### After Deployment

```bash
✅ Monitor logs for errors
✅ Check metrics in Grafana
✅ Verify health endpoints
✅ Test critical user flows
✅ Watch alerts in Slack
```

---

## 📞 Emergency Contacts

### Rollback Production

```bash
# Immediate rollback
kubectl rollout undo deployment/mlops-sentiment -n mlops-sentiment

# Notify team
# Post in #production-alerts Slack channel
```

### Scale Down (Emergency)

```bash
# Scale to minimum
kubectl scale deployment mlops-sentiment --replicas=1 -n mlops-sentiment

# Disable HPA temporarily
kubectl patch hpa mlops-sentiment -n mlops-sentiment -p '{"spec":{"maxReplicas":1}}'
```

---

## 🔗 Useful Links

- [GitHub Actions](https://github.com/<org>/<repo>/actions)
- [GitHub Container Registry](https://github.com/<org>/<repo>/pkgs/container/kubesentiment)
- [GitHub Security](https://github.com/<org>/<repo>/security)
- [Full CI/CD Documentation](./CICD_README.md)
- [CI/CD Fixes Summary](./CICD_FIXES.md)

---

## 📚 Related Documentation

- [Development Guide](./setup/DEVELOPMENT.md)
- [Deployment Guide](./setup/deployment-guide.md)
- [Kubernetes Documentation](./KUBERNETES.md)
- [Monitoring Guide](./MONITORING.md)
- [Troubleshooting](./troubleshooting/index.md)

---

**Last Updated**: October 2025
**Version**: 2.0
**Maintained by**: MLOps Team
