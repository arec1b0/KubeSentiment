# KubeSentiment: MLOps Sentiment Analysis Microservice

![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**KubeSentiment** is a production-ready sentiment analysis microservice built with FastAPI and designed for scale and reliability using modern MLOps best practices. It's containerized with Docker, deployable on Kubernetes with Helm, and comes with a comprehensive observability stack.

## ✨ Key Features

- **Real-time AI Inference**: High-performance sentiment analysis using pre-trained transformer models.
- **ONNX Optimization**: Support for ONNX Runtime for faster inference and lower resource consumption.
- **Cloud-Native**: Designed for Kubernetes with auto-scaling, health checks, and zero-downtime deployments.
- **Full Observability**: Comes with pre-configured Prometheus metrics, Grafana dashboards, and structured logging.
- **Infrastructure as Code**: Reproducible infrastructure using Terraform.
- **Automated CI/CD**: GitHub Actions for automated testing, security scanning, and deployment.
- **Secure**: Integrates with HashiCorp Vault for secrets management and includes network policies for security.

## 📚 Documentation

For detailed information about the project, please refer to our documentation:

- **[Architecture Overview](docs/architecture.md)**: A deep dive into the system architecture, components, and design patterns.
- **[Contributing Guide](CONTRIBUTING.md)**: Instructions for setting up your development environment and contributing to the project.
- **[Deployment Guide](docs/setup/deployment-guide.md)**: Step-by-step instructions for deploying the application.
- **[Quick Start](docs/setup/QUICKSTART.md)**: Get the application and its monitoring stack running in minutes.

## 🚀 Quick Demo

1.  **Start the service locally using Docker Compose:**
    ```bash
    docker-compose up
    ```

2.  **Send a prediction request:**
    ```bash
    curl -X POST "http://localhost:8000/predict" \
         -H "Content-Type: application/json" \
         -d '{"text": "This is an amazing project!"}'
    ```

    **Response:**
    ```json
    {
      "label": "POSITIVE",
      "score": 0.999
    }
    ```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) to get started.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
