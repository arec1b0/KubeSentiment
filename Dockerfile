# Multi-stage build for production-ready ML service
FROM python:3.11-slim as base

# Build arguments for CI/CD integration
ARG BUILDTIME
ARG VERSION
ARG REVISION

# Set build metadata as labels
LABEL org.opencontainers.image.created="${BUILDTIME}"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.revision="${REVISION}"
LABEL org.opencontainers.image.title="MLOps Sentiment Analysis Service"
LABEL org.opencontainers.image.description="Production-ready FastAPI microservice for sentiment analysis"
LABEL org.opencontainers.image.source="https://github.com/your-org/mlops-sentiment"
LABEL org.opencontainers.image.licenses="MIT"

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Build metadata as env vars
    BUILD_VERSION="${VERSION}" \
    BUILD_REVISION="${REVISION}" \
    BUILD_TIME="${BUILDTIME}"

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Install system dependencies with security updates
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install Python dependencies
COPY requirements.txt .

# Install Python dependencies with security checks
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    # Remove build dependencies to reduce image size
    apt-get purge -y build-essential && \
    apt-get autoremove -y

# Copy application code
COPY app/ ./app/
COPY .env .env* ./

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Add build info endpoint data
RUN echo '{"version":"'${VERSION}'","revision":"'${REVISION}'","build_time":"'${BUILDTIME}'"}' > /app/build-info.json

# Enhanced health check with proper error handling
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command with proper signal handling
CMD ["python", "-m", "uvicorn", "app.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "1", \
    "--access-log", \
    "--log-config", "/dev/null"]
