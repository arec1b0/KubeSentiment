# Workflow Migration Guide

This guide helps you understand the changes in the new modular workflow architecture and how to migrate from the legacy monolithic CI workflow.

## Overview of Changes

### Before (Legacy)

Single monolithic `ci.yml` file containing:
- Code quality checks
- Unit, integration, and performance tests
- Coverage verification
- Docker build
- Security scanning
- Deployment to all environments

**Problems:**
- Hard to maintain and understand
- All jobs run for every trigger
- No code reuse
- Difficult to test individual components
- Long execution times

### After (Modular)

Multiple specialized workflows:
- **Reusable components** for common tasks
- **Separate workflows** for PRs vs main branch
- **Specialized workflows** for security, releases, docs
- **On-demand deployment** workflow

**Benefits:**
- ✅ Better separation of concerns
- ✅ Faster PR validation
- ✅ Reusable workflow components
- ✅ Easier to maintain and test
- ✅ More efficient resource usage

---

## Workflow Mapping

| Legacy Workflow | New Workflow(s) | Notes |
|----------------|-----------------|-------|
| `ci.yml` (PR) | `ci-pr.yml` | Focused on PR validation only |
| `ci.yml` (main push) | `ci-main.yml` | Main branch CI/CD |
| `ci.yml` (deployment) | `deploy.yml` | Separated deployment logic |
| N/A | `_reusable-*.yml` | Reusable components |
| N/A | `security-scan.yml` | Dedicated security workflow |
| N/A | `release.yml` | Automated release process |
| N/A | `docs.yml` | Documentation validation |
| `terraform-apply.yml` | `infrastructure.yml` | Renamed for clarity |
| `vault-secret-rotation.yml` | `secrets-rotation.yml` | Renamed for consistency |

---

## Key Changes

### 1. Pull Request Workflow

**Legacy:**
```yaml
# ci.yml
on:
  pull_request:
    branches: [main, develop]
# ... all jobs run including build and deploy
```

**New:**
```yaml
# ci-pr.yml
on:
  pull_request:
    branches: [main, develop]

jobs:
  code-quality:
    uses: ./.github/workflows/_reusable-code-quality.yml

  unit-tests:
    uses: ./.github/workflows/_reusable-tests.yml
    with:
      test-type: unit
```

**Impact:** PRs now run faster by only validating code, not building/deploying.

### 2. Main Branch Workflow

**Legacy:**
```yaml
# ci.yml - everything in one file
jobs:
  lint: ...
  test: ...
  build: ...
  deploy: ...
```

**New:**
```yaml
# ci-main.yml - build and security
jobs:
  test-suite:
    uses: ./.github/workflows/_reusable-tests.yml

  build:
    uses: ./.github/workflows/_reusable-docker-build.yml

  trigger-deploy:
    # Triggers separate deploy.yml workflow
```

**Impact:** Better separation between CI (test/build) and CD (deploy).

### 3. Deployment

**Legacy:**
```yaml
# ci.yml - deployment embedded in CI
deploy:
  strategy:
    matrix:
      environment: [dev, staging, prod]
  # Complex conditional logic
```

**New:**
```yaml
# deploy.yml - standalone deployment workflow
on:
  workflow_dispatch:
    inputs:
      environment: ...
      image_tag: ...

# Simple, focused deployment logic
```

**Impact:** Deployments can now be triggered independently of CI.

### 4. Reusable Components

**New Capability:** Share workflow logic across multiple workflows.

```yaml
# Any workflow can now use:
jobs:
  my-tests:
    uses: ./.github/workflows/_reusable-tests.yml
    with:
      test-type: unit
      coverage-threshold: 85
```

**Impact:** DRY principle - write once, use everywhere.

---

## Migration Steps

### Step 1: Understanding Your Current Setup

1. Review `ci.yml.legacy` to understand current triggers and jobs
2. Identify which jobs run on PRs vs main branch
3. Note any custom configurations or secrets used

### Step 2: Testing New Workflows

The new workflows are already in place. To test:

1. **Create a test PR:**
   ```bash
   git checkout -b test/new-workflows
   # Make a small change
   git commit -am "test: validate new workflow system"
   git push origin test/new-workflows
   # Open PR on GitHub
   ```

2. **Verify PR workflow runs:**
   - Check that `ci-pr.yml` runs
   - Confirm code quality and tests pass
   - Verify coverage check succeeds

3. **Test main branch workflow:**
   ```bash
   # After PR is merged to develop
   # Check that ci-main.yml runs
   # Verify image is built and pushed
   ```

### Step 3: Adjusting Secrets and Variables

Ensure these secrets/variables are set in your repository:

```
Required Secrets:
- GITHUB_TOKEN (automatic)
- KUBE_CONFIG (base64 encoded kubeconfig)
- CODECOV_TOKEN (optional, for coverage)
- SLACK_WEBHOOK_URL (optional, for notifications)
- VAULT_ADDR (for secret rotation)
- TF_STATE_BUCKET (for Terraform)

Optional Secrets:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- DOCKER_USERNAME
- DOCKER_PASSWORD
```

### Step 4: Updating Branch Protection Rules

Update branch protection to use new workflow names:

**Before:**
```
Required status checks:
- CI/CD Pipeline / lint
- CI/CD Pipeline / unit-tests
- CI/CD Pipeline / coverage-check
```

**After:**
```
Required status checks:
- Pull Request CI / code-quality
- Pull Request CI / unit-tests
- Pull Request CI / coverage-check
```

### Step 5: Removing Legacy Workflows

After confirming new workflows work correctly:

