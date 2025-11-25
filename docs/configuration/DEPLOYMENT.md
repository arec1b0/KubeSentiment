# Deployment Configuration

Environment-specific configurations for development, staging, and production deployments.

## Table of Contents

1. [Overview](#overview)
2. [Development Environment](#development-environment)
3. [Staging Environment](#staging-environment)
4. [Production Environment](#production-environment)
5. [Migration Between Environments](#migration-between-environments)
6. [Secrets Management](#secrets-management)
7. [Best Practices](#best-practices)

---

## Overview

KubeSentiment supports three primary deployment environments:

| Environment | Use Case | Profile | Services | Replicas | Autoscaling |
|------------|----------|---------|----------|----------|-------------|
| **Development** | Local development and feature testing | `development` | Optional (Redis, Kafka disabled by default) | 1 | No |
| **Staging** | Pre-production testing and validation | `staging` | All enabled (except Data Lake) | 2 | Yes (2-5) |
| **Production** | Live production traffic | `production` | All enabled (Redis, Kafka, Vault, Data Lake) | 3+ | Yes (3-10) |

Each environment has specific Kubernetes manifests, Helm values, and environment variables to optimize for its purpose.

---

## Development Environment

### Purpose

Local development, feature testing, debugging, and rapid iteration.

### Configuration Profile

```bash
export MLOPS_PROFILE=development
```

### Helm Values File

`helm/mlops-sentiment/values-dev.yaml`

**Key Configuration:**
```yaml
replicaCount: 1

image:
  tag: dev
  pullPolicy: IfNotPresent

deployment:
  env:
    MLOPS_DEBUG: "true"
    MLOPS_LOG_LEVEL: "DEBUG"
    MLOPS_ENABLE_METRICS: "true"
    MLOPS_ENABLE_PROFILING: "true"

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 1000m
    memory: 2Gi

model:
  backend: "pytorch"  # Faster iteration
  cacheEnabled: false  # Disable for testing

monitoring:
  prometheus:
    enabled: true
  grafana:
    enabled: true

autoscaling:
  enabled: false

api:
  versionPrefix: ""  # No /api/v1 prefix in debug mode
  rateLimiting:
    enabled: false
  authentication:
    enabled: false
```

### Deployment Commands

**Create namespace:**
```bash
kubectl create namespace mlops-dev
```

**Install:**
```bash
helm install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-dev \
  --values helm/mlops-sentiment/values-dev.yaml
```

**Upgrade:**
```bash
helm upgrade mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-dev \
  --values helm/mlops-sentiment/values-dev.yaml
```

### Accessing Services

```bash
# Port forward to local machine
kubectl port-forward -n mlops-dev svc/mlops-sentiment 8000:80

# Test the service
curl http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This is great!"}'

# View API docs
open http://localhost:8000/docs

# View Grafana dashboards
kubectl port-forward -n mlops-dev svc/grafana 3000:80
open http://localhost:3000
```

### Local Docker Compose Setup

For complete dev environment with services:

```bash
docker-compose up
```

See `docs/configuration/examples/docker-compose.yml`

---

## Staging Environment

### Purpose

Pre-production testing, integration testing, performance validation, user acceptance testing (UAT).

### Configuration Profile

```bash
export MLOPS_PROFILE=staging
```

### Helm Values File

`helm/mlops-sentiment/values-staging.yaml`

**Key Configuration:**
```yaml
replicaCount: 2  # Minimum 2 for availability

image:
  repository: gcr.io/my-project/mlops-sentiment
  tag: staging-latest
  pullPolicy: Always

deployment:
  env:
    MLOPS_DEBUG: "false"
    MLOPS_LOG_LEVEL: "INFO"
    MLOPS_ENABLE_METRICS: "true"
    MLOPS_ENABLE_PROFILING: "false"

resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 2000m
    memory: 4Gi

model:
  backend: "onnx"
  cacheEnabled: true
  cacheTTL: 3600

modelPersistence:
  enabled: true
  size: 5Gi
  storageClassName: "standard"

monitoring:
  enabled: true
  prometheus:
    enabled: true
    retention: 15d
  grafana:
    enabled: true
  alerts:
    enabled: true
    slackWebhook: "${SLACK_WEBHOOK_STAGING}"

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 70

api:
  versionPrefix: "/api/v1"
  rateLimiting:
    enabled: true
    requestsPerMinute: 100
  authentication:
    enabled: true
    type: "api-key"

security:
  podSecurityContext:
    runAsNonRoot: true
    runAsUser: 1000
  networkPolicy:
    enabled: true
```

### Environment Variables

Create ConfigMap and Secret:

```bash
# ConfigMap for non-sensitive settings
kubectl create configmap mlops-sentiment-staging \
  --from-literal=MLOPS_PROFILE=staging \
  --from-literal=MLOPS_REDIS_HOST=redis-staging \
  --from-literal=MLOPS_VAULT_ADDR=https://vault-staging.example.com \
  -n mlops-staging

# Secret for sensitive settings
kubectl create secret generic mlops-sentiment-secrets \
  --from-literal=MLOPS_VAULT_TOKEN=<token> \
  --from-literal=MLOPS_API_KEY=<api-key> \
  -n mlops-staging
```

### Deployment Commands

**Create namespace:**
```bash
kubectl create namespace mlops-staging
```

**Install:**
```bash
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-staging \
  --create-namespace \
  --values helm/mlops-sentiment/values-staging.yaml \
  --wait
```

**Upgrade with monitoring:**
```bash
helm upgrade mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-staging \
  --values helm/mlops-sentiment/values-staging.yaml \
  --set deployment.env.SLACK_WEBHOOK_STAGING="${SLACK_WEBHOOK}" \
  --wait
```

### Accessing Services

```bash
# Via Ingress (requires DNS configuration)
curl https://staging-api.example.com/api/v1/health \
  -H "X-API-Key: ${API_KEY}"

# Or port-forward for testing
kubectl port-forward -n mlops-staging svc/mlops-sentiment 8000:80

# View logs
kubectl logs -n mlops-staging -l app=mlops-sentiment -f

# View metrics (Prometheus)
kubectl port-forward -n mlops-staging svc/prometheus 9090:9090
open http://localhost:9090

# View dashboards (Grafana)
kubectl port-forward -n mlops-staging svc/grafana 3000:80
open http://localhost:3000
```

---

## Production Environment

### Purpose

Live production traffic, maximum reliability, optimal performance, security hardened.

### Configuration Profile

```bash
export MLOPS_PROFILE=production
```

### Helm Values File

`helm/mlops-sentiment/values-prod.yaml`

**Key Configuration:**
```yaml
replicaCount: 3  # Minimum 3 for HA

image:
  repository: gcr.io/my-project/mlops-sentiment
  tag: "v1.0.0"  # Specific version tag
  pullPolicy: IfNotPresent

deployment:
  env:
    MLOPS_DEBUG: "false"
    MLOPS_LOG_LEVEL: "WARNING"
    MLOPS_ENABLE_METRICS: "true"
    MLOPS_ENABLE_PROFILING: "false"
    MLOPS_WARMUP_ENABLED: "true"

resources:
  requests:
    cpu: 2000m
    memory: 4Gi
  limits:
    cpu: 4000m
    memory: 8Gi

model:
  backend: "onnx"
  optimized: true
  quantized: false
  cacheEnabled: true
  cacheTTL: 7200

modelPersistence:
  enabled: true
  size: 10Gi
  storageClassName: "fast-ssd"
  backupEnabled: true

monitoring:
  enabled: true
  prometheus:
    enabled: true
    retention: 30d
    storageSize: 50Gi
  grafana:
    enabled: true
    adminPassword: "${GRAFANA_ADMIN_PASSWORD_PROD}"
  alerts:
    enabled: true
    slackWebhook: "${SLACK_WEBHOOK_PROD}"
    pagerdutyKey: "${PAGERDUTY_SERVICE_KEY}"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 60
  customMetrics:
    - type: Pods
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"

api:
  versionPrefix: "/api/v1"
  rateLimiting:
    enabled: true
    requestsPerMinute: 1000
    burstSize: 2000
  authentication:
    enabled: true
    type: "jwt"
  cors:
    enabled: true
    allowedOrigins:
      - "https://app.example.com"

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

vault:
  enabled: true
  address: "https://vault.example.com"
  role: "mlops-sentiment-prod"

backup:
  enabled: true
  schedule: "0 2 * * *"
  retention: 30
  destination: "s3://prod-backups/mlops-sentiment"
```

### Environment Variables

**ConfigMap (non-sensitive):**
```bash
kubectl create configmap mlops-sentiment-prod \
  --from-literal=MLOPS_PROFILE=production \
  --from-literal=MLOPS_ENVIRONMENT=production \
  --from-literal=MLOPS_LOG_LEVEL=WARNING \
  --from-literal=MLOPS_REDIS_HOST=redis-prod.production.svc.cluster.local \
  --from-literal=MLOPS_KAFKA_BOOTSTRAP_SERVERS=kafka-prod.production.svc.cluster.local:9092 \
  --from-literal=MLOPS_VAULT_ADDR=https://vault.example.com \
  --from-literal=MLOPS_MLFLOW_TRACKING_URI=https://mlflow.example.com \
  -n mlops-prod
```

**Secret (sensitive):**
```bash
kubectl create secret generic mlops-sentiment-prod-secrets \
  --from-literal=MLOPS_API_KEY=${API_KEY} \
  --from-literal=MLOPS_VAULT_TOKEN=${VAULT_TOKEN} \
  --from-literal=MLOPS_REDIS_PASSWORD=${REDIS_PASSWORD} \
  --from-literal=MLOPS_SLACK_WEBHOOK_PROD=${SLACK_WEBHOOK} \
  -n mlops-prod
```

### Deployment Commands

**Create namespace:**
```bash
kubectl create namespace mlops-prod
```

**Install (initial):**
```bash
helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-prod \
  --create-namespace \
  --values helm/mlops-sentiment/values-prod.yaml \
  --atomic \
  --wait \
  --timeout 10m
```

**Upgrade (with validation):**
```bash
# Dry run first
helm upgrade mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-prod \
  --values helm/mlops-sentiment/values-prod.yaml \
  --dry-run --debug

# Actual upgrade
helm upgrade mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-prod \
  --values helm/mlops-sentiment/values-prod.yaml \
  --atomic \
  --wait \
  --timeout 10m
```

### Accessing Services

```bash
# Via production domain
curl https://api.example.com/api/v1/predict \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"text": "production traffic"}'

# View logs (tail recent errors)
kubectl logs -n mlops-prod -l app=mlops-sentiment -f --tail=100

# Check pod status
kubectl get pods -n mlops-prod -o wide

# Describe pod for issues
kubectl describe pod -n mlops-prod -l app=mlops-sentiment

# View metrics
kubectl port-forward -n mlops-prod svc/prometheus 9090:9090

# View dashboards
kubectl port-forward -n mlops-prod svc/grafana 3000:80
```

---

## Migration Between Environments

### Promoting from Dev to Staging

1. **Run Tests**
   ```bash
   pytest tests/
   pytest tests/integration/
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

5. **Performance Testing**
   ```bash
   ./benchmarking/run_staging_benchmarks.sh
   ```

---

### Promoting from Staging to Production

1. **Review Staging Metrics**
   - Check Grafana dashboards for errors/latency
   - Review application logs
   - Validate business metrics
   - Performance baselines met

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

4. **Deploy with Canary (10%)**
   ```bash
   helm upgrade mlops-sentiment ./helm/mlops-sentiment \
     --namespace mlops-prod \
     --values helm/mlops-sentiment/values-prod.yaml \
     --set image.tag=v1.2.0 \
     --set deployment.canary.enabled=true \
     --set deployment.canary.weight=10 \
     --wait
   ```

5. **Monitor Canary (30 minutes)**
   - Watch error rates
   - Check latency metrics
   - Verify business metrics
   - No incidents?

6. **Canary to 50%**
   ```bash
   helm upgrade mlops-sentiment ./helm/mlops-sentiment \
     --namespace mlops-prod \
     --values helm/mlops-sentiment/values-prod.yaml \
     --set image.tag=v1.2.0 \
     --set deployment.canary.weight=50 \
     --wait
   ```

7. **Monitor 50% (30 minutes)**
   - Same monitoring as step 5
   - No issues?

8. **Full Rollout (100%)**
   ```bash
   helm upgrade mlops-sentiment ./helm/mlops-sentiment \
     --namespace mlops-prod \
     --values helm/mlops-sentiment/values-prod.yaml \
     --set image.tag=v1.2.0 \
     --set deployment.canary.enabled=false \
     --wait
   ```

9. **Verify Deployment**
   ```bash
   # Check all pods are running
   kubectl get pods -n mlops-prod -l app=mlops-sentiment

   # Check version
   curl https://api.example.com/api/v1/health
   ```

---

### Rollback Procedure

**Quick rollback to previous version:**
```bash
helm rollback mlops-sentiment -n mlops-prod
```

**Rollback to specific revision:**
```bash
# List revisions
helm history mlops-sentiment -n mlops-prod

# Rollback to revision 3
helm rollback mlops-sentiment 3 -n mlops-prod
```

**Manual rollback:**
```bash
# Revert to previous image
helm upgrade mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-prod \
  --values helm/mlops-sentiment/values-prod.yaml \
  --set image.tag=v1.1.0 \
  --wait
```

---

## Secrets Management

### Development

Use `.env` files locally:
```bash
cp .env.development.template .env
# Edit .env with local values
export $(cat .env | xargs)
```

### Staging/Production

Use Kubernetes Secrets:

```bash
# Create secret from file
kubectl create secret generic mlops-sentiment-secrets \
  --from-env-file=.env.prod \
  -n mlops-prod

# Create secret from literal values
kubectl create secret generic mlops-sentiment-secrets \
  --from-literal=MLOPS_VAULT_TOKEN=${VAULT_TOKEN} \
  --from-literal=MLOPS_API_KEY=${API_KEY} \
  -n mlops-prod

# Reference in Helm values
deployment:
  envFrom:
    - secretRef:
        name: mlops-sentiment-secrets
```

### Using Vault

For production, use HashiCorp Vault:

```yaml
vault:
  enabled: true
  address: "https://vault.example.com"
  role: "mlops-sentiment-prod"
  namespace: "mlops"
  secretPath: "mlops-sentiment/prod"
```

Then set environment variable:
```bash
export MLOPS_VAULT_ENABLED=true
export MLOPS_VAULT_ADDR=https://vault.example.com
```

---

## Best Practices

1. **Always use profiles**
   - `MLOPS_PROFILE=development` for dev
   - `MLOPS_PROFILE=staging` for staging
   - `MLOPS_PROFILE=production` for prod

2. **Never use production credentials in lower environments**
   - Separate API keys for each environment
   - Separate database credentials
   - Separate external service endpoints

3. **Test configuration changes in dev/staging first**
   - Apply in dev
   - Verify behavior
   - Promote to staging
   - Test thoroughly
   - Then production

4. **Use GitOps for production deployments**
   - Store Helm values in git
   - Use CI/CD for deployments
   - Track all changes
   - Enable rollbacks

5. **Monitor resource usage**
   - Track CPU/memory per environment
   - Adjust limits as needed
   - Set up alerts for overuse

6. **Keep staging close to production**
   - Use same profile (staging)
   - Same services enabled
   - Same monitoring/alerting
   - Only different endpoints

7. **Document environment-specific quirks**
   - Why certain settings differ
   - Any known issues per environment
   - Special procedures needed

8. **Regular security audits**
   - Review secrets management
   - Check RBAC policies
   - Verify network policies
   - Update security settings

---

## Related Documentation

- **[Quick Start](QUICK_START.md)** - Getting started
- **[Profiles](PROFILES.md)** - Profile-based defaults
- **[Environment Variables](ENVIRONMENT_VARIABLES.md)** - Complete settings reference
- **[Architecture](ARCHITECTURE.md)** - Configuration design
- **[examples/](examples/)** - Copy-paste ready configurations

---

**Last Updated:** 2025-11-25
**Maintained By:** KubeSentiment Team
