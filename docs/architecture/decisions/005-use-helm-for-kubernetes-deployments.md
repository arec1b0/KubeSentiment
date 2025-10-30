# ADR 005: Use Helm for Kubernetes Deployments

**Status:** Accepted
**Date:** 2024-01-25
**Authors:** KubeSentiment Team

## Context

We need a deployment strategy for KubeSentiment on Kubernetes that provides:
- Reproducible deployments across environments (dev/staging/prod)
- Configuration management without duplicating YAML
- Version control for deployment configurations
- Easy rollback capabilities
- Package dependencies (Prometheus, Grafana, Redis)
- Templating for environment-specific values

Our deployment includes:
- Main application (API server)
- Dependencies (Prometheus, Grafana, Redis, Alertmanager)
- ConfigMaps and Secrets
- Services, Ingress, HPA
- ServiceMonitors and PrometheusRules

## Decision

We will use **Helm** as the package manager and deployment tool for Kubernetes.

### Implementation Strategy

1. **Helm Chart Structure**:
   - Main chart: `helm/mlops-sentiment/`
   - Dependencies: Prometheus, Grafana, Alertmanager (via subchart dependencies)
   - Environment-specific values files

2. **Templating Approach**:
   - Use Helm templates for all Kubernetes resources
   - Separate values files per environment
   - Named templates for reusable components

3. **Release Management**:
   - Semantic versioning for chart versions
   - Automated releases via CI/CD
   - Rollback support through Helm history

## Consequences

### Positive

- **DRY principle**: No duplicate YAML across environments
- **Easy parameterization**: Values files for environment-specific config
- **Dependency management**: Automatic handling of Prometheus, Grafana, etc.
- **Rollback support**: `helm rollback` for easy recovery
- **Release history**: Track all deployments and changes
- **Hooks support**: Pre/post-install hooks for migrations
- **Large ecosystem**: Thousands of community charts available
- **Testing**: `helm template` for validation before deploy

### Negative

- **Learning curve**: Helm templating can be complex
- **Debugging difficulty**: Template errors can be cryptic
- **Over-templating risk**: Can make charts hard to read
- **Version compatibility**: Helm 2 vs 3 breaking changes
- **State management**: Helm releases stored in Kubernetes secrets

### Neutral

- **Additional tool**: Team must learn Helm
- **Chart maintenance**: Templates require ongoing updates
- **Values complexity**: Large values files can be unwieldy

## Alternatives Considered

### Alternative 1: kubectl with Kustomize

**Pros:**
- Native to kubectl (no extra tools)
- Simpler than Helm
- Good for overlays and patches

**Cons:**
- No dependency management
- No release history
- Limited templating capabilities
- No package versioning
- Harder to manage complex deployments

**Rejected because**: Lack of dependency management and release history are critical for our needs.

### Alternative 2: Raw Kubernetes YAML

**Pros:**
- Simplest approach
- No tooling required
- Full control

**Cons:**
- Massive duplication across environments
- No parameterization
- Manual dependency management
- No rollback mechanism
- No version control for deployments

**Rejected because**: Does not scale for multiple environments and dependencies.

### Alternative 3: Terraform with Kubernetes Provider

**Pros:**
- Infrastructure as Code
- State management
- Good for multi-cloud

**Cons:**
- Not designed for Kubernetes applications
- More complex than Helm
- Slower iteration cycle
- No native Kubernetes packaging

**Rejected because**: Terraform better suited for infrastructure, not application deployment.

### Alternative 4: ArgoCD/FluxCD (GitOps)

**Pros:**
- GitOps workflow
- Automatic synchronization
- Great for continuous deployment

**Cons:**
- Requires additional infrastructure
- Steeper learning curve
- Over-engineered for our current scale
- Can still use Helm underneath

**Decision**: Adopt in future, but can be used with Helm charts.

## Implementation Details

### Chart Structure

```
helm/mlops-sentiment/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default values
├── values-dev.yaml         # Development overrides
├── values-staging.yaml     # Staging overrides
├── values-prod.yaml        # Production overrides
├── templates/
│   ├── deployment.yaml     # Main application
│   ├── service.yaml        # Service
│   ├── ingress.yaml        # Ingress
│   ├── hpa.yaml            # Horizontal Pod Autoscaler
│   ├── configmap.yaml      # Configuration
│   ├── secret.yaml         # Secrets
│   ├── servicemonitor.yaml # Prometheus metrics
│   ├── prometheusrule.yaml # Alerts
│   ├── _helpers.tpl        # Template helpers
│   └── NOTES.txt           # Post-install notes
└── charts/                 # Dependency charts (cached)
```

### Chart.yaml

