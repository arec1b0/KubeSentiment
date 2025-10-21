# Deployment Guide

**Version:** 1.0.0  
**Last Updated:** October 21, 2025

## Table of Contents

- [Overview](#overview)
- [Deployment Options](#deployment-options)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Docker Deployment](#docker-deployment)
- [Serverless Deployment](#serverless-deployment)
- [Environment Configuration](#environment-configuration)
- [Security Setup](#security-setup)
- [Monitoring Setup](#monitoring-setup)
- [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers deploying the MLOps Sentiment Analysis service across different environments and platforms. Choose the deployment method that best fits your needs.

### Deployment Comparison

| Method | Best For | Complexity | Scalability | Cost |
|--------|----------|------------|-------------|------|
| Docker | Development, Small deployments | Low | Manual | Low |
| Docker Compose | Local testing, Small teams | Low | Limited | Low |
| Kubernetes | Production, Enterprise | High | Automatic | Medium |
| AWS Lambda | Event-driven, Sporadic load | Medium | Automatic | Pay-per-use |
| Cloud Run | Serverless, Variable load | Low | Automatic | Pay-per-use |

---

## Deployment Options

### Quick Start Matrix

```bash
# Development (Local)
docker run -p 8000:8000 sentiment-service:latest

# Staging (Kubernetes)
helm install sentiment-staging ./helm/mlops-sentiment \
  --values ./helm/mlops-sentiment/values-staging.yaml

# Production (Kubernetes)
helm install sentiment-prod ./helm/mlops-sentiment \
  --values ./helm/mlops-sentiment/values-prod.yaml
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster 1.28+ (EKS, GKE, AKS, or local with Kind/Minikube)
- kubectl configured
- Helm 3.13+ installed
- Docker registry access (ghcr.io recommended)

### Option 1: Local Kubernetes (Kind)

```bash
# 1. Create local Kubernetes cluster
bash scripts/setup-kind.sh

# 2. Load Docker image into Kind
docker build -t sentiment-service:latest .
kind load docker-image sentiment-service:latest --name mlops-sentiment

# 3. Deploy with Helm
helm install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-sentiment \
  --create-namespace \
  --set image.repository=sentiment-service \
  --set image.tag=latest \
  --set image.pullPolicy=Never

# 4. Port forward to access service
kubectl port-forward -n mlops-sentiment svc/mlops-sentiment 8000:80

# 5. Test deployment
curl http://localhost:8000/health
```

### Option 2: Production Kubernetes

#### Step 1: Prepare Container Image

```bash
# Build and push to registry
docker build -t ghcr.io/yourusername/mlops-sentiment:v1.0.0 .
docker push ghcr.io/yourusername/mlops-sentiment:v1.0.0
```

#### Step 2: Create Namespace and Secrets

```bash
# Create namespace
kubectl create namespace mlops-sentiment

# Create image pull secret (if using private registry)
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io \
  --docker-username=your-username \
  --docker-password=your-token \
  --namespace=mlops-sentiment

# Create API key secret (optional)
kubectl create secret generic mlops-secrets \
  --from-literal=api-key=your-secure-api-key \
  --namespace=mlops-sentiment
```

#### Step 3: Deploy with Helm

```bash
# Install Helm chart
helm install mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-sentiment \
  --values ./helm/mlops-sentiment/values-prod.yaml \
  --set image.repository=ghcr.io/yourusername/mlops-sentiment \
  --set image.tag=v1.0.0

# Verify deployment
helm status mlops-sentiment -n mlops-sentiment
kubectl get all -n mlops-sentiment

# View logs
kubectl logs -f deployment/mlops-sentiment -n mlops-sentiment
```

#### Step 4: Configure Ingress

```bash
# Get ingress details
kubectl get ingress -n mlops-sentiment

# Access via ingress (update your DNS to point to ingress IP)
curl https://sentiment.yourdomain.com/health
```

### Helm Configuration

#### Development Environment

```yaml
# helm/mlops-sentiment/values-dev.yaml
replicaCount: 1

image:
  pullPolicy: Always

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: false

monitoring:
  prometheus:
    enabled: true
  grafana:
    enabled: false
```

#### Production Environment

```yaml
# helm/mlops-sentiment/values-prod.yaml
replicaCount: 3

image:
  pullPolicy: IfNotPresent

resources:
  requests:
    cpu: 1000m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 2Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

podDisruptionBudget:
  enabled: true
  minAvailable: 2

monitoring:
  prometheus:
    enabled: true
  grafana:
    enabled: true
  alertmanager:
    enabled: true

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "1000"
  hosts:
    - host: sentiment-api.production.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: sentiment-api-tls
      hosts:
        - sentiment-api.production.com
```

### Upgrade Deployment

```bash
# Upgrade to new version
helm upgrade mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-sentiment \
  --values ./helm/mlops-sentiment/values-prod.yaml \
  --set image.tag=v1.1.0

# Rollback if needed
helm rollback mlops-sentiment -n mlops-sentiment

# View history
helm history mlops-sentiment -n mlops-sentiment
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment mlops-sentiment \
  --replicas=5 \
  --namespace=mlops-sentiment

# Check HPA status
kubectl get hpa -n mlops-sentiment

# View pod status
kubectl get pods -n mlops-sentiment -w
```

---

## Docker Deployment

### Standalone Docker

```bash
# 1. Build image
docker build -t sentiment-service:latest .

# 2. Run container
docker run -d \
  --name sentiment-app \
  -p 8000:8000 \
  -e MLOPS_MODEL_NAME="distilbert-base-uncased-finetuned-sst-2-english" \
  -e MLOPS_DEBUG=false \
  -e MLOPS_LOG_LEVEL=INFO \
  -v $(pwd)/models:/app/models \
  --restart unless-stopped \
  sentiment-service:latest

# 3. View logs
docker logs -f sentiment-app

# 4. Test
curl http://localhost:8000/health
```

### Docker Compose (Development)

```yaml
# docker-compose.yml
version: '3.8'

services:
  sentiment-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      MLOPS_DEBUG: "true"
      MLOPS_LOG_LEVEL: "DEBUG"
      MLOPS_MODEL_NAME: "distilbert-base-uncased-finetuned-sst-2-english"
    volumes:
      - ./models:/app/models
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus-config.yaml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: "admin"
    volumes:
      - ./config/grafana-datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yaml
      - ./config/grafana-advanced-dashboard.json:/var/lib/grafana/dashboards/sentiment-dashboard.json
    restart: unless-stopped
```

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f sentiment-api

# Stop all services
docker-compose down

# Clean up volumes
docker-compose down -v
```

---

## Serverless Deployment

### AWS Lambda

```bash
# Navigate to Lambda directory
cd serverless/aws-lambda

# Install serverless framework
npm install -g serverless

# Configure AWS credentials
aws configure

# Deploy to AWS
serverless deploy --stage prod

# Test function
serverless invoke --function sentiment-predict \
  --data '{"text":"Great product!"}'

# View logs
serverless logs --function sentiment-predict --tail

# Remove deployment
serverless remove --stage prod
```

### Google Cloud Run

```bash
# Navigate to Cloud Run directory
cd serverless/google-cloud-run

# Authenticate with GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and deploy
bash deploy.sh prod

# Test deployment
ENDPOINT=$(gcloud run services describe sentiment-api \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)')

curl -X POST ${ENDPOINT}/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"Amazing service!"}'
```

---

## Environment Configuration

### Production Checklist

```bash
✓ Set MLOPS_DEBUG=false
✓ Set MLOPS_LOG_LEVEL=INFO or WARNING
✓ Configure MLOPS_API_KEY for authentication
✓ Set resource limits (CPU, memory)
✓ Enable monitoring (Prometheus, Grafana)
✓ Configure health checks
✓ Set up auto-scaling (HPA)
✓ Configure pod disruption budget
✓ Enable TLS/SSL on ingress
✓ Set up rate limiting
✓ Configure backup and disaster recovery
✓ Set up alerting (Slack, PagerDuty)
```

### Environment Variables

```bash
# Core Configuration
export MLOPS_APP_NAME="ML Model Serving API"
export MLOPS_APP_VERSION="1.0.0"
export MLOPS_DEBUG=false
export MLOPS_LOG_LEVEL=INFO

# Model Configuration
export MLOPS_MODEL_NAME="distilbert-base-uncased-finetuned-sst-2-english"
export MLOPS_MAX_TEXT_LENGTH=512
export MLOPS_PREDICTION_CACHE_MAX_SIZE=1000

# Optional: ONNX Optimization
export MLOPS_ONNX_MODEL_PATH="/app/onnx_models/distilbert"

# Security
export MLOPS_API_KEY="your-production-api-key"
export MLOPS_ALLOWED_ORIGINS='["https://yourdomain.com"]'

# Vault Configuration (recommended for production)
export MLOPS_VAULT_ENABLED=true
export MLOPS_VAULT_ADDR="https://vault.production.com:8200"
export MLOPS_VAULT_TOKEN="s.your-vault-token"
export MLOPS_VAULT_NAMESPACE="mlops-sentiment"

# Monitoring
export MLOPS_ENABLE_METRICS=true
export MLOPS_METRICS_CACHE_TTL=5
```

---

## Security Setup

### HashiCorp Vault Integration

```bash
# 1. Set up Vault authentication
kubectl create serviceaccount mlops-sentiment-vault \
  --namespace mlops-sentiment

# 2. Configure Vault policy
vault policy write mlops-sentiment - <<EOF
path "mlops-sentiment/data/prod/*" {
  capabilities = ["read", "list"]
}
EOF

# 3. Enable Kubernetes auth
vault auth enable kubernetes

# 4. Configure Kubernetes auth
vault write auth/kubernetes/role/mlops-sentiment-prod \
    bound_service_account_names=mlops-sentiment-vault \
    bound_service_account_namespaces=mlops-sentiment \
    policies=mlops-sentiment \
    ttl=24h

# 5. Store secrets in Vault
vault kv put mlops-sentiment/prod/api_key value="your-secret-key"
```

### TLS/SSL Configuration

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

---

## Monitoring Setup

### Prometheus Configuration

```bash
# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values config/prometheus-values.yaml
```

### Grafana Dashboard

```bash
# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Default credentials: admin / prom-operator

# Import dashboard
# Go to http://localhost:3000
# Import config/grafana-advanced-dashboard.json
```

### Alerting

```bash
# Configure AlertManager
kubectl apply -f config/alertmanager-config.yaml

# Test alert
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname":"TestAlert","severity":"warning"},
    "annotations": {"summary":"Test alert"}
  }]'
```

---

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n mlops-sentiment

# Describe pod for events
kubectl describe pod <pod-name> -n mlops-sentiment

# Check logs
kubectl logs <pod-name> -n mlops-sentiment

# Common causes:
# - Image pull errors (check imagePullSecrets)
# - Insufficient resources (check resource requests/limits)
# - Failing health checks (check liveness/readiness probes)
```

#### Service Unreachable

```bash
# Check service
kubectl get svc -n mlops-sentiment

# Check endpoints
kubectl get endpoints -n mlops-sentiment

# Test internal connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://mlops-sentiment.mlops-sentiment.svc.cluster.local/health
```

#### High Latency

```bash
# Check resource utilization
kubectl top pods -n mlops-sentiment

# Check HPA status
kubectl get hpa -n mlops-sentiment

# Check metrics
curl http://localhost:8000/metrics

# Scale manually if needed
kubectl scale deployment mlops-sentiment --replicas=5 -n mlops-sentiment
```

### Health Check Endpoints

```bash
# Liveness probe
curl http://localhost:8000/health

# Readiness probe
curl http://localhost:8000/health

# Metrics endpoint
curl http://localhost:8000/metrics
```

### Rollback Procedure

```bash
# View deployment history
kubectl rollout history deployment/mlops-sentiment -n mlops-sentiment

# Rollback to previous version
kubectl rollout undo deployment/mlops-sentiment -n mlops-sentiment

# Rollback to specific revision
kubectl rollout undo deployment/mlops-sentiment \
  --to-revision=2 \
  -n mlops-sentiment

# Check rollout status
kubectl rollout status deployment/mlops-sentiment -n mlops-sentiment
```

---

## Best Practices

### Do's ✓

- Always use specific image tags (not `latest`) in production
- Set resource requests and limits
- Configure health checks (liveness and readiness probes)
- Enable auto-scaling with appropriate thresholds
- Use pod disruption budgets for high availability
- Implement proper monitoring and alerting
- Store secrets in Vault, not environment variables
- Use TLS for all external communication
- Implement rate limiting
- Regular backup of critical data

### Don'ts ✗

- Don't deploy directly to production without testing
- Don't skip security scanning of container images
- Don't use `latest` tag in production
- Don't run containers as root
- Don't hardcode secrets in manifests
- Don't ignore resource limits
- Don't skip health check configuration
- Don't deploy on Friday afternoon

---

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)

---

**Maintainers**: MLOps Operations Team  
**Last Review**: October 2025  
**Next Review**: January 2026
