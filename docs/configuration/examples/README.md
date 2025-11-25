# Configuration Examples

Copy-paste ready configuration files for common scenarios.

## Quick Start

### For Local Development

```bash
# Copy local configuration
cp .env.local .env

# Edit if needed
nano .env

# Run application
export $(cat .env | xargs)
python -m uvicorn app.main:app --reload
```

### With Docker Compose

```bash
# Start all services (dev environment)
docker-compose -f docker-compose-dev.yml up

# Test the API
curl http://localhost:8000/api/v1/health

# View logs
docker-compose -f docker-compose-dev.yml logs -f api

# Stop services
docker-compose -f docker-compose-dev.yml down
```

### With Kubernetes

```bash
# Deploy development environment
kubectl apply -f kubernetes-dev.yaml

# Port forward to local machine
kubectl port-forward -n mlops-dev svc/mlops-sentiment 8000:80

# Test the API
curl http://localhost:8000/api/v1/health

# View logs
kubectl logs -n mlops-dev -l app=mlops-sentiment -f

# Clean up
kubectl delete -f kubernetes-dev.yaml
```

---

## Available Examples

### Environment Configuration Files

| File | Purpose | Use Case |
|------|---------|----------|
| `.env.local` | Minimal local setup | Quick local testing without services |
| `.env.development` | Development with services | Feature development with Redis/Kafka |

### Docker Compose

| File | Purpose | Services |
|------|---------|----------|
| `docker-compose-dev.yml` | Complete dev environment | API + Redis + Kafka + Prometheus + Grafana |

### Kubernetes

| File | Purpose | Replicas | Services | Autoscaling |
|------|---------|----------|----------|-------------|
| `kubernetes-dev.yaml` | Development environment | 1 | Redis included | No |
| `kubernetes-staging.yaml` | Staging environment | 2-5 | Redis (external) | Yes (2-5) |
| `kubernetes-prod.yaml` | Production environment | 3-10 | All (external) | Yes (3-10) |

---

## Environment Configuration Files

### .env.local

**Use case:** Quick testing on your laptop without any external services

**Profile:** `development` (local variant)

**Services enabled:** None

**When to use:**
- Initial development
- Running unit tests
- Verifying code compiles
- No dependencies needed

**Setup:**
```bash
cp .env.local .env
export $(cat .env | xargs)
python -m uvicorn app.main:app --reload
```

### .env.development

**Use case:** Development with optional services (Redis, Kafka)

**Profile:** `development`

**Services enabled:** Optional (disabled by default, can enable individually)

**When to use:**
- Feature development
- Integration testing
- Testing with Redis/Kafka

**Setup:**
```bash
cp .env.development .env

# Edit to enable services if needed
# MLOPS_REDIS_ENABLED=true
# MLOPS_KAFKA_ENABLED=true

export $(cat .env | xargs)
python -m uvicorn app.main:app --reload
```

---

## Docker Compose Examples

### docker-compose-dev.yml

**Services:**
- mlops-sentiment (API)
- redis (Cache)
- kafka (Message streaming)
- zookeeper (Kafka dependency)
- prometheus (Metrics)
- grafana (Dashboards)

**Usage:**
```bash
# Start all services
docker-compose -f docker-compose-dev.yml up

# Build and start
docker-compose -f docker-compose-dev.yml up --build

# Run in background
docker-compose -f docker-compose-dev.yml up -d

# View logs
docker-compose -f docker-compose-dev.yml logs -f api

# Stop services
docker-compose -f docker-compose-dev.yml down

# Clean up volumes
docker-compose -f docker-compose-dev.yml down -v
```

**Access Services:**
- API: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Redis: localhost:6379
- Kafka: localhost:9092

---

## Kubernetes Examples

### kubernetes-dev.yaml

**Use case:** Development environment in Kubernetes

**Configuration:**
- 1 replica
- Debug mode enabled
- Redis included
- Resource limits: 500m CPU / 1Gi memory (request), 1000m CPU / 2Gi memory (limit)
- Service type: ClusterIP

**Deployment:**
```bash
# Apply configuration
kubectl apply -f kubernetes-dev.yaml

# Verify deployment
kubectl get pods -n mlops-dev
kubectl get svc -n mlops-dev

# Port forward
kubectl port-forward -n mlops-dev svc/mlops-sentiment 8000:80

# Test
curl http://localhost:8000/api/v1/health

# View logs
kubectl logs -n mlops-dev -l app=mlops-sentiment -f

# Clean up
kubectl delete -f kubernetes-dev.yaml
```

### kubernetes-staging.yaml

**Use case:** Pre-production testing and validation

**Configuration:**
- 2-5 replicas (with autoscaling)
- Production-like configuration
- Redis enabled (external)
- Vault enabled
- All MLOps features enabled
- Resource limits: 1000m CPU / 2Gi memory (request), 2000m CPU / 4Gi memory (limit)
- Service type: LoadBalancer
- Pod Disruption Budget: minimum 1 available

**Prerequisites:**
Update the YAML with your endpoints:
```bash
# Edit kubernetes-staging.yaml and replace:
# - gcr.io/my-project/mlops-sentiment:staging-latest → your image
# - https://vault-staging.example.com → your Vault address
# - https://mlflow-staging.example.com → your MLflow address
# - redis-staging → your Redis host
```

