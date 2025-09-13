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

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

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
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Deployment

Use the provided Dockerfile for containerized deployment in production environments.

## Cleanup

To stop and remove the container:

```bash
docker stop my-sentiment-app
docker rm my-sentiment-app
```

## Development Roadmap

Future enhancements planned:
- Kubernetes deployment configurations
- Advanced monitoring and alerting
- Model versioning and A/B testing
- CI/CD pipeline integration
- Distributed tracing and logging
- Multi-model support
- Batch processing capabilities

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
