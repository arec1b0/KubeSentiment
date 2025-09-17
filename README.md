# MLOps Sentiment Analysis Microservice

A production-ready sentiment analysis microservice built with FastAPI and containerized with Docker. This project demonstrates MLOps best practices including containerization, API design, monitoring, and automated testing capabilities.

## Architecture Overview

This microservice implements a sentiment analysis solution using:

- **FastAPI** for high-performance API development
- **DistilBERT** for efficient sentiment classification
- **Docker** for containerization and deployment
- **Uvicorn** as the ASGI server

## Features

- **Real-time sentiment analysis** using pre-trained transformer models
- **Health monitoring** with comprehensive endpoint diagnostics
- **Performance metrics** and system monitoring capabilities
- **Automatic API documentation** with Swagger UI and ReDoc
- **Graceful error handling** with fallback mechanisms
- **Containerized deployment** for scalability and portability

## Quick Start

### Prerequisites

- Docker installed and running
- Python 3.9+ (for local development)

### 1. Build Docker Image

```bash
docker build -t sentiment-service:0.1 .
```

### 2. Run Container

```bash
docker run -d -p 8000:8000 --name my-sentiment-app sentiment-service:0.1
```

### 3. Verify Deployment

Check if the container is running:

```bash
docker ps
```

## API Endpoints

### Health Check

**GET** `/health`

Provides service health status and model availability.

```bash
curl -X GET http://localhost:8000/health
```

**Response:**

```json
{"status":"ok","model_status":"ok"}
```

### Metrics

**GET** `/metrics`

Returns system metrics and performance indicators.

```bash
curl -X GET http://localhost:8000/metrics
```

### Sentiment Prediction

**POST** `/predict`

Analyzes text sentiment and returns classification results.

```bash
curl -X POST http://localhost:8000/predict \
-H "Content-Type: application/json" \
-d '{"text": "I love weekend projects, they make me feel so productive."}'
```

**Response (Positive):**

```json
{"label":"POSITIVE","score":0.99}
```

**Example with negative sentiment:**

```bash
curl -X POST http://localhost:8000/predict \
-H "Content-Type: application/json" \
-d '{"text": "I hate spending my weekend debugging Docker containers."}'
```

**Response (Negative):**

```json
{"label":"NEGATIVE","score":0.99}
```

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** <http://localhost:8000/docs>
- **ReDoc:** <http://localhost:8000/redoc>

## Technical Specifications

### Model Details

- **Model**: DistilBERT base uncased fine-tuned on SST-2
- **Input**: Text strings (any length)
- **Output**: Binary sentiment classification (POSITIVE/NEGATIVE) with confidence scores
- **Performance**: Optimized for CPU inference

### System Requirements

- **Memory**: Minimum 2GB RAM
- **CPU**: Multi-core recommended for concurrent requests
- **Storage**: ~500MB for model weights and dependencies

### Response Time

- **Target**: < 100ms per request
- **Monitoring**: Response times tracked via X-Process-Time-MS header

## Monitoring and Observability

The service includes built-in monitoring capabilities:

- Health check endpoint for service availability
- Metrics endpoint for system performance
- Process time tracking for all requests
- Model status monitoring with graceful degradation

## Error Handling

The service implements robust error handling:

- Model loading failures result in mock responses with clear indicators
- Input validation using Pydantic models
- Graceful degradation when GPU is unavailable
- Comprehensive logging for debugging

## Deployment

### Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

```bash
python run.py
```

### Docker Deployment

```bash
# Build and run with Docker
docker build -t sentiment-service:latest .
docker run -d -p 8000:8000 --name sentiment-app sentiment-service:latest
```

### Kubernetes Deployment

#### Quick Start with Minikube

```bash
# 1. Setup Minikube
bash scripts/setup-minikube.sh

# 2. Deploy the service
bash scripts/deploy.sh

# 3. Access the service
curl http://$(minikube ip):30800/health
```

#### Quick Start with Kind

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

# Optional: Apply Ingress and HPA
kubectl apply -f k8s/ingress.yaml  # Requires NGINX Ingress Controller
kubectl apply -f k8s/hpa.yaml      # Requires metrics server

# Check deployment
kubectl get pods -n mlops-sentiment
kubectl get services -n mlops-sentiment
```

### Production Deployment

Use the provided Kubernetes manifests for production deployment with proper resource limits, health checks, and autoscaling capabilities.

## Cleanup

### Docker Cleanup

```bash
# Stop and remove Docker container
docker stop sentiment-app
docker rm sentiment-app
docker rmi sentiment-service:latest
```

### Kubernetes Cleanup

```bash
# Remove all Kubernetes resources
bash scripts/cleanup.sh

# Or manually delete namespace
kubectl delete namespace mlops-sentiment

# Stop local clusters
minikube stop    # For Minikube
kind delete cluster --name mlops-sentiment  # For Kind
```

## Development Roadmap

Future enhancements planned:

- ✅ Kubernetes deployment configurations
- Advanced monitoring and alerting (Prometheus/Grafana)
- Model versioning and A/B testing
- CI/CD pipeline integration (GitHub Actions/GitLab CI)
- Distributed tracing and logging (Jaeger/OpenTelemetry)
- Multi-model support
- Batch processing capabilities
- Helm charts for easier Kubernetes deployment
- GitOps integration (ArgoCD/Flux)

## Contributing

This project follows MLOps best practices and welcomes contributions for:

- Performance optimizations
- Additional model integrations
- Enhanced monitoring capabilities
- Documentation improvements

## License

MIT License - see LICENSE file for details.

## Author

Daniil Krizhanovskyi - AI Architect specializing in MLOps and production ML systems.
