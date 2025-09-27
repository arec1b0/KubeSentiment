# Development Environment Guide

## 🚀 Quick Start

### 1. **Environment Setup**

```bash
# The virtual environment is already created at: F:\Projects\MLOps\venv\
# Python version: 3.13.5
# All dependencies are installed
```

### 2. **Start Development Server**

```bash
python run.py
```

### 3. **Access the Service**

- **API Documentation**: <http://localhost:8000/docs>
- **Alternative Docs**: <http://localhost:8000/redoc>
- **Health Check**: <http://localhost:8000/health>
- **Metrics**: <http://localhost:8000/metrics>

## 🧪 Testing

### Quick Test

```bash
python test_service.py
```

### Manual Testing

```bash
# Health check
curl -X GET "http://localhost:8000/health"

# Positive sentiment
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"text": "I love this service!"}'

# Negative sentiment  
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"text": "This is terrible"}'
```

## 📁 Project Structure

```
f:\Projects\MLOps\
├── .env                    # Environment variables
├── app/                    # Main application
│   ├── __init__.py         # Package init
│   ├── main.py            # FastAPI app & lifecycle
│   ├── config.py          # Configuration management
│   ├── api.py             # API endpoints
│   └── ml/                # ML modules
│       ├── __init__.py    
│       └── sentiment.py   # Sentiment analysis logic
├── k8s/                   # Kubernetes manifests
│   ├── namespace.yaml     # Namespace and resource quotas
│   ├── configmap.yaml     # Configuration maps
│   ├── deployment.yaml    # Deployment specification
│   ├── service.yaml       # Service definitions
│   ├── ingress.yaml       # Ingress configuration
│   └── hpa.yaml          # Horizontal Pod Autoscaler
├── scripts/               # Deployment scripts
│   ├── deploy.sh         # Main deployment script
│   ├── cleanup.sh        # Cleanup script
│   ├── setup-minikube.sh # Minikube setup
│   └── setup-kind.sh     # Kind setup
├── venv/                  # Virtual environment
├── run.py                 # Development server launcher
├── test_service.py        # Test script
├── setup_dev.py          # Environment setup script
├── requirements.txt       # Dependencies
├── Dockerfile            # Container definition
└── README.md             # Documentation
```

## ⚙️ Configuration

### Environment Variables (.env file)

```bash
MLOPS_DEBUG=true                    # Enable debug mode
MLOPS_LOG_LEVEL=INFO               # Logging level
MLOPS_HOST=0.0.0.0                 # Server host
MLOPS_PORT=8000                    # Server port
MLOPS_ENABLE_METRICS=true          # Enable metrics
MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
```

### Model Configuration

- **Model**: DistilBERT fine-tuned on SST-2
- **Input**: Text strings (max 512 chars)
- **Output**: POSITIVE/NEGATIVE with confidence score
- **Performance**: ~100ms response time

## 🔧 Development Workflow

### 1. **Code Changes**

- The server runs with hot reload enabled
- Changes to `app/` directory are automatically detected
- Browser refresh shows updated API docs

### 2. **Adding New Endpoints**

1. Add endpoint to `app/api.py`
2. Update Pydantic models if needed
3. Test via `/docs` interface

### 3. **Model Changes**

1. Update `app/ml/sentiment.py`
2. Modify `app/config.py` for new settings
3. Restart server to reload model

## 🐛 Troubleshooting

### Common Issues

**Import Errors**

```bash
# Reinstall dependencies
F:\Projects\MLOps\venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Model Loading Issues**

- Check internet connection (model downloads from Hugging Face)
- Verify disk space (model ~268MB)
- Check logs for specific errors

**Port Already in Use**

```bash
# Change port in .env file
MLOPS_PORT=8001
```

**Performance Issues**

- Model loads on first startup (~30 seconds)
- Subsequent requests are fast (~100ms)
- CPU-only inference (no GPU required)

## 📊 Monitoring

### Health Check Response

```json
{
  "status": "healthy",
  "model_status": "available", 
  "version": "1.0.0",
  "timestamp": 1726251097.5
}
```

### Metrics Response

```json
{
  "torch_version": "2.5.1+cpu",
  "cuda_available": false,
  "cuda_memory_allocated_mb": 0.0,
  "cuda_memory_reserved_mb": 0.0,
  "cuda_device_count": 0
}
```

## 🚢 Deployment

### Local Container

```bash
docker build -t sentiment-service:1.0 .
docker run -d -p 8000:8000 sentiment-service:1.0
```

### Kubernetes Deployment

#### Option 1: Minikube (Recommended for Development)

```bash
# 1. Setup Minikube
bash scripts/setup-minikube.sh

# 2. Deploy the service
bash scripts/deploy.sh

# 3. Access the service
# Minikube IP will be displayed after deployment
curl http://$(minikube ip):30800/health
```

#### Option 2: Kind (Kubernetes in Docker)

```bash
# 1. Setup Kind cluster
bash scripts/setup-kind.sh

# 2. Deploy the service
bash scripts/deploy.sh

# 3. Access the service
curl http://localhost:30800/health
```

#### Manual Kubernetes Deployment

```bash
# Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml    # Optional: requires NGINX Ingress
kubectl apply -f k8s/hpa.yaml        # Optional: requires metrics server

# Check deployment status
kubectl get pods -n mlops-sentiment
kubectl get services -n mlops-sentiment

