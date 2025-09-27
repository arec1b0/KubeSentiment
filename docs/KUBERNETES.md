# Kubernetes Deployment Guide

## 🚀 Quick Start

This guide provides step-by-step instructions for deploying the MLOps Sentiment Analysis service to Kubernetes using either Minikube or Kind.

## Prerequisites

- Docker installed and running
- kubectl command-line tool
- Either Minikube or Kind installed

## Option 1: Minikube (Recommended for Development)

### 1. Install Minikube

**Windows:**

```bash
# Using Chocolatey
choco install minikube

# Using winget
winget install Kubernetes.minikube
```

**macOS:**

```bash
# Using Homebrew
brew install minikube
```

**Linux:**

```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

### 2. Setup and Deploy

```bash
# Setup Minikube with all required addons
bash scripts/setup-minikube.sh

# Deploy the sentiment analysis service
bash scripts/deploy.sh

# Get service URL
minikube service sentiment-service-nodeport -n mlops-sentiment --url
```

### 3. Access the Service

```bash
# Get Minikube IP
MINIKUBE_IP=$(minikube ip)

# Test the service
curl http://${MINIKUBE_IP}:30800/health
curl -X POST http://${MINIKUBE_IP}:30800/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this Kubernetes deployment!"}'

# Access API documentation
open http://${MINIKUBE_IP}:30800/docs
```

## Option 2: Kind (Kubernetes in Docker)

### 1. Install Kind

**Windows:**

```bash
# Using Chocolatey
choco install kind

# Manual installation
curl.exe -Lo kind-windows-amd64.exe https://kind.sigs.k8s.io/dl/v0.20.0/kind-windows-amd64
Move-Item .\kind-windows-amd64.exe c:\some-dir-in-your-PATH\kind.exe
```

**macOS:**

```bash
# Using Homebrew
brew install kind

# Manual installation
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-darwin-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```

**Linux:**

```bash
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```

### 2. Setup and Deploy

```bash
# Setup Kind cluster with all required components
bash scripts/setup-kind.sh

# Deploy the sentiment analysis service
bash scripts/deploy.sh

# Service will be available on localhost:30800
```

### 3. Access the Service

```bash
# Test the service
curl http://localhost:30800/health
curl -X POST http://localhost:30800/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Kind makes Kubernetes development easy!"}'

# Access API documentation
open http://localhost:30800/docs
```

## Manual Deployment Steps

If you prefer to deploy manually or understand what the scripts do:

### 1. Build and Load Docker Image

```bash
# Build the Docker image
docker build -t sentiment-service:latest .

# Load image into cluster
minikube image load sentiment-service:latest  # For Minikube
# OR
kind load docker-image sentiment-service:latest --name mlops-sentiment  # For Kind
```

### 2. Apply Kubernetes Manifests

```bash
# Create namespace and apply configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Optional: Apply Ingress (requires NGINX Ingress Controller)
kubectl apply -f k8s/ingress.yaml

# Optional: Apply HPA (requires metrics server)
kubectl apply -f k8s/hpa.yaml
```

### 3. Verify Deployment

```bash
# Check if pods are running
kubectl get pods -n mlops-sentiment

# Check service status
kubectl get services -n mlops-sentiment

# View logs
kubectl logs -f deployment/sentiment-service -n mlops-sentiment
```

## Kubernetes Resources Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    mlops-sentiment namespace                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   Ingress    │────│   Service       │────│ Deployment  │ │
│  │              │    │ (ClusterIP +    │    │ (2 replicas)│ │
│  │ sentiment.   │    │  NodePort)      │    │             │ │
│  │ local        │    │                 │    │ sentiment-  │ │
│  └──────────────┘    └─────────────────┘    │ service     │ │
│                                             │             │ │
│  ┌──────────────┐    ┌─────────────────┐    └─────────────┘ │
│  │ ConfigMap    │────│      HPA        │                    │
│  │              │    │                 │                    │
│  │ App Config   │    │ Auto Scaling    │                    │
│  └──────────────┘    └─────────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Resource Specifications

#### Deployment

- **Replicas**: 2 (for high availability)
- **Strategy**: Rolling Update (zero downtime deployments)
- **Resources**:
  - Requests: 500m CPU, 1Gi memory
  - Limits: 1000m CPU, 2Gi memory
- **Health Checks**: Liveness, Readiness, and Startup probes

#### Service

- **ClusterIP**: Internal cluster communication
- **NodePort**: External access on port 30800
- **Target Port**: 8000 (application port)

#### ConfigMap

- Production and development configurations
- Environment-specific settings
- Model parameters

#### HPA (Horizontal Pod Autoscaler)

- **Min Replicas**: 2
- **Max Replicas**: 10
- **Metrics**: CPU (70%), Memory (80%)

## Monitoring and Debugging

### Check Deployment Status

```bash
# Overall cluster status
kubectl get all -n mlops-sentiment

# Pod details
kubectl describe pod <pod-name> -n mlops-sentiment

