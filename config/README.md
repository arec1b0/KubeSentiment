# Configuration Structure

This directory contains all configuration files for the MLOps Sentiment Analysis Service.

## Directory Structure

### `monitoring/`
Contains configuration for the observability stack:
- **Prometheus**: `prometheus.yml`, `prometheus-rules.yaml`
- **Grafana**: Dashboards (`*.json`) and datasource provisioning (`*.yaml`)
- **AlertManager**: `alertmanager.yml`
- **Loki/Promtail**: Logging configuration (`loki-config.yaml`, `promtail-config.yaml`)
- **Logstash**: ELK stack configuration (`logstash.conf`, `logstash.yml`)

### `infrastructure/`
Contains infrastructure service configurations:
- `kafka.yaml`: Kafka consumer/producer settings
- `async_batch.yaml`: Async batch processing settings
  (previously in the root-level `configs/` directory)

### `environments/`
Contains environment-specific overrides:
- `environments.yaml`: Deployment settings for Development, Staging, and Production

## Usage

These configurations are mounted into containers via `docker-compose.yml` and `docker-compose.observability.yml`.
When deploying to Kubernetes, these values are typically managed via Helm chart values or ConfigMaps.
