# GitHub Actions Workflows

This directory contains all GitHub Actions workflows for the KubeSentiment project. The workflows are organized into reusable components and specialized workflows for different purposes.

## Table of Contents

1. [Workflow Architecture](#workflow-architecture)
2. [Reusable Workflows](#reusable-workflows)
3. [Main Workflows](#main-workflows)
4. [Specialized Workflows](#specialized-workflows)
5. [Legacy Workflows](#legacy-workflows)
6. [Usage Examples](#usage-examples)
7. [Best Practices](#best-practices)

---

## Workflow Architecture

The workflow system is designed with modularity and reusability in mind:

```
┌─────────────────────────────────────────────────────────┐
│              Reusable Workflows (Components)            │
├─────────────────────────────────────────────────────────┤
│ • _reusable-code-quality.yml                            │
│ • _reusable-tests.yml                                   │
│ • _reusable-docker-build.yml                            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Main CI/CD Workflows                  │
├─────────────────────────────────────────────────────────┤
│ • ci-pr.yml           - Pull Request validation         │
│ • ci-main.yml         - Main/Develop branch CI/CD       │
│ • deploy.yml          - Kubernetes deployment           │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                 Specialized Workflows                   │
├─────────────────────────────────────────────────────────┤
│ • security-scan.yml   - Security scanning (daily)       │
│ • release.yml         - Release automation              │
│ • docs.yml            - Documentation validation        │
│ • infrastructure.yml  - Terraform IaC                   │
│ • secrets-rotation.yml - Vault secret rotation          │
└─────────────────────────────────────────────────────────┘
```

---

## Reusable Workflows

Reusable workflow components that can be called by other workflows. These start with `_reusable-` prefix.

### `_reusable-code-quality.yml`

Performs comprehensive code quality checks including formatting, linting, type checking, and security scanning.

**Inputs:**
- `python-version` (string, default: "3.11") - Python version to use
- `target-paths` (string, default: "app/ tests/ scripts/ run.py") - Paths to check

**Tools:**
- Black (formatting)
- isort (import sorting)
- Ruff (fast linting)
- Flake8 (style checking)
- mypy (type checking)
- Radon (complexity analysis)
- Bandit (security scanning)

**Example:**
```yaml
jobs:
  quality:
    uses: ./.github/workflows/_reusable-code-quality.yml
    with:
      python-version: "3.11"
```

### `_reusable-tests.yml`

Runs tests with coverage reporting. Supports different test types and coverage thresholds.

**Inputs:**
- `python-version` (string, default: "3.11") - Python version to use
- `test-type` (string, required) - Type of tests: unit/integration/performance/all
- `coverage-threshold` (number, default: 0) - Minimum coverage percentage

**Outputs:**
- `coverage-percentage` - Test coverage percentage

**Example:**
```yaml
jobs:
  unit-tests:
    uses: ./.github/workflows/_reusable-tests.yml
    with:
      python-version: "3.11"
      test-type: unit
      coverage-threshold: 85
```

### `_reusable-docker-build.yml`

Builds and optionally pushes Docker images with multi-platform support and SBOM generation.

**Inputs:**
- `dockerfile` (string, default: "Dockerfile") - Dockerfile to use
- `image-name` (string, required) - Image name without registry
- `push` (boolean, default: false) - Whether to push to registry
- `platforms` (string, default: "linux/amd64") - Target platforms
- `build-args` (string, default: "") - Additional build arguments

**Outputs:**
- `image-tag` - Short image tag
- `image-full` - Full image reference
- `image-digest` - Image digest

**Example:**
```yaml
jobs:
  build:
    uses: ./.github/workflows/_reusable-docker-build.yml
    with:
      dockerfile: Dockerfile.optimized
      image-name: ${{ github.repository }}
      push: true
      platforms: linux/amd64,linux/arm64
```

---

## Main Workflows

### `ci-pr.yml` - Pull Request CI

**Triggers:** Pull requests to main/develop branches

**Jobs:**
1. Code quality checks
2. Unit tests
3. Integration tests
4. Performance tests
5. Combined coverage check (≥85%)
6. PR summary comment

**Purpose:** Validate all changes before merging

### `ci-main.yml` - Main Branch CI/CD

**Triggers:**
- Push to main/develop branches
- Version tags (v*)

**Jobs:**
1. Code quality checks
2. Full test suite with 85% coverage threshold
3. Multi-platform Docker image build
4. Security scanning with Trivy
5. Trigger deployment workflow

**Purpose:** Build and prepare deployments for main branches

### `deploy.yml` - Kubernetes Deployment

**Triggers:** Manual workflow dispatch

**Inputs:**
- `environment` - Target environment (development/staging/production)
- `image_tag` - Image tag to deploy

**Jobs:**
1. Deploy to Kubernetes with Helm
2. Run health checks
3. Run smoke tests
4. Generate deployment summary

**Purpose:** Deploy to Kubernetes clusters

---

## Specialized Workflows

### `security-scan.yml` - Security Scanning

**Triggers:**
- Daily at 2 AM UTC (cron)
- Manual dispatch
- Push to main/develop (on dependency/Dockerfile changes)

**Jobs:**
1. **Dependency Scan** - Safety and pip-audit
2. **Code Scan** - Bandit security analysis
3. **SAST Scan** - Semgrep static analysis
4. **Docker Scan** - Trivy and Grype
5. **Secret Scan** - Gitleaks and TruffleHog
6. **Security Summary** - Consolidated report

**Purpose:** Continuous security monitoring

### `release.yml` - Release Automation

**Triggers:**
- Push of version tags (v*.*.*)
- Manual dispatch with version input

**Jobs:**
1. Validate release version format
2. Run full test suite
3. Build multi-platform release images (standard/optimized/distroless)
4. Create GitHub release with changelog
5. Deploy to production
6. Update Helm chart version
7. Send notification

**Purpose:** Automated release process

### `docs.yml` - Documentation Validation

**Triggers:**
- Push to main/develop (docs changes)
- Pull requests (docs changes)
- Manual dispatch

**Jobs:**
1. **Validate** - Check Markdown links and lint
2. **Generate API Docs** - Create pdoc documentation
3. **Check ADRs** - Verify ADR structure
4. **Build Docs Site** - Generate MkDocs site
5. **Deploy Pages** - Deploy to GitHub Pages (main only)

**Purpose:** Maintain documentation quality

### `infrastructure.yml` - Terraform IaC

**Triggers:**
- Manual dispatch (with environment and action inputs)
- Push to main (infrastructure changes)

**Inputs:**
- `environment` - Target environment (dev/prod)
- `action` - Terraform action (plan/apply/destroy)

**Jobs:**
1. Format check
2. Terraform init
3. Terraform validate
4. Terraform plan
5. Terraform apply (conditional)
6. Upload plan artifacts

**Purpose:** Infrastructure as Code management

### `secrets-rotation.yml` - Vault Secret Rotation

**Triggers:**
- Weekly on Sundays at midnight UTC (cron)
- Manual dispatch

**Inputs:**
- `environment` - Environment to rotate (dev/staging/prod)
- `secret_name` - Specific secret or all
- `dry_run` - Test mode

**Jobs:**
1. Import secrets from Vault
2. Rotate specified secrets
3. Wait for Kubernetes rollout
4. Verify application health
5. Send notification (Slack)
6. Create audit log

**Purpose:** Automated secret rotation for security

---

## Legacy Workflows

These workflows are kept for reference but are superseded by the new modular system:

- `ci.yml.legacy` - Original monolithic CI/CD workflow
- The new system splits this into `ci-pr.yml`, `ci-main.yml`, and `deploy.yml`

---

## Usage Examples

### Running Tests Locally

Simulate what CI does:

```bash
# Code quality
black --check app/ tests/
isort --check-only app/ tests/
ruff check app/ tests/
mypy app/

# Tests
pytest tests/unit/ -v -m unit --cov=app
pytest tests/integration/ -v -m integration --cov=app
pytest tests/ -v --cov=app --cov-fail-under=85
```

### Triggering Deployment

```bash
# Via GitHub CLI
gh workflow run deploy.yml \
  -f environment=staging \
  -f image_tag=main-abc123

# Via API
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/actions/workflows/deploy.yml/dispatches \
  -d '{"ref":"main","inputs":{"environment":"staging","image_tag":"main-abc123"}}'
```

### Creating a Release

```bash
# Create and push tag
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3

# Or use GitHub CLI
gh release create v1.2.3 --generate-notes
```

---

## Best Practices

### 1. **Use Reusable Workflows**

Always use reusable components instead of duplicating logic:

```yaml
# ✅ Good
jobs:
  test:
    uses: ./.github/workflows/_reusable-tests.yml
    with:
      test-type: unit

# ❌ Bad - duplicating test logic
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: pytest tests/
```

### 2. **Parameterize Workflows**

Make workflows flexible with inputs:

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [dev, staging, prod]
```

### 3. **Use Caching**

Cache dependencies to speed up workflows:

```yaml
- uses: actions/setup-python@v4
  with:
    python-version: "3.11"
    cache: "pip"  # ← Automatically caches pip dependencies
```

### 4. **Fail Fast**

Use `needs` to create dependencies and fail early:

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    # ...

  test:
    needs: lint  # ← Only run if lint passes
    runs-on: ubuntu-latest
    # ...
```

### 5. **Use Secrets Securely**

Never hardcode secrets in workflows:

```yaml
# ✅ Good
- name: Login
  env:
    TOKEN: ${{ secrets.MY_SECRET }}
  run: echo "$TOKEN" | tool login

# ❌ Bad
- name: Login
  run: echo "hardcoded-secret" | tool login
```

### 6. **Add Job Summaries**

Use `$GITHUB_STEP_SUMMARY` for readable output:

```yaml
- name: Summary
  run: |
    echo "## Deployment Complete" >> $GITHUB_STEP_SUMMARY
    echo "- Environment: production" >> $GITHUB_STEP_SUMMARY
    echo "- Image: myapp:v1.2.3" >> $GITHUB_STEP_SUMMARY
```

### 7. **Test Workflows Locally**

Use [act](https://github.com/nektos/act) to test workflows locally:

```bash
# Install act
brew install act  # macOS
choco install act  # Windows

# Run workflow
act -j code-quality
act pull_request
```

### 8. **Version Control Actions**

Pin action versions for security and stability:

```yaml
# ✅ Good - pinned version
- uses: actions/checkout@v4

# ⚠️ Acceptable - major version
- uses: actions/checkout@v4

# ❌ Bad - unpinned
- uses: actions/checkout@master
```

### 9. **Use Matrix Builds**

Test across multiple versions/platforms:

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
    os: [ubuntu-latest, macos-latest, windows-latest]
```

### 10. **Monitor Workflow Performance**

- Review workflow run times regularly
- Optimize slow jobs
- Use parallel execution where possible
- Cache aggressively

---

## Workflow Maintenance

### Adding a New Workflow

1. Create workflow file in `.github/workflows/`
2. Follow naming convention:
   - Reusable: `_reusable-<name>.yml`
   - Main: `<name>.yml`
3. Add documentation to this README
4. Test locally with `act` if possible
5. Create PR and verify in CI

### Updating Workflows

1. Update workflow file
2. Update documentation
3. Test changes in a feature branch
4. Review impact on dependent workflows
5. Monitor first runs after merge

### Deprecating Workflows

1. Rename to `<name>.yml.legacy`
2. Add deprecation notice at the top
3. Update documentation
4. Remove after 2 major versions

---

## Troubleshooting

### Workflow Not Triggering

- Check trigger conditions (branches, paths)
- Verify permissions in repository settings
- Check if workflow file is in main/default branch

### Job Failing

1. Check the logs for specific errors
2. Run the commands locally
3. Verify secrets are set correctly
4. Check action versions for breaking changes

### Slow Workflows

1. Enable caching for dependencies
2. Use matrix builds for parallel execution
3. Optimize test suite (mark slow tests)
4. Use self-hosted runners for heavy workloads

### Permission Errors

Add required permissions to job:

```yaml
jobs:
  my-job:
    permissions:
      contents: write
      packages: write
```

---

## Related Documentation

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Reusing Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [Environment Variables](../../../docs/configuration/ENVIRONMENT_VARIABLES.md)
- [Deployment Guide](../../../docs/setup/deployment-guide.md)
- [Contributing Guidelines](../../../CONTRIBUTING.md)

---

## Version History

| Date | Changes |
|------|---------|
| 2025-12-15 | Initial refactoring - modular workflow architecture |

---

**Note**: This workflow structure follows MLOps best practices and is designed for production use. Always test workflow changes in a feature branch before merging to main.