# Service endpoints
kubectl get endpoints -n mlops-sentiment

# Resource usage (requires metrics server)
kubectl top pods -n mlops-sentiment
```

### View Logs

```bash
# Real-time logs from all pods
kubectl logs -f deployment/sentiment-service -n mlops-sentiment

# Logs from specific pod
kubectl logs <pod-name> -n mlops-sentiment

# Previous container logs (if pod restarted)
kubectl logs <pod-name> -n mlops-sentiment --previous
```

### Port Forwarding

```bash
# Forward local port to service
kubectl port-forward svc/sentiment-service 8000:8000 -n mlops-sentiment

# Forward local port to specific pod
kubectl port-forward <pod-name> 8000:8000 -n mlops-sentiment
```

### Execute Commands in Pod

```bash
# Get shell access to pod
kubectl exec -it deployment/sentiment-service -n mlops-sentiment -- /bin/bash

# Run specific command
kubectl exec deployment/sentiment-service -n mlops-sentiment -- env
```

## Scaling

### Manual Scaling

```bash
# Scale deployment to 5 replicas
kubectl scale deployment sentiment-service --replicas=5 -n mlops-sentiment

# Check scaling status
kubectl get pods -n mlops-sentiment -w
```

### Auto Scaling (HPA)

```bash
# Check HPA status
kubectl get hpa -n mlops-sentiment

# Describe HPA for detailed metrics
kubectl describe hpa sentiment-service-hpa -n mlops-sentiment

# Generate load to test auto scaling
kubectl run -i --tty load-generator --rm --image=busybox --restart=Never -- /bin/sh
# Inside pod: while true; do wget -q -O- http://sentiment-service.mlops-sentiment:8000/health; done
```

## Cleanup

### Quick Cleanup

```bash
# Remove all resources
bash scripts/cleanup.sh
```

### Manual Cleanup

```bash
# Delete namespace (removes all resources)
kubectl delete namespace mlops-sentiment

# Stop and remove clusters
minikube stop && minikube delete    # For Minikube
kind delete cluster --name mlops-sentiment  # For Kind
```

## Troubleshooting

### Common Issues

#### Pods Stuck in Pending State

```bash
# Check node resources
kubectl describe nodes

# Check pod events
kubectl describe pod <pod-name> -n mlops-sentiment

# Check resource quotas
kubectl describe resourcequota -n mlops-sentiment
```

#### Image Pull Errors

```bash
# For Minikube: ensure image is loaded
minikube image ls | grep sentiment-service
minikube image load sentiment-service:latest

# For Kind: ensure image is loaded
docker exec -it mlops-sentiment-control-plane crictl images | grep sentiment-service
kind load docker-image sentiment-service:latest --name mlops-sentiment
```

#### Service Not Accessible

```bash
# Check service endpoints
kubectl get endpoints sentiment-service -n mlops-sentiment

# Test internal connectivity
kubectl run debug --image=curlimages/curl -it --rm -- /bin/sh
# curl http://sentiment-service.mlops-sentiment:8000/health

# For NodePort issues, check node IP and port
kubectl get nodes -o wide
kubectl get svc sentiment-service-nodeport -n mlops-sentiment
```

#### Ingress Not Working

```bash
# Check NGINX Ingress Controller
kubectl get pods -n ingress-nginx

# Check ingress resource
kubectl describe ingress sentiment-service-ingress -n mlops-sentiment

# Test ingress controller
curl -H "Host: sentiment.local" http://<cluster-ip>/health
```

### Performance Issues

```bash
# Check resource usage
kubectl top pods -n mlops-sentiment
kubectl top nodes

# Check HPA metrics
kubectl get hpa -n mlops-sentiment

# View detailed pod metrics
kubectl describe pod <pod-name> -n mlops-sentiment
```

## Advanced Configuration

### Custom Configuration

Edit `k8s/configmap.yaml` to modify application settings:

```yaml
data:
  MLOPS_MODEL_NAME: "your-custom-model"
  MLOPS_MAX_TEXT_LENGTH: "1024"
  MLOPS_DEBUG: "false"
```

### Resource Limits

Edit `k8s/deployment.yaml` to adjust resource allocation:

```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Ingress Configuration

Edit `k8s/ingress.yaml` to customize routing:

```yaml
spec:
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /sentiment
        pathType: Prefix
        backend:
          service:
            name: sentiment-service
            port:
              number: 8000
```

## Next Steps

- Set up monitoring with Prometheus and Grafana
- Implement CI/CD pipeline with GitHub Actions
- Add distributed tracing with Jaeger
- Set up log aggregation with ELK stack
- Implement GitOps with ArgoCD
- Create Helm charts for easier deployment
- Set up service mesh with Istio

## Support

For issues and questions:

- Check the troubleshooting section above
- Review logs: `kubectl logs -f deployment/sentiment-service -n mlops-sentiment`
- Inspect resources: `kubectl describe <resource> <name> -n mlops-sentiment`
- Open an issue in the project repository
