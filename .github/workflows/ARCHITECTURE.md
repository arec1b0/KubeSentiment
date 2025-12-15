# Workflow Architecture

This document provides a visual overview of the KubeSentiment GitHub Actions workflow architecture.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GitHub Actions Workflows                             │
│                          KubeSentiment Project                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          LAYER 1: REUSABLE COMPONENTS                        │
│                         (Building Blocks - Called by Others)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │ _reusable-code-      │  │ _reusable-tests      │  │ _reusable-docker-│  │
│  │ quality.yml          │  │ .yml                 │  │ build.yml        │  │
│  ├──────────────────────┤  ├──────────────────────┤  ├──────────────────┤  │
│  │ • Black formatting   │  │ • Unit tests         │  │ • Multi-platform │  │
│  │ • isort imports      │  │ • Integration tests  │  │ • SBOM gen       │  │
│  │ • Ruff linting       │  │ • Performance tests  │  │ • Image push     │  │
│  │ • Flake8 style       │  │ • Coverage reports   │  │ • Metadata       │  │
│  │ • mypy types         │  │ • Parameterized      │  │ • Cache layers   │  │
│  │ • Radon complexity   │  │                      │  │                  │  │
│  │ • Bandit security    │  │                      │  │                  │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LAYER 2: MAIN CI/CD WORKFLOWS                       │
│                          (Primary Pipelines - Use Reusables)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ci-pr.yml - Pull Request Validation                                 │   │
│  │ Trigger: Pull requests to main/develop                              │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  1. Code Quality (calls _reusable-code-quality.yml)                 │   │
│  │  2. Unit Tests (calls _reusable-tests.yml with type=unit)           │   │
│  │  3. Integration Tests (calls _reusable-tests.yml type=integration)  │   │
│  │  4. Performance Tests (calls _reusable-tests.yml type=performance)  │   │
│  │  5. Coverage Check (≥85% threshold)                                 │   │
│  │  6. PR Summary Comment                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ci-main.yml - Main/Develop Branch CI/CD                             │   │
│  │ Trigger: Push to main/develop, version tags                         │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  1. Code Quality (calls _reusable-code-quality.yml)                 │   │
│  │  2. Full Test Suite (calls _reusable-tests.yml type=all, 85%)      │   │
│  │  3. Docker Build (calls _reusable-docker-build.yml)                 │   │
│  │     - Multi-platform: amd64, arm64                                  │   │
│  │     - Push to ghcr.io                                               │   │
│  │  4. Security Scan (Trivy vulnerability scanning)                    │   │
│  │  5. Trigger Deployment (calls deploy.yml)                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ deploy.yml - Kubernetes Deployment                                  │   │
│  │ Trigger: Manual dispatch (on-demand)                                │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  Inputs: environment (dev/staging/prod), image_tag                  │   │
│  │  1. Setup kubectl and Helm                                          │   │
│  │  2. Determine deployment parameters                                 │   │
│  │  3. Helm upgrade --install                                          │   │
│  │  4. Health checks (wait for pods)                                   │   │
│  │  5. Smoke tests (curl health endpoint)                              │   │
│  │  6. Deployment summary                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 3: SPECIALIZED WORKFLOWS                        │
│                    (Domain-Specific - Independent Execution)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │ security-scan.yml - Comprehensive Security Scanning              │      │
│  │ Trigger: Daily 2 AM UTC, Manual, Dependency changes              │      │
│  ├──────────────────────────────────────────────────────────────────┤      │
│  │  1. Dependency Scan (Safety, pip-audit)                          │      │
│  │  2. Code Scan (Bandit)                                           │      │
│  │  3. SAST Scan (Semgrep - Python, Security, OWASP Top 10)        │      │
│  │  4. Docker Scan (Trivy, Grype)                                   │      │
│  │  5. Secret Scan (Gitleaks, TruffleHog)                           │      │
│  │  6. Security Summary Report                                      │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │ release.yml - Automated Release Management                       │      │
│  │ Trigger: Version tags (v*.*.*), Manual                           │      │
│  ├──────────────────────────────────────────────────────────────────┤      │
│  │  1. Validate version format (vX.Y.Z)                             │      │
│  │  2. Full test suite (calls _reusable-tests.yml)                  │      │
│  │  3. Build image variants (calls _reusable-docker-build.yml 3x)  │      │
│  │     - Standard (Dockerfile)                                      │      │
│  │     - Optimized (Dockerfile.optimized)                           │      │
│  │     - Distroless (Dockerfile.distroless)                         │      │
│  │  4. Generate changelog (git log)                                 │      │
│  │  5. Create GitHub release                                        │      │
│  │  6. Deploy to production (calls deploy.yml)                      │      │
│  │  7. Update Helm chart version                                    │      │
│  │  8. Send Slack notification                                      │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │ docs.yml - Documentation Validation & Deployment                 │      │
│  │ Trigger: Push/PR (docs changes), Manual                          │      │
│  ├──────────────────────────────────────────────────────────────────┤      │
│  │  1. Validate Markdown (markdown-link-check, markdownlint)       │      │
│  │  2. Generate API docs (pdoc3)                                    │      │
│  │  3. Check ADR structure (custom script)                          │      │
│  │  4. Build MkDocs site                                            │      │
│  │  5. Deploy to GitHub Pages (main branch only)                   │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │ infrastructure.yml - Terraform IaC Management                    │      │
│  │ Trigger: Manual (with inputs), Push (infra changes)              │      │
│  ├──────────────────────────────────────────────────────────────────┤      │
│  │  Inputs: environment (dev/prod), action (plan/apply/destroy)     │      │
│  │  1. Terraform format check                                       │      │
│  │  2. Terraform init                                               │      │
│  │  3. Terraform validate                                           │      │
│  │  4. Terraform plan                                               │      │
│  │  5. Terraform apply/destroy (conditional)                        │      │
│  │  6. Upload plan artifacts                                        │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │ secrets-rotation.yml - Vault Secret Rotation                     │      │
│  │ Trigger: Weekly Sunday midnight, Manual                          │      │
│  ├──────────────────────────────────────────────────────────────────┤      │
│  │  Inputs: environment, secret_name, dry_run                       │      │
│  │  1. Import secrets from Vault (OIDC auth)                        │      │
│  │  2. Rotate secrets (custom script)                               │      │
│  │  3. Wait for Kubernetes rollout                                  │      │
│  │  4. Verify application health                                    │      │
│  │  5. Send Slack notification                                      │      │
│  │  6. Create audit log (JSON artifact)                             │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Workflow Trigger Matrix