```bash
# Delete legacy file
git rm .github/workflows/ci.yml.legacy
git commit -m "chore: remove legacy CI workflow"
git push origin main
```

---

## Troubleshooting

### Issue: Workflows Not Running

**Symptom:** New workflows don't trigger on PR or push.

**Solution:**
1. Check workflow files are in `.github/workflows/` on main branch
2. Verify YAML syntax: `yamllint .github/workflows/*.yml`
3. Check repository settings → Actions → General → Allow all actions

### Issue: Reusable Workflow Not Found

**Symptom:** Error "Unable to resolve action `./github/workflows/_reusable-*.yml`"

**Solution:**
1. Reusable workflows must be on the default branch (main)
2. Check the path is correct: `./.github/workflows/_reusable-*.yml`
3. Verify the reusable workflow file exists

### Issue: Permission Denied

**Symptom:** Jobs fail with "Resource not accessible by integration"

**Solution:**
Add permissions to workflow:
```yaml
jobs:
  my-job:
    permissions:
      contents: read
      packages: write
      id-token: write
```

### Issue: Deployment Not Triggering

**Symptom:** `ci-main.yml` runs but `deploy.yml` doesn't trigger.

**Solution:**
1. Check `workflow_dispatch` permissions are enabled
2. Verify environment names match in repository settings
3. Manually trigger first deployment:
   ```bash
   gh workflow run deploy.yml \
     -f environment=development \
     -f image_tag=develop-abc123
   ```

### Issue: Coverage Threshold Failing

**Symptom:** Coverage check fails with new workflows.

**Solution:**
1. Adjust threshold in `_reusable-tests.yml` or calling workflow
2. Run locally: `pytest --cov=app --cov-fail-under=85`
3. Check if test files moved or renamed

---

## Rollback Plan

If you need to rollback to the legacy workflow:

### Quick Rollback

```bash
# Restore legacy workflow
git mv .github/workflows/ci.yml.legacy .github/workflows/ci.yml

# Disable new workflows (rename to prevent triggering)
for f in .github/workflows/{ci-pr,ci-main,deploy}.yml; do
  git mv "$f" "$f.disabled"
done

git commit -m "rollback: restore legacy CI workflow"
git push origin main
```

### Gradual Rollback

Keep new workflows but fall back for specific scenarios:

1. **Use legacy for production:**
   - Keep `ci.yml.legacy` active for production deployments
   - Use new workflows for dev/staging

2. **Parallel running:**
   - Run both legacy and new workflows side-by-side
   - Compare results before fully migrating

---

## Best Practices for New Architecture

### 1. Keep Reusable Workflows Generic

```yaml
# ✅ Good - flexible and reusable
on:
  workflow_call:
    inputs:
      test-type:
        type: string
        required: true

# ❌ Bad - too specific
on:
  workflow_call:
    # No inputs, hardcoded values
```

### 2. Use Workflow Outputs

```yaml
# Reusable workflow
jobs:
  build:
    outputs:
      image-tag: ${{ steps.extract.outputs.tag }}

# Calling workflow
jobs:
  deploy:
    needs: build
    run: |
      echo "Deploying ${{ needs.build.outputs.image-tag }}"
```

### 3. Document Workflow Dependencies

```yaml
# At the top of each workflow file
# Dependencies:
# - Requires: KUBE_CONFIG secret
# - Calls: _reusable-tests.yml
# - Triggers: deploy.yml (on success)
```

### 4. Test Locally When Possible

```bash
# Use act to test workflows locally
act -j code-quality -W .github/workflows/ci-pr.yml

# Test with specific event
act pull_request -W .github/workflows/ci-pr.yml
```

### 5. Monitor Workflow Performance

```bash
# Use GitHub CLI to check workflow runs
gh run list --workflow=ci-pr.yml --limit 20

# View specific run
gh run view <run-id>

# Check workflow timing
gh run view <run-id> --log | grep "took"
```

---

## FAQ

### Q: Can I still use the old workflow?

**A:** Yes, `ci.yml.legacy` is preserved for reference. You can restore it if needed, but the new modular approach is recommended.

### Q: Do I need to update my Makefile?

**A:** No, the Makefile commands remain the same. The changes only affect GitHub Actions workflows.

### Q: Will this affect local development?

**A:** No, local development is unchanged. All `make` commands work as before.

### Q: How do I trigger a deployment manually?

**A:** Use the GitHub UI or CLI:
```bash
gh workflow run deploy.yml \
  -f environment=staging \
  -f image_tag=main-abc123
```

### Q: Can I customize the reusable workflows?

**A:** Yes, you can override inputs when calling them:
```yaml
jobs:
  my-tests:
    uses: ./.github/workflows/_reusable-tests.yml
    with:
      python-version: "3.12"
      coverage-threshold: 90
```

### Q: What happens to old workflow runs?

**A:** They remain visible in the Actions tab under the legacy workflow name. New runs use the new workflow names.

---

## Getting Help

If you encounter issues during migration:

1. **Check workflow logs** in GitHub Actions tab
2. **Review this guide** and the [Workflow README](.github/workflows/README.md)
3. **Test locally** with `act` when possible
4. **Compare with legacy** workflow behavior
5. **Open an issue** with detailed logs and context

---

## Related Documentation

- [Workflow README](README.md) - Complete workflow documentation
- [GitHub Actions Reusing Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Contribution guidelines
- [CLAUDE.md](../../CLAUDE.md) - AI assistant guide

---

**Last Updated:** 2025-12-15

**Migration Status:** ✅ Complete - New workflows active, legacy preserved for reference
