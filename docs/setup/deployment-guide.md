# Deployment Guide

> **Note:** This guide provides basic deployment instructions. For comprehensive environment-specific configurations, Helm values, and deployment procedures, see **[docs/configuration/DEPLOYMENT.md](../configuration/DEPLOYMENT.md)**.

This guide provides basic instructions for deploying the Sentiment Analysis Microservice in various environments.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration](#configuration)
- [Scaling](#scaling)
- [Monitoring](#monitoring)

## Prerequisites

### System Requirements
- Docker 20.10+ and Docker Compose 1.29+
- Kubernetes 1.21+ (for Kubernetes deployment)
- Helm 3.7+ (for Helm chart deployment)
- Python 3.11+ (for local development)
- 4GB RAM (minimum), 8GB+ recommended
- 2 CPU cores (minimum), 4+ recommended

### Required Tools
- `kubectl` (for Kubernetes deployments)
- `helm` (for Helm chart deployments)
- `docker` and `docker-compose`
- `git`

## Local Development

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/arec1b0/KubeSentiment.git
   cd KubeSentiment
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Service

#### Development Mode
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Mode
```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b :8000 app.main:app
```

### Testing

Run the test suite:
```bash
pytest tests/
```

## Docker Deployment

### Building the Image
```bash
docker build -t sentiment-service:latest .
```

### Running the Container
```bash
docker run -d \
  --name sentiment-service \
  -p 8000:8000 \
  -e MAX_TEXT_LENGTH=5000 \
  -e LOG_LEVEL=INFO \
  sentiment-service:latest
```

### Docker Compose
```yaml
version: '3.8'

services:
  sentiment-service:
    image: sentiment-service:latest
    ports:
      - "8000:8000"
    environment:
      - MAX_TEXT_LENGTH=5000
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

## Kubernetes Deployment

### Prerequisites
- A running Kubernetes cluster
- `kubectl` configured to communicate with your cluster
- `helm` installed

### Using Helm

1. Add the Helm repository (if applicable)
2. Install the chart:
   ```bash
   helm install sentiment-service ./helm/mlops-sentiment \
     --namespace mlops \
     --values helm/mlops-sentiment/values-dev.yaml
   ```

### Manual Deployment

**Note:** This project uses Helm for deployment. Individual Kubernetes manifest files are generated from the Helm chart templates. For raw manifest deployment, use one of these approaches:

#### Option 1: Generate Manifests from Helm (Recommended)
```bash
# Generate all Kubernetes manifests
helm template mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-sentiment \
  --values helm/mlops-sentiment/values-dev.yaml \
  > generated-manifests.yaml

# Apply generated manifests
kubectl create namespace mlops-sentiment
kubectl apply -f generated-manifests.yaml
```

#### Option 2: Use Scalability Configuration
```bash
# For scalability features (Redis, HPA, etc.)
kubectl create namespace mlops-sentiment
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/scalability-config.yaml
```

## Configuration

> **For complete configuration documentation**, including all environment variables, profile-based defaults, and deployment configurations, see **[docs/configuration/DEPLOYMENT.md](../configuration/DEPLOYMENT.md)** and **[docs/configuration/ENVIRONMENT_VARIABLES.md](../configuration/ENVIRONMENT_VARIABLES.md)**.

### Quick Reference

- **Environment-specific configs:** [Deployment Guide](../configuration/DEPLOYMENT.md)
- **All environment variables:** [Environment Variables Reference](../configuration/ENVIRONMENT_VARIABLES.md)
- **Profile-based defaults:** [Configuration Profiles](../configuration/PROFILES.md)
- **Configuration troubleshooting:** [Configuration Troubleshooting](../configuration/TROUBLESHOOTING.md)

## Scaling

### Horizontal Pod Autoscaling

The service includes an HPA configuration that automatically scales the number of pods based on CPU and memory usage.

#### View HPA Status
```bash
kubectl get hpa -n mlops
```

#### Manual Scaling
```bash
kubectl scale deployment/sentiment-service --replicas=3 -n mlops
```

## Monitoring

### Prometheus Metrics
Metrics are exposed at `/metrics` in Prometheus format.

### Health Checks
- `/health`: Service health status
- `/metrics/json`: JSON-formatted metrics

### Logs
View logs using:
```bash
# For Kubernetes
kubectl logs -l app=sentiment-service -n mlops-sentiment --tail=100

# For Docker
kubectl logs -f sentiment-service
```

## Upgrading

1. Pull the latest changes
2. Update the container image
3. Follow the rolling update strategy:
   ```bash
   kubectl set image deployment/sentiment-service \
     sentiment-service=your-registry/sentiment-service:new-version \
     -n mlops
   ```

## Rollback

To rollback to the previous version:
```bash
kubectl rollout undo deployment/sentiment-service -n mlops
```