| Workflow | PR | Push (main/dev) | Tag | Cron | Manual |
|----------|----|--------------------|-----|------|--------|
| **ci-pr.yml** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **ci-main.yml** | ❌ | ✅ | ✅ | ❌ | ❌ |
| **deploy.yml** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **security-scan.yml** | ❌ | ✅* | ❌ | ✅ Daily 2AM | ✅ |
| **release.yml** | ❌ | ❌ | ✅ | ❌ | ✅ |
| **docs.yml** | ✅* | ✅* | ❌ | ❌ | ✅ |
| **infrastructure.yml** | ❌ | ✅* | ❌ | ❌ | ✅ |
| **secrets-rotation.yml** | ❌ | ❌ | ❌ | ✅ Weekly Sun | ✅ |

*Only on specific path changes

## Data Flow Diagram

```
┌─────────────┐
│  Developer  │
└──────┬──────┘
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│  Create PR   │  │  Push Main   │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│  ci-pr.yml   │  │ ci-main.yml  │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ├─────────────────┴─────────────────┐
       │                                   │
       ▼                                   ▼
┌──────────────────┐            ┌──────────────────┐
│ Reusable: Code   │            │ Reusable: Tests  │
│ Quality          │            │                  │
└──────────────────┘            └──────────────────┘
       │                                   │
       └─────────────────┬─────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   Success?   │
                  └──────┬───────┘
                         │
                    Yes  │  No
            ┌────────────┴────────────┐
            ▼                         ▼
    ┌──────────────┐         ┌──────────────┐
    │ Docker Build │         │  Fail & Stop │
    └──────┬───────┘         └──────────────┘
           │
           ▼
    ┌──────────────┐
    │ Push to GHCR │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │   Security   │
    │     Scan     │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │   Trigger    │
    │  Deployment  │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  deploy.yml  │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  Kubernetes  │
    │   Cluster    │
    └──────────────┘
```

## Component Dependencies

