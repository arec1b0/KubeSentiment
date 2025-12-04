# Distroless Docker Image Deployment Guide

> **Last Updated:** 2025-01-27
> **Purpose:** Guide for building, deploying, and managing the distroless Docker image variant of KubeSentiment.

---

## Table of Contents

1. [Overview](#overview)
2. [What is Distroless?](#what-is-distroless)
3. [Building the Distroless Image](#building-the-distroless-image)
4. [Running the Distroless Container](#running-the-distroless-container)
5. [Directory Structure](#directory-structure)
6. [Health Checks](#health-checks)
7. [Pros and Cons](#pros-and-cons)
8. [Debugging Distroless Containers](#debugging-distroless-containers)
9. [Kubernetes Deployment](#kubernetes-deployment)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The distroless Docker image provides a **hardened, minimal runtime** for the KubeSentiment service with:

- **~30-50% smaller image size** compared to standard Python images
- **Minimal attack surface** - no shell, package managers, or unnecessary tools
- **CIS/NIST compliance friendly** - reduced CVE exposure
- **Production-ready** - optimized for security and performance

### Quick Start

```bash
# Build distroless image
make build-distroless

# Run container
docker run -p 8000:8000 sentiment-service:distroless

# Test health endpoint
curl http://localhost:8000/api/v1/health
```

---

## What is Distroless?

**Distroless** images are minimal container images that contain **only your application and its runtime dependencies**. They exclude:

- Shell (`/bin/sh`, `/bin/bash`)
- Package managers (`apt`, `yum`, `apk`)
- Debugging tools (`curl`, `wget`, `netcat`)
- System utilities (`ps`, `top`, `ls`)

### Why Use Distroless?

1. **Security**: Smaller attack surface reduces CVE exposure
2. **Compliance**: Easier to meet CIS/NIST security benchmarks
3. **Size**: Smaller images = faster deployments and lower storage costs
4. **Immutable**: Harder to modify containers at runtime (security benefit)

### Trade-offs

- **No shell access** - debugging requires Kubernetes ephemeral containers or debug images
- **No curl/wget** - health checks must use Python scripts or Kubernetes probes
- **Less flexibility** - harder to troubleshoot issues without debugging tools

---

## Building the Distroless Image

### Prerequisites

- Docker 20.10+ with BuildKit enabled
- Python 3.11+ dependencies installed (for local testing)

### Standard Build

```bash
# Using Makefile (recommended)
make build-distroless

# Manual build
docker build -f Dockerfile.distroless -t sentiment-service:distroless .

# With build arguments
docker build -f Dockerfile.distroless \
  --build-arg VERSION=1.0.0 \
  --build-arg REVISION=$(git rev-parse --short HEAD) \
  --build-arg BUILDTIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  -t sentiment-service:distroless .
```

### Debug Build

For debugging, use the debug variant of distroless:

```bash
# Build with debug image (includes shell and debugging tools)
make build-distroless-debug

# Or manually modify Dockerfile.distroless line 62:
# FROM gcr.io/distroless/python3-debian12:debug AS runtime
```

**Note:** The debug variant includes a shell and basic debugging tools, but is **not recommended for production**.

### Build Process

The distroless build uses a **multi-stage build**:

1. **Stage 1 (Builder)**: `python:3.11-slim`
   - Installs build dependencies
   - Installs Python packages to `/install`
   - Copies application code
   - Creates necessary directories

2. **Stage 2 (Runtime)**: `gcr.io/distroless/python3-debian12`
   - Copies only installed packages (`site-packages`)
   - Copies application code
   - Sets up environment variables
   - Configures non-root user (UID 65532)

### Build Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `VERSION` | Application version | `latest` |
| `REVISION` | Git revision/commit SHA | `unknown` |
| `BUILDTIME` | Build timestamp (ISO 8601) | Current time |
| `DEBUG_IMAGE` | Use debug distroless variant | `false` |

---

## Running the Distroless Container

### Basic Run

```bash
docker run -d \
  --name sentiment-distroless \
  -p 8000:8000 \
  sentiment-service:distroless
```

### With Environment Variables

```bash
docker run -d \
  --name sentiment-distroless \
  -p 8000:8000 \
  -e MLOPS_PROFILE=production \
  -e MLOPS_MODEL_BACKEND=onnx \
  -e MLOPS_REDIS_ENABLED=true \
  -e REDIS_HOST=redis-server \
  sentiment-service:distroless
```

### With Volume Mounts

```bash
docker run -d \
  --name sentiment-distroless \
  -p 8000:8000 \
  -v $(pwd)/config:/app/config:ro \
  sentiment-service:distroless
```

### Docker Compose

```yaml
version: '3.8'

services:
  sentiment-distroless:
    build:
      context: .
      dockerfile: Dockerfile.distroless
    ports:
      - "8000:8000"
    environment:
      - MLOPS_PROFILE=production
      - MLOPS_MODEL_BACKEND=onnx
    healthcheck:
      test: ["CMD", "python", "healthcheck.py"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

---

## Directory Structure

The distroless image has the following structure:

```
/app/
├── app/                    # Application source code
│   ├── api/               # API routes
│   ├── core/             # Core configuration
│   ├── models/           # ML models
│   └── ...
├── healthcheck.py        # Health check script
├── build-info.json       # Build metadata
├── logs/                 # Log directory (writable)
└── tmp/                  # Temporary files (writable)

/usr/local/lib/python3.11/site-packages/  # Python packages
```

### File Permissions

- All files owned by UID 65532 (distroless nonroot user)
- Application directories: `755`
- Logs and tmp directories: writable by nonroot user

---

## Health Checks

### Health Check Script

The distroless image includes `healthcheck.py` for container health checks:

```bash
# Manual health check
docker exec sentiment-distroless python healthcheck.py

# With custom parameters
docker exec sentiment-distroless python healthcheck.py \
  --host localhost \
  --port 8000 \
  --path /api/v1/health \
  --timeout 5 \
  --verbose
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HEALTHCHECK_HOST` | Host to check | `localhost` |
| `HEALTHCHECK_PORT` | Port to check | `8000` |
| `HEALTHCHECK_PATH` | Health endpoint path | `/health` |
| `HEALTHCHECK_TIMEOUT` | Request timeout (seconds) | `5` |

### Kubernetes Probes

**Important:** Distroless containers **cannot use shell-based HEALTHCHECK** directives. Use Kubernetes probes instead:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentiment-distroless
spec:
  template:
    spec:
      containers:
      - name: sentiment
        image: sentiment-service:distroless
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
```

### Health Endpoint

The service exposes health endpoints:

- **Quick check**: `GET /api/v1/health` (production) or `GET /health` (debug mode)
- **Detailed check**: `GET /api/v1/health/details`

---

## Pros and Cons

### Advantages ✅

1. **Security**
   - Minimal attack surface
   - No shell access reduces risk of command injection
   - Fewer CVEs in base image
   - CIS/NIST compliance friendly

2. **Size**
   - ~30-50% smaller than standard Python images
   - Faster image pulls and deployments
   - Lower storage costs

3. **Immutable**
   - Harder to modify containers at runtime
   - Encourages infrastructure-as-code practices

4. **Production-Ready**
   - Optimized for security and performance
   - Non-root execution by default

### Disadvantages ❌

1. **Debugging**
   - No shell for interactive debugging
   - Requires Kubernetes ephemeral containers or debug images
   - No `curl`, `wget`, or other debugging tools

2. **Flexibility**
   - Harder to troubleshoot issues
   - Cannot run ad-hoc commands
   - Requires proper health check implementation

3. **Development**
   - Not ideal for local development
   - Slower iteration cycle
   - Requires rebuilding for changes

### When to Use Distroless

**Use distroless when:**
- ✅ Production deployments requiring high security
- ✅ Compliance requirements (CIS, NIST)
- ✅ Minimal image size is important
- ✅ You have proper observability (metrics, logs, traces)

**Avoid distroless when:**
- ❌ Local development and debugging
- ❌ You need interactive shell access
- ❌ Rapid iteration and testing
- ❌ You lack proper monitoring/observability

---

## Debugging Distroless Containers

### Kubernetes Ephemeral Containers

The recommended way to debug distroless containers in Kubernetes:

```bash
# Create ephemeral debug container
kubectl debug sentiment-distroless-xxx -it --image=busybox -- sh

# Or use kubectl debug with custom image
kubectl debug sentiment-distroless-xxx -it \
  --image=python:3.11-slim \
  --target=sentiment-distroless-xxx \
  -- sh
```

### Debug Image Variant

Build and use the debug variant for troubleshooting:

```bash
# Build debug variant
make build-distroless-debug

# Run debug container
docker run -it --rm sentiment-service:distroless-debug sh
```

**Note:** Debug images include shell and debugging tools but are **not for production**.

### Logs and Metrics

Use application logs and metrics for debugging:

```bash
# View logs
docker logs sentiment-distroless
kubectl logs sentiment-distroless-xxx

# View metrics
curl http://localhost:8000/api/v1/metrics

# Check health
curl http://localhost:8000/api/v1/health/details
```

### Common Debugging Scenarios

#### Issue: Container exits immediately

```bash
# Check logs
docker logs sentiment-distroless

# Check if port is accessible
docker port sentiment-distroless

# Verify environment variables
docker inspect sentiment-distroless | jq '.[0].Config.Env'
```

#### Issue: Health check fails

```bash
# Test health endpoint manually
docker exec sentiment-distroless python healthcheck.py --verbose

# Check if service is listening
docker exec sentiment-distroless python -c "import socket; s = socket.socket(); s.bind(('0.0.0.0', 8000)); print('Port open')"
```

#### Issue: Permission denied

```bash
# Check file permissions (requires debug image)
docker run --rm --entrypoint sh sentiment-service:distroless-debug -c "ls -la /app"

# Verify nonroot user
docker run --rm --entrypoint sh sentiment-service:distroless-debug -c "id"
```

---

## Kubernetes Deployment

### Helm Chart

Update Helm values to use distroless image:

```yaml
# values-production.yaml
image:
  repository: sentiment-service
  tag: distroless
  pullPolicy: IfNotPresent

# Use distroless-specific Dockerfile
dockerfile: Dockerfile.distroless
```

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentiment-distroless
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sentiment-distroless
  template:
    metadata:
      labels:
        app: sentiment-distroless
    spec:
      containers:
      - name: sentiment
        image: sentiment-service:distroless
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: MLOPS_PROFILE
          value: "production"
        - name: MLOPS_MODEL_BACKEND
          value: "onnx"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        securityContext:
          runAsNonRoot: true
          runAsUser: 65532
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false  # Allow logs/tmp writes
          capabilities:
            drop:
            - ALL
```

### Security Context

Distroless containers run as **non-root (UID 65532)** by default. Configure Kubernetes security context:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 65532
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false  # Set to true if using volume mounts for logs
  capabilities:
    drop:
    - ALL
```

---

## Troubleshooting

### Common Issues

#### 1. Container won't start

**Symptoms:** Container exits immediately with no logs

**Solutions:**
- Check application logs: `docker logs <container>`
- Verify ENTRYPOINT format (must be JSON array in distroless)
- Check Python path: `PYTHONPATH=/usr/local/lib/python3.11/site-packages`
- Verify all dependencies are installed

#### 2. Import errors

**Symptoms:** `ModuleNotFoundError` or `ImportError`

**Solutions:**
- Verify `site-packages` are copied correctly
- Check `PYTHONPATH` environment variable
- Ensure all dependencies in `requirements.txt` are installed
- Verify Python version matches (3.11)

#### 3. Permission denied

**Symptoms:** Cannot write to logs or tmp directories

**Solutions:**
- Verify directories are owned by UID 65532
- Check directory permissions (should be writable)
- Use volume mounts for persistent storage
- Set `readOnlyRootFilesystem: false` in Kubernetes

#### 4. Health check fails

**Symptoms:** Kubernetes probes failing

**Solutions:**
- Use HTTP probes instead of exec probes
- Verify health endpoint path (`/api/v1/health` in production)
- Check service is listening on correct port
- Increase `initialDelaySeconds` for slow startup

#### 5. Cannot debug container

**Symptoms:** Need shell access for troubleshooting

**Solutions:**
- Use Kubernetes ephemeral containers: `kubectl debug`
- Build debug variant: `make build-distroless-debug`
- Use application logs and metrics
- Deploy sidecar container with debugging tools

### Getting Help

- **Logs**: Check application logs and metrics
- **Documentation**: See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- **Issues**: Check GitHub/GitLab issues
- **Health Check**: Use `healthcheck.py` script with `--verbose` flag

---

## Additional Resources

- [Distroless Images](https://github.com/GoogleContainerTools/distroless)
- [Kubernetes Ephemeral Containers](https://kubernetes.io/docs/concepts/workloads/pods/ephemeral-containers/)
- [Container Security Best Practices](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Project Documentation](../README.md)

---

**Note:** This guide assumes familiarity with Docker and Kubernetes. For basic setup, see [QUICKSTART.md](../setup/QUICKSTART.md).
