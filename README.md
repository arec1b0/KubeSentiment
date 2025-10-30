# KubeSentiment: Production-Ready MLOps Sentiment Analysis Microservice

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/arec1b0/KubeSentiment/actions)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/arec1b0/KubeSentiment/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](https://example.com/coverage)
[![Code Quality](https://img.shields.io/badge/quality-A-brightgreen.svg)](https://example.com/quality)

**KubeSentiment** is a production-grade, scalable, and observable sentiment analysis microservice. Built with FastAPI and designed for Kubernetes, it embodies modern MLOps best practices from the ground up, providing a robust foundation for deploying machine learning models in a cloud-native environment.

## ✨ Why KubeSentiment?

This project was built to serve as a comprehensive, real-world example of MLOps principles in action. It addresses common challenges in deploying ML models, such as:

- **Scalability**: Handles high-throughput inference with Kubernetes Horizontal Pod Autoscaling.
- **Observability**: Offers deep insights into model and system performance with a pre-configured monitoring stack.
- **Reproducibility**: Ensures consistent environments from development to production with Docker, Terraform, and Helm.
- **Security**: Integrates best practices for secret management, container security, and network policies.
- **Automation**: Features a complete CI/CD pipeline for automated testing and deployment.

## 🚀 Key Features

- **High-Performance AI Inference**: Leverages state-of-the-art transformer models for real-time sentiment analysis.
- **ONNX Optimization**: Supports ONNX Runtime for accelerated inference and reduced resource consumption.
- **Cloud-Native & Kubernetes-Ready**: Designed for Kubernetes with auto-scaling, health checks, and zero-downtime deployments via Helm.
- **Full Observability Stack**: Integrated with Prometheus, Grafana, and structured logging for comprehensive monitoring.
- **Infrastructure as Code (IaC)**: Reproducible infrastructure defined with Terraform.
- **Automated CI/CD Pipeline**: GitHub Actions for automated testing, security scanning (Trivy), and deployment.
- **Secure by Design**: Integrates with HashiCorp Vault for secrets management and includes hardened network policies.
- **Comprehensive Benchmarking**: Includes a full suite for performance and cost analysis across different hardware configurations.

## 🏛️ Architecture Overview

The system is designed as a modular, cloud-native application. At its core is the FastAPI service, which serves the sentiment analysis model. This service is containerized and deployed to a Kubernetes cluster, with a surrounding ecosystem for monitoring, security, and traffic management.

```mermaid
graph TD
    subgraph "Clients"
        A[Web/Mobile Apps]
        B[Batch Jobs]
        C[API Consumers]
    end

    subgraph "Infrastructure Layer (Kubernetes Cluster)"
        D[Ingress Controller] --> E{Sentiment Service};
        E --> F[Pod 1];
        E --> G[Pod 2];
        E --> H[...];

        subgraph "Sentiment Analysis Pod"
            direction LR
            I[FastAPI App] --> J["Sentiment Model - ONNX/PyTorch"];
        end

        F ----> I;

        subgraph "Observability Stack"
            K[Prometheus] -- Scrapes --> E;
            L[Grafana] -- Queries --> K;
            M[Alertmanager] -- Alerts from --> K;
            M --> N[Notifications];
        end

        subgraph "Security"
            O[HashiCorp Vault] <--> F;
        end
    end

    A --> D;
    B --> D;
    C --> D;

    style F fill:#lightgreen
    style G fill:#lightgreen
    style H fill:#lightgreen
```

For a deeper dive into the technical design, components, and patterns used, please see the **[Architecture Document](docs/architecture.md)**.

## 🏁 Getting Started

### Prerequisites

Ensure you have the following tools installed on your local machine:

- **Python 3.11+**
- **Docker & Docker Compose**
- **kubectl** (for Kubernetes interaction)
- **Helm 3+** (for Kubernetes package management)
- **make** (optional, for using Makefile shortcuts)

### 1. Local Development (Docker Compose)

This is the quickest way to get the service running on your local machine.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/arec1b0/KubeSentiment.git
    cd KubeSentiment
    ```

2.  **Install dependencies:**
    ```bash
    make install-dev
    ```

3.  **Start the service:**
    ```bash
    docker-compose up --build
    ```
    This will build the Docker image and start the FastAPI service.

4.  **Test the service:**
    Open a new terminal and send a prediction request:

    > **Note on Ports:** The application runs on port 8000 inside the container. When using Docker Compose, this is mapped to `localhost:8000`. In Kubernetes, you can use `kubectl port-forward` to map to any local port (e.g., `8080:80` or `8000:8000`).

    ```bash
    curl -X POST "http://localhost:8000/predict" \
         -H "Content-Type: application/json" \
         -d '{"text": "This is an amazing project and the setup was so easy!"}'
    ```

    You should receive a response like:
    ```json
    {
      "text": "This is an amazing project and the setup was so easy!",
      "sentiment": {
        "label": "POSITIVE",
        "score": 0.9998
      }
    }
    ```

### 2. Full Kubernetes Deployment with Monitoring

To experience the full MLOps stack, including the monitoring dashboard, you can deploy the entire system to a Kubernetes cluster (e.g., Minikube, kind, or a cloud provider's cluster).

Our **[Quick Start Guide](docs/setup/QUICKSTART.md)** provides a one-line script to get the application and its full monitoring stack running in minutes.

```bash
# Follow the instructions in the Quick Start guide
./scripts/setup-monitoring.sh
```

This will deploy the application along with Prometheus for metrics, Grafana for dashboards, and Alertmanager for alerts.

## 💻 Usage

### API Endpoints

The service exposes several key endpoints:

| Method | Endpoint              | Description                                      |
|--------|-----------------------|--------------------------------------------------|
| `POST` | `/api/v1/predict`            | Analyzes the sentiment of the input text.        |
| `POST`   | `/api/v1/batch/predict`      | Submits a batch of texts for asynchronous prediction. |
| `GET`    | `/api/v1/batch/status/{job_id}` | Checks the status of a batch prediction job.      |
| `GET`    | `/api/v1/batch/results/{job_id}`| Retrieves the results of a completed batch job. |
| `GET`  | `/api/v1/health`             | Health check endpoint for readiness/liveness.    |
| `GET`  | `/api/v1/metrics`            | Exposes Prometheus metrics.                      |
| `GET`  | `/api/v1/model-info`  | Returns metadata about the loaded ML model.      |

> **Note on API Versioning:** All endpoints use the `/api/v1` prefix in production mode. When running in debug mode (`MLOPS_DEBUG=true`), the `/api/v1` prefix is omitted for easier local development (e.g., `/predict` instead of `/api/v1/predict`).

### Configuration

The application is configured via environment variables, which are documented in our **[Deployment Guide](docs/setup/deployment-guide.md)**. For Kubernetes deployments, these are managed via `ConfigMap` and `Secret` objects, which are defined in the Helm chart.

> **Note:** `.env` files are intentionally _not_ baked into the container image. Provide any sensitive or environment-specific settings at runtime using the mechanisms supported by your orchestrator.

#### Supplying configuration at runtime

- **Docker / Docker Compose:** pass variables with `--env-file` or individual `-e` flags when running the container.
- **Kubernetes:** mount configuration with `envFrom` or `env` entries sourced from a `ConfigMap` or `Secret`. Sensitive values (API keys, credentials) should be stored in a `Secret`, while non-sensitive defaults can live in a `ConfigMap`.

Example Kubernetes manifest snippet:

```yaml
envFrom:
  - configMapRef:
      name: mlops-sentiment-config
  - secretRef:
      name: mlops-sentiment-secrets
```

This approach keeps secrets out of the image and allows you to tailor configuration per environment (dev/staging/prod) without rebuilding the container.

## 📊 Benchmarking

A key part of this project is its ability to measure performance and cost-effectiveness. The `benchmarking/` directory contains a powerful suite for running load tests against the service on different hardware configurations.

This allows you to answer questions like:
- "Is a GPU instance more cost-effective than a CPU instance for my workload?"
- "What is the maximum RPS our current configuration can handle?"

The benchmarking scripts generate a comprehensive HTML report with performance comparisons, cost analysis, and resource utilization charts. See the **[Benchmarking README](benchmarking/README.md)** for more details.

### Latest Kafka Consumer Benchmark Snapshot

| Scenario | Batch Size | Messages Processed | Wall Time (s) | Approx. Throughput (msg/s) |
|----------|------------|--------------------|----------------|-----------------------------|
| Synthetic workload executed with the in-repo `MockModel` using the high-throughput Kafka consumer (no external brokers) | 1,000 | 1,000 | 0.0095 | ~105,700 |

> **How it was measured:** `python benchmarking` helper script (see commit history) instantiates `HighThroughputKafkaConsumer` with the same `MockModel` used in the test suite and processes 1,000 synthetic messages in a single batch. This mirrors the high-throughput path without requiring a live Kafka cluster, making it reproducible in constrained environments.

> **Tip:** For end-to-end benchmarks against a running Kafka cluster, use `benchmarking/kafka_performance_test.py`. It exercises producer/consumer I/O, DLQ handling, and Prometheus instrumentation at scale.

## 🤝 Contributing

We welcome contributions of all kinds! Whether it's reporting a bug, improving documentation, or submitting a new feature, your help is appreciated.

Please read our **[Contributing Guide](CONTRIBUTING.md)** to get started with the development setup, code quality standards, and pull request process.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