```
_reusable-code-quality.yml
    ↓
ci-pr.yml (uses)
ci-main.yml (uses)
release.yml (indirectly via ci-main)

_reusable-tests.yml
    ↓
ci-pr.yml (uses 3x: unit, integration, performance)
ci-main.yml (uses 1x: all)
release.yml (uses 1x: all)

_reusable-docker-build.yml
    ↓
ci-main.yml (uses 1x: standard)
release.yml (uses 3x: standard, optimized, distroless)

deploy.yml
    ↓
ci-main.yml (triggers)
release.yml (triggers for production)
Manual triggers

No Dependencies (Standalone):
- security-scan.yml
- docs.yml
- infrastructure.yml
- secrets-rotation.yml
```

## Execution Patterns

### Pattern 1: Pull Request Validation (Fast Path)

```
PR Created → ci-pr.yml
    ├─ [Parallel] Code Quality (2 min)
    ├─ [Parallel] Unit Tests (3 min)
    ├─ [Parallel] Integration Tests (3 min)
    └─ [Parallel] Performance Tests (2 min)
    ↓
Coverage Check (1 min)
    ↓
PR Summary Comment
    ↓
Total Time: ~7 minutes
```

### Pattern 2: Main Branch Build & Deploy (Full Path)

```
Push to main → ci-main.yml
    ├─ [Serial] Code Quality (2 min)
    ├─ [Serial] Full Test Suite (5 min)
    ├─ [Serial] Docker Build (4 min)
    └─ [Serial] Security Scan (3 min)
    ↓
Trigger deploy.yml
    ├─ [Serial] Helm Install (2 min)
    ├─ [Serial] Health Checks (1 min)
    └─ [Serial] Smoke Tests (1 min)
    ↓
Total Time: ~18 minutes
```

### Pattern 3: Release (Comprehensive Path)

```
Tag v1.2.3 → release.yml
    ├─ [Serial] Validation (1 min)
    ├─ [Serial] Full Tests (5 min)
    ├─ [Parallel 3x] Build Images (5 min each → 5 min total)
    ├─ [Serial] Generate Changelog (1 min)
    ├─ [Serial] Create Release (1 min)
    ├─ [Serial] Deploy Production (5 min)
    ├─ [Serial] Update Helm Chart (1 min)
    └─ [Serial] Notification (1 min)
    ↓
Total Time: ~20 minutes
```

## Key Architectural Decisions

### 1. Reusable Workflows as Foundation

**Decision:** Create reusable workflow components that can be called by multiple workflows.

**Rationale:**
- Eliminates code duplication
- Single source of truth for common operations
- Easier maintenance and updates
- Consistent behavior across workflows

### 2. Separate PR and Main Workflows

**Decision:** Split CI workflow into `ci-pr.yml` and `ci-main.yml`.

**Rationale:**
- Faster PR validation (skip build/deploy)
- Different requirements for PR vs production
- Clearer separation of concerns
- Better resource utilization

### 3. On-Demand Deployment

**Decision:** Make `deploy.yml` manually triggered instead of automatic.

**Rationale:**
- More control over deployments
- Avoid accidental production deploys
- Can deploy any image tag to any environment
- Better for GitOps workflows

### 4. Specialized Workflows

**Decision:** Create dedicated workflows for security, releases, docs, etc.

**Rationale:**
- Independent execution schedules
- Focused responsibility
- Can be maintained by domain experts
- Doesn't clutter main CI/CD

### 5. Multi-Platform Images

**Decision:** Build for both amd64 and arm64 architectures.

**Rationale:**
- Support for Apple Silicon Macs
- Future-proof for ARM servers
- Cost savings on ARM-based cloud instances
- Wider deployment compatibility

---

## Best Practices Implemented

✅ **DRY (Don't Repeat Yourself):** Reusable workflows eliminate duplication
✅ **Separation of Concerns:** Each workflow has a single responsibility
✅ **Fast Feedback:** PR workflows complete in ~7 minutes
✅ **Security First:** Dedicated security scanning workflow
✅ **Observability:** Job summaries, artifacts, notifications
✅ **Fail Fast:** Early validation prevents expensive later failures
✅ **Caching:** Aggressive caching of dependencies
✅ **Parallelization:** Jobs run concurrently where possible
✅ **Versioning:** Pinned action versions for stability
✅ **Documentation:** Comprehensive docs for all workflows

---

## Related Documentation

- [Workflow README](README.md) - Complete workflow documentation
- [Migration Guide](MIGRATION_GUIDE.md) - Migrating from legacy workflows
- [Refactoring Summary](../WORKFLOWS_REFACTORING_SUMMARY.md) - Executive summary

---

**Last Updated:** 2025-12-15
**Version:** 2.0 (Modular Architecture)