# Port forward for local access
kubectl port-forward svc/sentiment-service 8000:8000 -n mlops-sentiment
```

#### Cleanup Kubernetes Resources

```bash
# Remove all resources
bash scripts/cleanup.sh

# Or manually
kubectl delete namespace mlops-sentiment
```

### Production Considerations

- Use `MLOPS_DEBUG=false` in production
- Set up proper logging aggregation
- Configure health checks for orchestrators
- Use process managers (gunicube) for scaling
- Set up monitoring and alerting
- Configure resource limits and requests
- Set up horizontal pod autoscaling
- Use proper ingress controllers

## ☸️ Kubernetes Development

### Prerequisites

- Docker Desktop with Kubernetes enabled, or
- Minikube installed, or  
- Kind (Kubernetes in Docker) installed
- kubectl command-line tool

### Quick Kubernetes Setup

#### Using Minikube (Recommended)

```bash
# Install Minikube (if not installed)
# Windows: choco install minikube
# macOS: brew install minikube
# Linux: curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64

# Setup and start Minikube
bash scripts/setup-minikube.sh

# Deploy the service
bash scripts/deploy.sh

# Access the service
minikube service sentiment-service-nodeport -n mlops-sentiment --url
```

#### Using Kind

```bash
# Install Kind (if not installed)
# Windows: choco install kind
# macOS: brew install kind
# Linux: curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64

# Setup Kind cluster
bash scripts/setup-kind.sh

# Deploy the service
bash scripts/deploy.sh

# Access the service (NodePort available on localhost:30800)
curl http://localhost:30800/health
```

### Kubernetes Resources Overview

#### Namespace

- **mlops-sentiment**: Isolated namespace for the application
- Resource quotas to limit resource consumption

#### ConfigMap

- **sentiment-config**: Production configuration
- **sentiment-config-dev**: Development configuration with debug enabled

#### Deployment

- **sentiment-service**: Main application deployment
- 2 replicas with rolling update strategy
- Resource limits: 1 CPU, 2Gi memory
- Health checks: liveness, readiness, and startup probes

#### Services

- **sentiment-service**: ClusterIP service for internal access
- **sentiment-service-nodeport**: NodePort service for external access (port 30800)

#### Ingress (Optional)

- Routes external traffic to the service
- Requires NGINX Ingress Controller
- Accessible via `sentiment.local` or `localhost/sentiment`

#### HPA (Optional)

- Horizontal Pod Autoscaler
- Scales 2-10 pods based on CPU (70%) and memory (80%) usage
- Requires metrics server

### Kubernetes Development Workflow

#### 1. **Local Development**

```bash
# Start local development server
python run.py

# Build and test Docker image
docker build -t sentiment-service:latest .
docker run -p 8000:8000 sentiment-service:latest
```

#### 2. **Deploy to Kubernetes**

```bash
# Quick deployment
bash scripts/deploy.sh

# Manual deployment
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

#### 3. **Development Iteration**

```bash
# Update code and rebuild image
docker build -t sentiment-service:latest .

# Load image into cluster
minikube image load sentiment-service:latest  # For Minikube
# OR
kind load docker-image sentiment-service:latest --name mlops-sentiment  # For Kind

# Restart deployment to use new image
kubectl rollout restart deployment/sentiment-service -n mlops-sentiment
```

#### 4. **Monitoring and Debugging**

```bash
# Check pod status
kubectl get pods -n mlops-sentiment

# View logs
kubectl logs -f deployment/sentiment-service -n mlops-sentiment

# Port forward for local access
kubectl port-forward svc/sentiment-service 8000:8000 -n mlops-sentiment

# Execute commands in pod
kubectl exec -it deployment/sentiment-service -n mlops-sentiment -- /bin/bash

# Check resource usage
kubectl top pods -n mlops-sentiment
```

#### 5. **Cleanup**

```bash
# Remove all resources
bash scripts/cleanup.sh

# Or manually delete namespace
kubectl delete namespace mlops-sentiment
```

### Kubernetes Troubleshooting

#### Common Issues

**Pods not starting**

```bash
# Check pod events
kubectl describe pod <pod-name> -n mlops-sentiment

# Check logs
kubectl logs <pod-name> -n mlops-sentiment
```

**Image pull errors**

```bash
# For Minikube: Load image manually
minikube image load sentiment-service:latest

# For Kind: Load image manually  
kind load docker-image sentiment-service:latest --name mlops-sentiment

# Check if image exists in cluster
kubectl describe pod <pod-name> -n mlops-sentiment
```

**Service not accessible**

```bash
# Check service endpoints
kubectl get endpoints -n mlops-sentiment

# Test service connectivity from within cluster
kubectl run test-pod --image=curlimages/curl -it --rm -- /bin/sh
# Inside pod: curl http://sentiment-service.mlops-sentiment:8000/health
```

**Ingress not working**

```bash
# Check if NGINX Ingress Controller is installed
kubectl get pods -n ingress-nginx

# Check ingress status
kubectl describe ingress sentiment-service-ingress -n mlops-sentiment
```

## 📝 Next Steps

1. **Add Tests**: Create proper unit and integration tests
2. **Add CI/CD**: Set up automated testing and deployment
3. **Add Monitoring**: Integrate with Prometheus/Grafana
4. **Add Security**: API keys, rate limiting, input validation
5. **Add Documentation**: API specifications, deployment guides
6. **Add Helm Charts**: Package Kubernetes manifests with Helm
7. **Add GitOps**: Set up ArgoCD or Flux for continuous deployment
