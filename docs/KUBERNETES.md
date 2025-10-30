# Kubernetes Deployment Guide

For detailed Kubernetes deployment instructions, please see:

**[setup/deployment-guide.md](setup/deployment-guide.md)** - Comprehensive deployment guide

**[setup/DEVELOPMENT.md](setup/DEVELOPMENT.md)** - Development environment setup including Kubernetes

## Quick Kubernetes Setup

### Prerequisites

- Kubernetes 1.21+
- kubectl configured
- Helm 3.7+
- Docker (for local clusters)

### Option 1: Using Helm (Recommended)

```bash
# Install with Helm
helm install sentiment-service ./helm/mlops-sentiment \
  --namespace mlops-sentiment \
  --create-namespace \
  --values helm/mlops-sentiment/values-dev.yaml
```

### Option 2: Manual Deployment

```bash
# Create namespace
kubectl create namespace mlops-sentiment

# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

### Option 3: Local Development Clusters

#### Minikube

```bash
# Setup Minikube
bash scripts/setup-minikube.sh

# Deploy the service
bash scripts/deploy.sh

# Access the service
minikube service sentiment-service-nodeport -n mlops-sentiment --url
```

#### Kind (Kubernetes in Docker)

```bash
# Setup Kind cluster
bash scripts/setup-kind.sh

# Deploy the service
bash scripts/deploy.sh

# Access via NodePort
curl http://localhost:30800/api/v1/health
```

## Kubernetes Resources

The deployment includes:

### Core Resources

- **Namespace**: `mlops-sentiment` - Isolated environment
- **Deployment**: Manages application pods with rolling updates
- **Service**: ClusterIP and NodePort services
- **ConfigMap**: Application configuration
- **Secret**: Sensitive credentials (API keys, tokens)

### Scaling & High Availability

- **HorizontalPodAutoscaler (HPA)**: Auto-scales 2-10 pods based on CPU/memory
- **PodDisruptionBudget (PDB)**: Ensures minimum availability during updates
- **Anti-Affinity Rules**: Distributes pods across nodes

### Monitoring & Observability

- **ServiceMonitor**: Prometheus metrics collection
- **PrometheusRule**: Alerting rules
- **NetworkPolicy**: Restricts pod-to-pod communication

### Storage

- **PersistentVolumeClaim**: Model cache storage (optional)
- **ReadWriteMany**: Shared storage across pods

## Scaling Operations

### Manual Scaling

```bash
# Scale to 5 replicas
kubectl scale deployment sentiment-service --replicas=5 -n mlops-sentiment
```

### Auto-Scaling

HPA automatically scales based on:
- CPU utilization > 70%
- Memory utilization > 80%
- Custom metrics (active requests)

### Check HPA Status

```bash
kubectl get hpa -n mlops-sentiment
kubectl describe hpa sentiment-service-hpa -n mlops-sentiment
```

## Health Checks

The deployment includes:

- **Liveness Probe**: Restarts unhealthy containers
- **Readiness Probe**: Removes unready pods from service
- **Startup Probe**: Allows time for initial model loading

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n mlops-sentiment
kubectl describe pod <pod-name> -n mlops-sentiment
kubectl logs <pod-name> -n mlops-sentiment
```

### Common Issues

**Pods Not Starting**
```bash
# Check events
kubectl get events -n mlops-sentiment --sort-by='.metadata.creationTimestamp'

# Check resource limits
kubectl describe deployment sentiment-service -n mlops-sentiment
```

**Image Pull Errors**
```bash
# For Minikube
minikube image load sentiment-service:latest

# For Kind
kind load docker-image sentiment-service:latest --name mlops-sentiment
```

**Service Not Accessible**
```bash
# Check service endpoints
kubectl get endpoints -n mlops-sentiment

# Port forward for debugging
kubectl port-forward svc/sentiment-service 8000:8000 -n mlops-sentiment
```

## Advanced Topics

### Zero-Downtime Deployments

Rolling update strategy with:
- MaxSurge: 1 pod
- MaxUnavailable: 0 pods
- Graceful shutdown: 60s

### Resource Management

Recommended resource limits:

**Development**
```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 1000m
    memory: 2Gi
```

**Production**
```yaml
resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 2000m
    memory: 4Gi
```

### Network Policies

Ingress allowed from:
- Load balancer
- Prometheus (monitoring)

Egress allowed to:
- DNS
- Redis (caching)
- Kafka (message queue)
- HTTPS (model downloads)

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Architecture Guide](architecture.md)
- [Deployment Guide](setup/deployment-guide.md)
- [Scalability Enhancements](SCALABILITY_ENHANCEMENTS.md)
