# GitOps Migration Guide

Quick reference for migrating from direct Helm deployments to GitOps with ArgoCD.

## Pre-Migration Checklist

- [ ] ArgoCD installed and accessible
- [ ] Git repository updated with GitOps structure
- [ ] CI/CD pipelines updated to push to GitOps repo
- [ ] Team trained on GitOps workflows
- [ ] Rollback plan documented

## Migration Steps

### 1. Install ArgoCD

```bash
cd infrastructure/gitops/argocd
./bootstrap.sh install
```

### 2. Configure Repository Access

```bash
# For private repos
kubectl create secret generic github-credentials \
  -n argocd \
  --from-literal=username=<username> \
  --from-literal=password=<token>

kubectl apply -f infrastructure/gitops/argocd/argocd-config.yaml
```

### 3. Create ArgoCD Project

```bash
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
  - namespace: '*'
    server: https://kubernetes.default.svc
  clusterResourceWhitelist:
  - group: '*'
    kind: '*'
EOF
```

### 4. Migrate Development Environment

```bash
# 1. Export current state
helm get values mlops-sentiment -n mlops-sentiment-dev > backup-dev-values.yaml

# 2. Uninstall Helm release
helm uninstall mlops-sentiment -n mlops-sentiment-dev

# 3. Deploy via ArgoCD
kubectl apply -f infrastructure/gitops/applications/development/

# 4. Verify
argocd app sync mlops-sentiment-development
argocd app wait mlops-sentiment-development --health
```

### 5. Migrate Staging Environment

```bash
# 1. Backup
helm get values mlops-sentiment -n mlops-sentiment-staging > backup-staging-values.yaml

# 2. Uninstall
helm uninstall mlops-sentiment -n mlops-sentiment-staging

# 3. Deploy via ArgoCD
kubectl apply -f infrastructure/gitops/applications/staging/

# 4. Verify
argocd app sync mlops-sentiment-staging
argocd app wait mlops-sentiment-staging --health
```

### 6. Migrate Production (Zero Downtime)

```bash
# 1. Backup everything
helm get values mlops-sentiment -n mlops-sentiment > backup-prod-values.yaml
kubectl get all -n mlops-sentiment -o yaml > backup-prod-resources.yaml

# 2. Annotate existing resources for ArgoCD tracking
kubectl annotate deployment,service,ingress,configmap,secret \
  -n mlops-sentiment \
  argocd.argoproj.io/tracking-id="mlops-sentiment-production:${GROUP}/${KIND}:mlops-sentiment/${NAME}"

# 3. Create ArgoCD application (won't delete existing resources)
kubectl apply -f infrastructure/gitops/applications/production/

# 4. Verify sync status
argocd app get mlops-sentiment-production

# 5. Perform dry-run sync
argocd app sync mlops-sentiment-production --dry-run

# 6. Actual sync
argocd app sync mlops-sentiment-production

# 7. Verify health
argocd app wait mlops-sentiment-production --health
kubectl get pods -n mlops-sentiment
```

### 7. Update CI/CD Pipelines

**GitHub Actions:**

- Remove direct `helm upgrade` from `.github/workflows/deploy.yml`
- Use `.github/workflows/gitops-update.yml` instead

**GitLab CI:**

- Replace `deploy:*` jobs with `gitops:*` jobs in `.gitlab-ci.yml`
- Keep `deploy:*:emergency` jobs for emergencies only

### 8. Verify End-to-End

```bash
# 1. Make a code change
git checkout -b test-gitops
echo "# Test" >> README.md
git add README.md
git commit -m "test: verify gitops workflow"
git push origin test-gitops

# 2. Create PR and merge to develop

# 3. Watch CI build image and update GitOps repo

# 4. Verify ArgoCD syncs automatically
argocd app get mlops-sentiment-development

# 5. Check deployment
kubectl get pods -n mlops-sentiment-dev
```

## Common Issues

### Issue: "Application is Out of Sync"

**Cause:** Local cluster state differs from Git

**Solution:**

```bash
argocd app diff mlops-sentiment-production
argocd app sync mlops-sentiment-production --prune
```

### Issue: "Repository not accessible"

