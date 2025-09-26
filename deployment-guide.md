# Deployment Guide

This guide provides comprehensive instructions for deploying the Sentiment Analysis Microservice in various environments.

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
- Python 3.9+ (for local development)
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
   git clone https://github.com/your-org/mlops-sentiment.git
   cd mlops-sentiment
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

1. Create the namespace:
   ```bash
   kubectl create namespace mlops
   ```

2. Deploy the application:
   ```bash
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   kubectl apply -f k8s/ingress.yaml
   kubectl apply -f k8s/hpa.yaml
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_TEXT_LENGTH` | `10000` | Maximum allowed text length for analysis |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `MODEL_NAME` | `distilbert-base-uncased-finetuned-sst-2-english` | Hugging Face model name |
| `MODEL_CACHE_DIR` | `/app/model_cache` | Directory to cache the model |

### Updating Configuration

1. Update the ConfigMap in `k8s/configmap.yaml`
2. Apply the changes:
   ```bash
   kubectl apply -f k8s/configmap.yaml
   kubectl rollout restart deployment/sentiment-service -n mlops
   ```

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
kubectl logs -l app=sentiment-service -n mlops --tail=100

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
