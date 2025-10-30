# Environment-Specific Configurations

This document describes the configuration differences between development, staging, and production environments.

## Table of Contents

1. [Overview](#overview)
2. [Development Environment](#development-environment)
3. [Staging Environment](#staging-environment)
4. [Production Environment](#production-environment)
5. [Configuration Management](#configuration-management)
6. [Migration Between Environments](#migration-between-environments)

## Overview

KubeSentiment supports three primary environments:

- **Development (`dev`)**: Local development and testing
- **Staging (`staging`)**: Pre-production testing and validation
- **Production (`prod`)**: Live production deployment

Each environment has specific configurations optimized for its purpose.

## Development Environment

### Purpose
- Local development
- Feature testing
- Debugging

### Helm Values File
`helm/mlops-sentiment/values-dev.yaml`

### Key Configurations

#### Application Settings
```yaml
replicaCount: 1  # Single replica for development

image:
  repository: mlops-sentiment
  tag: dev
  pullPolicy: IfNotPresent

deployment:
  env:
    MLOPS_DEBUG: "true"  # Enable debug mode
    MLOPS_LOG_LEVEL: "DEBUG"  # Verbose logging
    MLOPS_ENABLE_METRICS: "true"
    MLOPS_ENABLE_PROFILING: "true"  # Performance profiling
```

#### Resource Limits
```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 1000m
    memory: 2Gi
```

#### Model Configuration
```yaml
model:
  name: "distilbert-base-uncased-finetuned-sst-2-english"
  backend: "pytorch"  # Faster iteration for development
  cacheEnabled: false  # Disable caching for testing
```

#### Monitoring
```yaml
monitoring:
  enabled: true
  prometheus:
    enabled: true
  grafana:
    enabled: true
    adminPassword: "admin123"  # Simple password for dev
```

#### Autoscaling
```yaml
autoscaling:
  enabled: false  # No autoscaling in dev
```

#### API Configuration
```yaml
api:
  versionPrefix: ""  # No /api/v1 prefix in debug mode
  rateLimiting:
    enabled: false  # No rate limiting in dev
  authentication:
    enabled: false  # No auth required in dev
```

### Deployment Command

```bash
helm install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-dev \
  --create-namespace \
  --values helm/mlops-sentiment/values-dev.yaml
```

### Accessing Services

```bash
# Port forward to access locally
kubectl port-forward -n mlops-dev svc/mlops-sentiment 8000:80

# Test endpoint (no /api/v1 prefix in dev)
curl http://localhost:8000/predict -d '{"text": "test"}'
```

---

## Staging Environment

### Purpose
- Pre-production testing
- Integration testing
- Performance validation
- User acceptance testing (UAT)

### Helm Values File
`helm/mlops-sentiment/values-staging.yaml`

### Key Configurations

#### Application Settings
```yaml
replicaCount: 2  # Minimum 2 replicas for availability

image:
  repository: gcr.io/my-project/mlops-sentiment
  tag: staging-latest
  pullPolicy: Always  # Always pull latest staging image

deployment:
  env:
    MLOPS_DEBUG: "false"
    MLOPS_LOG_LEVEL: "INFO"
    MLOPS_ENABLE_METRICS: "true"
    MLOPS_ENABLE_PROFILING: "false"
```

#### Resource Limits
```yaml
resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 2000m
    memory: 4Gi
```

#### Model Configuration
```yaml
model:
  name: "distilbert-base-uncased-finetuned-sst-2-english"
  backend: "onnx"  # Optimized runtime
  cacheEnabled: true
  cacheTTL: 3600  # 1 hour

modelPersistence:
  enabled: true
  size: 5Gi
  storageClassName: "standard"
```

#### Monitoring
```yaml
monitoring:
  enabled: true
  prometheus:
    enabled: true
    retention: 15d
  grafana:
    enabled: true
    adminPassword: "${GRAFANA_ADMIN_PASSWORD}"  # From secret
  alerts:
    enabled: true
    slackWebhook: "${SLACK_WEBHOOK_STAGING}"
```

#### Autoscaling
```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

#### API Configuration
```yaml
api:
  versionPrefix: "/api/v1"
  rateLimiting:
    enabled: true
    requestsPerMinute: 100
  authentication:
    enabled: true
    type: "api-key"
```

#### Security
```yaml
security:
  podSecurityContext:
    runAsNonRoot: true
    runAsUser: 1000
  networkPolicy:
    enabled: true
    allowedNamespaces:
      - monitoring
      - ingress
```

### Deployment Command

```bash
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-staging \
  --create-namespace \
  --values helm/mlops-sentiment/values-staging.yaml \
  --set deployment.env.GRAFANA_ADMIN_PASSWORD="${GRAFANA_PASSWORD}" \
  --wait
```

### Accessing Services

```bash
# Via Ingress (configure DNS)
curl https://staging-api.example.com/api/v1/predict \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"text": "test"}'
```

---

## Production Environment

### Purpose
- Live production traffic
- Maximum reliability
- Optimal performance
- Security hardened

### Helm Values File
`helm/mlops-sentiment/values-prod.yaml`

### Key Configurations

#### Application Settings
```yaml
replicaCount: 3  # Minimum 3 replicas for HA

image:
  repository: gcr.io/my-project/mlops-sentiment
  tag: "v1.0.0"  # Specific version tag
  pullPolicy: IfNotPresent

deployment:
  env:
    MLOPS_DEBUG: "false"
    MLOPS_LOG_LEVEL: "WARNING"  # Less verbose
    MLOPS_ENABLE_METRICS: "true"
    MLOPS_ENABLE_PROFILING: "false"
    MLOPS_WARMUP_ENABLED: "true"  # Warm up models
```

#### Resource Limits
```yaml
resources:
  requests:
    cpu: 2000m
    memory: 4Gi
  limits:
    cpu: 4000m
    memory: 8Gi
```

#### Model Configuration
```yaml
model:
  name: "distilbert-base-uncased-finetuned-sst-2-english"
  backend: "onnx"
  optimized: true
  quantized: false  # Full precision for accuracy
  cacheEnabled: true
  cacheTTL: 7200  # 2 hours

modelPersistence:
  enabled: true
  size: 10Gi
  storageClassName: "fast-ssd"  # High-performance storage
  backupEnabled: true
```

#### Monitoring
```yaml
monitoring:
  enabled: true
  prometheus:
    enabled: true
    retention: 30d
    storageSize: 50Gi
  grafana:
    enabled: true
    adminPassword: "${GRAFANA_ADMIN_PASSWORD_PROD}"
    ingress:
      enabled: true
      hostname: "grafana.example.com"
      tls: true
  alerts:
    enabled: true
    slackWebhook: "${SLACK_WEBHOOK_PROD}"
    pagerdutyKey: "${PAGERDUTY_SERVICE_KEY}"
    severity: "critical"
```

#### Autoscaling
```yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 60  # More aggressive scaling
  targetMemoryUtilizationPercentage: 70
  customMetrics:
    - type: Pods
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

#### API Configuration
```yaml
api:
  versionPrefix: "/api/v1"
  rateLimiting:
    enabled: true
    requestsPerMinute: 1000
    burstSize: 2000
  authentication:
    enabled: true
    type: "jwt"
    tokenExpiry: "1h"
  cors:
    enabled: true
    allowedOrigins:
      - "https://app.example.com"
```

#### Security
```yaml
security:
  podSecurityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containerSecurityContext:
    allowPrivilegeEscalation: false
    capabilities:
      drop:
        - ALL
  networkPolicy:
    enabled: true
    policyTypes:
      - Ingress
      - Egress
    allowedNamespaces:
      - monitoring
      - ingress
    egressRules:
      - to:
          - namespaceSelector:
              matchLabels:
                name: kube-system
        ports:
          - protocol: TCP
            port: 53  # DNS
```

#### Vault Integration
```yaml
vault:
  enabled: true
  address: "https://vault.example.com"
  role: "mlops-sentiment-prod"
  namespace: "mlops"
  secretPath: "mlops-sentiment/prod"
```

#### Backup and Disaster Recovery
```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2 AM
  retention: 30  # Keep 30 days
  destination: "s3://prod-backups/mlops-sentiment"
```

### Deployment Command

```bash
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-prod \
  --create-namespace \
  --values helm/mlops-sentiment/values-prod.yaml \
  --set deployment.env.GRAFANA_ADMIN_PASSWORD="${GRAFANA_PASSWORD_PROD}" \
  --set deployment.env.SLACK_WEBHOOK_PROD="${SLACK_WEBHOOK}" \
  --set deployment.env.PAGERDUTY_SERVICE_KEY="${PAGERDUTY_KEY}" \
  --atomic \
  --wait \
  --timeout 10m
```

### Accessing Services

```bash
# Via production domain
curl https://api.example.com/api/v1/predict \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d '{"text": "production traffic"}'
```

---

## Configuration Management

### Environment Variables

#### Loading from Files

**Development:**
```bash
export $(cat .env.dev | xargs)
```

**Staging/Production:**
```bash
# Use secret management system
kubectl create secret generic mlops-sentiment-secrets \
  --from-env-file=.env.prod \
  -n mlops-prod
```

#### Required Variables by Environment

| Variable | Dev | Staging | Prod | Description |
|----------|-----|---------|------|-------------|
| `MLOPS_DEBUG` | `true` | `false` | `false` | Debug mode |
| `MLOPS_LOG_LEVEL` | `DEBUG` | `INFO` | `WARNING` | Log verbosity |
| `MLOPS_API_KEY` | Optional | Required | Required | API authentication |
| `MLOPS_VAULT_ENABLED` | `false` | `true` | `true` | HashiCorp Vault |
| `MLOPS_REDIS_ENABLED` | `false` | `true` | `true` | Redis caching |
| `MLOPS_KAFKA_ENABLED` | `false` | Optional | `true` | Kafka streaming |

### Secrets Management

#### Development
- Local `.env` files (not committed to git)
- kubectl secrets for testing

#### Staging/Production
- HashiCorp Vault (primary)
- Kubernetes Secrets (encrypted at rest)
- External secret managers (AWS Secrets Manager, GCP Secret Manager)

### ConfigMaps

Each environment has its own ConfigMap:

```bash
# Create environment-specific ConfigMap
kubectl create configmap mlops-sentiment-config \
  --from-file=config-prod.yaml \
  -n mlops-prod
```

---

## Migration Between Environments

### Promoting from Dev to Staging

1. **Run Tests**
   ```bash
   pytest tests/
   ```

2. **Build and Tag Image**
   ```bash
   docker build -t mlops-sentiment:staging-v1.2.0 .
   docker push gcr.io/my-project/mlops-sentiment:staging-v1.2.0
   ```

3. **Deploy to Staging**
   ```bash
   helm upgrade mlops-sentiment ./helm/mlops-sentiment \
     --namespace mlops-staging \
     --values helm/mlops-sentiment/values-staging.yaml \
     --set image.tag=staging-v1.2.0 \
     --wait
   ```

4. **Run Integration Tests**
   ```bash
   ./tests/integration/run_staging_tests.sh
   ```

### Promoting from Staging to Production

1. **Review Staging Metrics**
   - Check Grafana dashboards
   - Review error rates
   - Validate performance

2. **Create Release**
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```

3. **Build Production Image**
   ```bash
   docker build -t mlops-sentiment:v1.2.0 .
   docker push gcr.io/my-project/mlops-sentiment:v1.2.0
   ```

4. **Deploy with Canary**
   ```bash
   # Deploy 10% traffic first
   helm upgrade mlops-sentiment ./helm/mlops-sentiment \
     --namespace mlops-prod \
     --values helm/mlops-sentiment/values-prod.yaml \
     --set image.tag=v1.2.0 \
     --set deployment.canary.enabled=true \
     --set deployment.canary.weight=10 \
     --wait
   ```

5. **Monitor and Validate**
   - Watch error rates
   - Check latency metrics
   - Verify business metrics

6. **Full Rollout**
   ```bash
   helm upgrade mlops-sentiment ./helm/mlops-sentiment \
     --namespace mlops-prod \
     --values helm/mlops-sentiment/values-prod.yaml \
     --set image.tag=v1.2.0 \
     --set deployment.canary.enabled=false \
     --wait
   ```

### Rollback Procedure

```bash
# Quick rollback to previous version
helm rollback mlops-sentiment -n mlops-prod

# Or rollback to specific revision
helm rollback mlops-sentiment 3 -n mlops-prod
```

---

## Environment Comparison Matrix

| Feature | Development | Staging | Production |
|---------|-------------|---------|------------|
| Replicas | 1 | 2 | 3-10 |
| CPU Request | 500m | 1000m | 2000m |
| Memory Request | 1Gi | 2Gi | 4Gi |
| Debug Mode | ✅ | ❌ | ❌ |
| API Versioning | Optional | Required | Required |
| Authentication | ❌ | ✅ | ✅ |
| Rate Limiting | ❌ | ✅ | ✅ |
| Monitoring | Basic | Full | Full + Alerting |
| Autoscaling | ❌ | ✅ | ✅ |
| Vault Integration | ❌ | ✅ | ✅ |
| Redis Caching | ❌ | ✅ | ✅ |
| Model Optimization | ❌ | ✅ | ✅ |
| Backups | ❌ | Optional | ✅ |
| High Availability | ❌ | ✅ | ✅ |

---

## Best Practices

1. **Never use production credentials in lower environments**
2. **Test configuration changes in dev/staging first**
3. **Use GitOps for production deployments**
4. **Monitor resource usage and adjust limits**
5. **Regular security audits of configurations**
6. **Document environment-specific quirks**
7. **Automate environment setup with IaC**
8. **Keep staging as close to production as possible**

---

## References

- [Deployment Guide](setup/deployment-guide.md)
- [Architecture Documentation](architecture.md)
- [Security Best Practices](security.md)
- [Helm Values Reference](../helm/mlops-sentiment/README.md)

---

**Last Updated:** 2025-10-30
**Maintained By:** KubeSentiment Team