```yaml
apiVersion: v2
name: mlops-sentiment
description: Production-ready MLOps sentiment analysis microservice
type: application
version: 0.1.0
appVersion: "1.0.0"

dependencies:
  - name: prometheus
    version: "25.8.0"
    repository: "https://prometheus-community.github.io/helm-charts"
    condition: prometheus.enabled
  - name: grafana
    version: "7.0.19"
    repository: "https://grafana.github.io/helm-charts"
    condition: grafana.enabled
```

### Values File Structure

```yaml
# values-prod.yaml
replicaCount: 3

image:
  repository: gcr.io/my-project/mlops-sentiment
  tag: "v1.0.0"
  pullPolicy: IfNotPresent

resources:
  requests:
    cpu: 2000m
    memory: 4Gi
  limits:
    cpu: 4000m
    memory: 8Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10

monitoring:
  enabled: true
  prometheus:
    enabled: true
  grafana:
    enabled: true

vault:
  enabled: true
  address: "https://vault.example.com"
```

### Deployment Commands

#### Development
```bash
helm install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-dev \
  --create-namespace \
  --values helm/mlops-sentiment/values-dev.yaml
```

#### Staging
```bash
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-staging \
  --create-namespace \
  --values helm/mlops-sentiment/values-staging.yaml \
  --wait
```

#### Production
```bash
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-prod \
  --create-namespace \
  --values helm/mlops-sentiment/values-prod.yaml \
  --atomic \
  --wait \
  --timeout 10m
```

### Rollback

```bash
# List releases
helm list -n mlops-prod

# View history
helm history mlops-sentiment -n mlops-prod

# Rollback to previous version
helm rollback mlops-sentiment -n mlops-prod

# Rollback to specific revision
helm rollback mlops-sentiment 3 -n mlops-prod
```

## Testing Strategy

### Template Validation

```bash
# Render templates without deploying
helm template mlops-sentiment ./helm/mlops-sentiment \
  --values helm/mlops-sentiment/values-dev.yaml \
  > rendered.yaml

# Validate generated YAML
kubectl apply --dry-run=client -f rendered.yaml
```

### Linting

```bash
# Lint chart for issues
helm lint ./helm/mlops-sentiment

# Lint with specific values
helm lint ./helm/mlops-sentiment \
  --values helm/mlops-sentiment/values-prod.yaml
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Deploy to Staging
  run: |
    helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
      --namespace mlops-staging \
      --values helm/mlops-sentiment/values-staging.yaml \
      --set image.tag=${{ github.sha }} \
      --wait
```

## Chart Versioning

We follow semantic versioning:
- **Major**: Breaking changes to chart API
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes

Example: `0.1.0` → `0.2.0` (new feature) → `1.0.0` (breaking change)

## Dependency Management

```bash
# Update chart dependencies
helm dependency update ./helm/mlops-sentiment

# List dependencies
helm dependency list ./helm/mlops-sentiment
```

## Best Practices

1. **Named Templates**: Use `_helpers.tpl` for reusable templates
2. **Values Schema**: Document all values with comments
3. **NOTES.txt**: Provide post-install instructions
4. **Hooks**: Use pre/post-install hooks for initialization
5. **Resource Limits**: Always set requests and limits
6. **Labels**: Consistent labels for all resources
7. **Testing**: Test chart with all values files
8. **Documentation**: README.md in chart directory

## Monitoring

Track Helm deployments:
- Release history: `helm history`
- Release status: `helm status`
- Values used: `helm get values`
- Deployed manifests: `helm get manifest`

## Security Considerations

- **Secrets Management**: Use external secrets operators (Vault)
- **RBAC**: Limit Helm permissions
- **Values Encryption**: Encrypt sensitive values files
- **Chart Signing**: Sign charts for production
- **Namespace Isolation**: Deploy to separate namespaces

## Migration Path

1. **Phase 1** (Complete): Create initial Helm chart
2. **Phase 2** (Complete): Test in development
3. **Phase 3** (Complete): Deploy to staging
4. **Phase 4** (Complete): Production deployment
5. **Phase 5** (In Progress): Chart optimization and templating improvements
6. **Phase 6** (Future): Publish chart to Helm repository

## References

- [Helm Documentation](https://helm.sh/docs/)
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Chart Template Guide](https://helm.sh/docs/chart_template_guide/)
- [Helm Chart Structure](../../../helm/mlops-sentiment/)
- [Deployment Guide](../../setup/deployment-guide.md)

## Related ADRs

- [ADR 004: Use FastAPI as Web Framework](004-use-fastapi-as-web-framework.md)
- [ADR 006: Use HashiCorp Vault for Secrets](006-use-hashicorp-vault-for-secrets.md)

## Change History

- 2024-01-25: Initial decision
- 2024-02-10: Production deployment complete
- 2024-03-01: Added dependency management details
- 2025-10-30: Added to ADR repository