**Cause:** Missing or incorrect credentials

**Solution:**

```bash
# Check repo config
argocd repo list

# Update credentials
kubectl edit secret -n argocd <repo-secret-name>

# Or recreate
kubectl delete secret github-credentials -n argocd
kubectl create secret generic github-credentials \
  -n argocd \
  --from-literal=username=<username> \
  --from-literal=password=<token>
```

### Issue: "Sync fails with permission denied"

**Cause:** ArgoCD doesn't have permission to create resources

**Solution:**

```bash
# Check RBAC
kubectl get rolebinding,clusterrolebinding -n argocd

# Grant additional permissions (if needed)
kubectl create rolebinding argocd-admin \
  -n mlops-sentiment \
  --clusterrole=admin \
  --serviceaccount=argocd:argocd-application-controller
```

### Issue: "Image pull errors after migration"

**Cause:** Image pull secrets not synced

**Solution:**

```bash
# Verify image pull secrets exist
kubectl get secret -n mlops-sentiment

# If missing, add to Helm values
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<username> \
  --docker-password=<password> \
  -n mlops-sentiment

# Update values to use secret
yq eval '.imagePullSecrets = [{"name": "regcred"}]' \
  -i infrastructure/gitops/environments/production/values.yaml
```

## Rollback Plan

If migration fails:

### Emergency Rollback

```bash
# 1. Delete ArgoCD application
kubectl delete application mlops-sentiment-production -n argocd

# 2. Restore from backup
kubectl apply -f backup-prod-resources.yaml

# 3. Or reinstall with Helm
helm install mlops-sentiment ./helm/mlops-sentiment \
  -n mlops-sentiment \
  --values backup-prod-values.yaml
```

### Gradual Rollback

```bash
# Keep ArgoCD but switch to manual sync
kubectl patch application mlops-sentiment-production -n argocd \
  --type=json \
  -p='[{"op": "replace", "path": "/spec/syncPolicy/automated", "value": null}]'

# Use emergency deploy workflow
# See .github/workflows/deploy.yml or .gitlab-ci.yml deploy:*:emergency jobs
```

## Post-Migration Tasks

- [ ] Update documentation
- [ ] Train team on new workflows
- [ ] Set up ArgoCD notifications (Slack/email)
- [ ] Configure ArgoCD SSO (GitHub/GitLab OAuth)
- [ ] Enable ArgoCD metrics in Grafana
- [ ] Set up ArgoCD webhooks for faster sync
- [ ] Document rollback procedures
- [ ] Schedule ArgoCD backup
- [ ] Review and optimize sync intervals
- [ ] Remove old deployment scripts (archive for reference)

## Validation Checklist

After migration:

- [ ] All environments deployed via ArgoCD
- [ ] Auto-sync working for dev/staging
- [ ] Manual sync working for production
- [ ] CI/CD pipelines updated image tags correctly
- [ ] Rollback tested successfully
- [ ] Monitoring and alerts configured
- [ ] Team can operate ArgoCD independently
- [ ] Documentation updated
- [ ] Old deployment methods deprecated
- [ ] Emergency procedures documented

## Next Steps

1. **Optimize sync policies** - Fine-tune auto-sync behavior
2. **Add sync waves** - For complex multi-resource deployments
3. **Enable notifications** - Slack/PagerDuty integration
4. **Set up RBAC** - Fine-grained access control
5. **Add webhooks** - Faster Git change detection
6. **Implement sync windows** - Control when syncs happen
7. **Add resource hooks** - Pre/post-sync actions
8. **Enable multi-cluster** - If managing multiple clusters
9. **Set up disaster recovery** - ArgoCD backup strategy
10. **Continuous improvement** - Monitor and optimize

## Resources

- [ArgoCD Getting Started](https://argo-cd.readthedocs.io/en/stable/getting_started/)
- [GitOps Best Practices](https://www.gitops.tech/)
- [Helm with ArgoCD](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)
- [ArgoCD Migration Guide](https://argo-cd.readthedocs.io/en/stable/operator-manual/upgrading/overview/)

---

**Migration Status:** Ready for deployment
**Last Updated:** 2025-12-16
**Version:** 1.0.0
