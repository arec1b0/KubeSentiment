# Dockerfile Guide

This project provides multiple Dockerfiles optimized for different use cases.

## Decision Matrix

| Use Case | Dockerfile | Reason |
|----------|-----------|--------|
| **Local Development** | `Dockerfile` | Faster builds, includes build tools, shell access for debugging. |
| **Production (Standard)** | `Dockerfile.optimized` | Balanced size/performance. Pre-compiled assets. |
| **Production (Secure)** | `Dockerfile.distroless` | **Recommended**. Minimal attack surface, no shell, non-root user. |

## Build Commands

### Local Development
```bash
make build-dev
# OR
docker build -f Dockerfile -t sentiment:dev .
```

### Production (Standard)
```bash
make build-prod
# OR
docker build -f Dockerfile.optimized -t sentiment:prod .
```

### Production (Secure)
```bash
make build-secure
# OR
docker build -f Dockerfile.distroless -t sentiment:secure .
```

## Details

### Dockerfile (Base)
- Based on `python:3.11-slim`
- Includes `build-essential` and `curl`
- Good for debugging and rapid iteration

### Dockerfile.optimized
- Multi-stage build
- Includes performance optimizations (ONNX runtime tuning)
- Pre-downloads and bakes models into the image (faster startup)

### Dockerfile.distroless
- Based on `gcr.io/distroless/python3-debian12`
- No OS package manager, shells, or standard utilities
- Strict security posture
- Requires ephemeral containers for debugging