**Deployment:**
```bash
# Edit configuration
nano kubernetes-staging.yaml

# Apply configuration
kubectl apply -f kubernetes-staging.yaml

# Verify deployment
kubectl get pods -n mlops-staging
kubectl get svc -n mlops-staging

# Check autoscaling
kubectl get hpa -n mlops-staging

# View logs
kubectl logs -n mlops-staging -l app=mlops-sentiment -f

# Monitor resource usage
kubectl top pods -n mlops-staging
```

### kubernetes-prod.yaml

**Use case:** Production deployment

**Configuration:**
- 3-10 replicas (with autoscaling)
- Production-optimized settings
- All services enabled (external)
- Security hardened (non-root, readonly filesystem, network policies)
- Resource limits: 2000m CPU / 4Gi memory (request), 4000m CPU / 8Gi memory (limit)
- Service type: ClusterIP
- Pod Anti-Affinity: prefer different nodes
- Pod Disruption Budget: minimum 2 available
- Network Policy: ingress/egress rules
- Health checks: liveness + readiness probes

**Prerequisites:**
1. **Update image repository:**
   ```bash
   # Replace gcr.io/my-project with your registry
   ```

2. **Create secrets:**
   ```bash
   kubectl create secret generic mlops-sentiment-secrets \
     --from-literal=MLOPS_API_KEY=<your-api-key> \
     --from-literal=MLOPS_VAULT_TOKEN=<your-vault-token> \
     --from-literal=MLOPS_REDIS_PASSWORD=<your-redis-password> \
     -n mlops-prod
   ```

3. **Update configuration:**
   - Update Redis host (redis-prod.mlops-prod.svc.cluster.local)
   - Update Kafka bootstrap servers
   - Update Vault address
   - Update MLflow URI
   - Update image tag to specific version

4. **Install ingress controller** (if using Ingress):
   ```bash
   kubectl install ingress-nginx/ingress-nginx
   ```

**Deployment:**
```bash
# Edit and customize
nano kubernetes-prod.yaml

# Dry run first
kubectl apply -f kubernetes-prod.yaml --dry-run=client

# Apply configuration
kubectl apply -f kubernetes-prod.yaml

# Verify all components
kubectl get pods,svc,hpa -n mlops-prod

# Check security context
kubectl get pod -n mlops-prod -l app=mlops-sentiment -o jsonpath='{.items[0].spec.securityContext}'

# Monitor
kubectl top pods -n mlops-prod
kubectl logs -n mlops-prod -l app=mlops-sentiment -f

# Update to new version
kubectl set image deployment/mlops-sentiment mlops-sentiment=gcr.io/my-project/mlops-sentiment:v1.1.0 -n mlops-prod

# Check rollout status
kubectl rollout status deployment/mlops-sentiment -n mlops-prod

# Rollback if needed
kubectl rollout undo deployment/mlops-sentiment -n mlops-prod
```

---

## Customization Guide

### Changing Environment

Edit the respective `.env` file:

```bash
# Change profile
MLOPS_PROFILE=staging

# Change model
MLOPS_MODEL_NAME=my-custom-model

# Enable services
MLOPS_REDIS_ENABLED=true
MLOPS_KAFKA_ENABLED=true

# Change resource limits
MLOPS_WORKERS=8
```

### Changing Docker Compose Services

Edit `docker-compose-dev.yml`:

```yaml
services:
  api:
    environment:
      - MLOPS_REDIS_HOST=redis  # Change Redis host
      - MLOPS_KAFKA_BOOTSTRAP_SERVERS=kafka:9092  # Change Kafka
```

### Changing Kubernetes Configuration

Edit the respective Kubernetes YAML:

```yaml
# Change replicas
spec:
  replicas: 3

# Change image
containers:
- image: my-registry/mlops-sentiment:v1.0.0

# Change resource limits
resources:
  requests:
    cpu: 2000m
    memory: 4Gi
```

---

## Troubleshooting

### Docker Compose Issues

**Containers not starting:**
```bash
# Check logs
docker-compose -f docker-compose-dev.yml logs api

# Restart services
docker-compose -f docker-compose-dev.yml restart

# Clean up and start fresh
docker-compose -f docker-compose-dev.yml down -v
docker-compose -f docker-compose-dev.yml up --build
```

### Kubernetes Issues

**Pods not starting:**
```bash
# Check pod status
kubectl describe pod -n mlops-dev <pod-name>

# Check logs
kubectl logs -n mlops-dev <pod-name>

# Check events
kubectl get events -n mlops-dev

# Check ConfigMap/Secret
kubectl get configmap,secret -n mlops-dev
```

**Connection issues:**
```bash
# Test connectivity inside pod
kubectl exec -n mlops-dev <pod-name> -- curl http://redis:6379

# Check DNS resolution
kubectl exec -n mlops-dev <pod-name> -- nslookup redis

# Check network policy
kubectl get networkpolicy -n mlops-prod
```

---

## Related Documentation

- **[Configuration README](../README.md)** - Navigation and overview
- **[Quick Start](../QUICK_START.md)** - Getting started
- **[Deployment](../DEPLOYMENT.md)** - Environment-specific configurations
- **[Environment Variables](../ENVIRONMENT_VARIABLES.md)** - Complete settings reference
- **[Troubleshooting](../TROUBLESHOOTING.md)** - Common issues and solutions

---

**Last Updated:** 2025-11-25
**Maintained By:** KubeSentiment Team
