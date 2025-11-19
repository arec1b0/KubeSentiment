# KubeSentiment Debugging Guide

> **Last Updated:** 2025-11-19
> **Purpose:** Help developers diagnose and fix common issues

## Overview

This guide provides debugging techniques and common issues for KubeSentiment API development. Each section includes symptoms, diagnosis steps, and solutions.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [API Issues](#api-issues)
3. [Model Issues](#model-issues)
4. [Cache Issues](#cache-issues)
5. [Batch Processing Issues](#batch-processing-issues)
6. [Logging & Tracing](#logging--tracing)
7. [Performance Issues](#performance-issues)
8. [Dependency Issues](#dependency-issues)

---

## Quick Diagnostics

### Health Check

```bash
# Quick health check
curl http://localhost:8000/api/v1/health

# Detailed health check
curl http://localhost:8000/api/v1/health/details

# Check model info
curl http://localhost:8000/api/v1/model-info
```

### Logs

```bash
# View application logs
tail -f logs/app.log

# Filter by level
tail -f logs/app.log | grep ERROR
tail -f logs/app.log | grep WARNING

# View Docker logs
docker-compose logs -f app
```

### System Info

```bash
# Check available resources
free -h                    # Memory (Linux)
top -l 1 | head -20       # System stats (macOS)
Task Manager               # Windows

# Check ports
lsof -i :8000             # Check if port 8000 is in use

# Check Python environment
python --version
pip list | grep fastapi
```

---

## API Issues

### Issue: "Model is not loaded" (E2001)

**Symptoms:**
- API returns 503 error with "Model is not loaded"
- All predictions fail with error code E2001

**Diagnosis:**

```bash
# 1. Check model status
curl http://localhost:8000/api/v1/model-info | jq

# 2. Check application logs
docker-compose logs app | grep -i "model"

# 3. Check if model file exists
ls -la models/

# 4. Check configuration
echo $MLOPS_MODEL_NAME
echo $MLOPS_MODEL_BACKEND
```

**Solutions:**

```bash
# Solution 1: Restart application
docker-compose restart app
# Or: Ctrl+C and restart uvicorn

# Solution 2: Force model reload (if available)
# Add endpoint or restart service

# Solution 3: Check model cache directory
export MLOPS_MODEL_CACHE_DIR="./models"
# Ensure directory exists and has proper permissions
ls -la ./models/

# Solution 4: Download model manually
python -c "
from transformers import AutoTokenizer, AutoModelForSequenceClassification
AutoTokenizer.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english')
AutoModelForSequenceClassification.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english')
"
```

### Issue: Invalid Text Input (E1001)

**Symptoms:**
- POST to `/predict` returns 400 "Invalid text input"
- Error message mentions empty or whitespace-only text

**Diagnosis:**

```python
import requests

# Debug request
payload = {"text": "   "}  # Only whitespace
response = requests.post("http://localhost:8000/api/v1/predict", json=payload)
print(response.json())  # Shows E1001 error
```

**Solutions:**

```python
# Solution 1: Validate text before sending
text = user_input.strip()
if not text or len(text) == 0:
    print("Error: Text cannot be empty")

# Solution 2: Check text length
max_length = 10000  # From API spec
if len(text) > max_length:
    print(f"Error: Text exceeds {max_length} character limit")

# Solution 3: Proper request format
payload = {
    "text": "I love this product!"  # Non-empty, valid text
}
response = requests.post("http://localhost:8000/api/v1/predict", json=payload)
```

### Issue: Slow API Response

**Symptoms:**
- Single prediction takes >500ms
- Even cached responses are slow
- Other services seem unaffected

**Diagnosis:**

```bash
# Check response headers for timing
curl -i http://localhost:8000/api/v1/predict \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}' | grep -i "x-inference"

# Measure latency with timing
time curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# Check if using cache
# "cached": false means model inference
# "cached": true means from Redis cache
```

**Solutions:**

```bash
# Solution 1: Check if Redis is running
redis-cli ping
# Should return: PONG

# Solution 2: Verify backend is ONNX (faster)
curl http://localhost:8000/api/v1/health | jq .backend
# Should show: "onnx"

# Solution 3: Monitor system resources
top         # Check CPU, memory usage
iostat      # Check disk I/O

# Solution 4: Profile the code
# See Performance Issues section below
```

### Issue: Batch Job Not Processing (E4001)

**Symptoms:**
- Batch submit returns "Batch service unavailable"
- Error code E4001
- Status endpoint shows "pending" indefinitely

**Diagnosis:**

```bash
# 1. Check batch service health
curl http://localhost:8000/api/v1/health/details | jq

# 2. Check queue status
curl http://localhost:8000/api/v1/batch/queue/status | jq

# 3. Check Kafka connectivity
docker-compose ps kafka
# Should show "Up"

# 4. View batch service logs
docker-compose logs -f app | grep -i batch
```

**Solutions:**

```bash
# Solution 1: Restart batch service
docker-compose restart app

# Solution 2: Check Kafka is running
docker-compose up -d kafka
# Wait a few seconds for it to start

# Solution 3: Check Redis for batch data
redis-cli keys "batch:*"
redis-cli dbsize

# Solution 4: Clear stuck jobs
redis-cli DEL batch:*  # Warning: Deletes all batch data
```

---

## Model Issues

### Issue: Different Results Between Backends

**Symptoms:**
- ONNX and PyTorch give different predictions for same input
- Score values differ significantly
- Labels occasionally differ

**Diagnosis:**

```python
import requests

# Test with both backends
for backend in ["onnx", "pytorch"]:
    response = requests.post(
        "http://localhost:8000/api/v1/predict",
        json={"text": "Test text"},
        headers={"X-Model-Backend": backend}  # If supported
    )
    result = response.json()
    print(f"{backend}: {result['label']} ({result['score']:.4f})")
```

**Solutions:**

```bash
# Solution 1: Expected behavior - small differences normal
# ONNX optimizations can cause minor differences (<5% variance)

# Solution 2: Use ONNX for production consistency
export MLOPS_MODEL_BACKEND=onnx

# Solution 3: Test boundary cases
# Labels change when confidence is near decision boundary
# Example: 0.50 score might be POSITIVE or NEUTRAL

# Solution 4: Update models together
# Ensure both ONNX and PyTorch models are same version
ls -la models/
```

### Issue: Model Memory Leak

**Symptoms:**
- Memory usage grows over time
- API becomes slower after hours of requests
- Restart temporarily fixes it

**Diagnosis:**

```bash
# Monitor memory usage
watch -n 1 'ps aux | grep python'

# Check model memory
python -c "
import torch
print(f'GPU Memory: {torch.cuda.memory_allocated() / 1e9:.2f}GB')
print(f'Cache Size: {torch.cuda.memory_cached() / 1e9:.2f}GB')
"

# Check Redis memory
redis-cli INFO memory | grep used_memory_human
```

**Solutions:**

```bash
# Solution 1: Clear cache periodically
redis-cli FLUSHDB  # Clear Redis
# Schedule: Every 6-12 hours

# Solution 2: Restart periodically
# Add health check + auto-restart
docker-compose up --health-interval=60s

# Solution 3: Monitor and alert
# Set up memory threshold alerts
# Restart when memory > 80% usage

# Solution 4: Update model factory
# Ensure models are properly unloaded
# Review: app/models/factory.py
```

---

## Cache Issues

### Issue: Cache Not Working (Always "cached": false)

**Symptoms:**
- All responses show `"cached": false`
- Response times unchanged on repeated requests
- Redis shows no keys

**Diagnosis:**

```bash
# Check Redis connection
redis-cli ping
# Should return: PONG

# Check health endpoint
curl http://localhost:8000/api/v1/health/details | jq '.dependencies[] | select(.component_name=="redis")'

# Check Redis configuration
echo $MLOPS_REDIS_ENABLED
echo $MLOPS_REDIS_HOST
echo $MLOPS_REDIS_PORT

# Check cached keys
redis-cli keys "*" | head
```

**Solutions:**

```bash
# Solution 1: Enable Redis
export MLOPS_REDIS_ENABLED=true

# Solution 2: Start Redis service
docker-compose up -d redis

# Solution 3: Check Redis logs
docker-compose logs redis

# Solution 4: Manual cache test
redis-cli SET testkey "testvalue"
redis-cli GET testkey
# Should return: "testvalue"

# Solution 5: Clear cache and retry
redis-cli FLUSHDB
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'
# On second request, should show cached: true
```

### Issue: Cache Stale Data

**Symptoms:**
- Model updated but getting old predictions
- Cache hits show outdated results
- Clearing cache fixes it temporarily

**Diagnosis:**

```bash
# Check cache TTL
redis-cli TTL prediction:*

# Check if cache was cleared after model update
redis-cli DBSIZE

# Check model update time
ls -la models/
date  # Current time
```

**Solutions:**

```bash
# Solution 1: Clear cache after model update
redis-cli FLUSHDB

# Solution 2: Set cache expiration
# Configure in app/core/config/
# Cache TTL: 24 hours (86400 seconds)
export MLOPS_CACHE_TTL=86400

# Solution 3: Disable cache during development
export MLOPS_REDIS_ENABLED=false

# Solution 4: Version cache keys
# Include model version in cache key
# prediction:{model_version}:{text_hash}
```

---

## Batch Processing Issues

### Issue: Batch Status Stuck on "processing"

**Symptoms:**
- Batch job status shows "processing" for hours
- Progress percentage doesn't change
- Job eventually times out

**Diagnosis:**

```bash
# Check batch service metrics
curl http://localhost:8000/api/v1/batch/metrics | jq

# Check specific job status
curl http://localhost:8000/api/v1/batch/status/job_id | jq

# Check Kafka consumers
docker-compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list

# Check Redis for job data
redis-cli GET "batch:job_id"
redis-cli HGETALL "batch:job_id:results"
```

**Solutions:**

```bash
# Solution 1: Check Kafka connectivity
docker-compose logs kafka

# Solution 2: Restart Kafka
docker-compose restart kafka
# Wait 30 seconds for startup

# Solution 3: Clear stuck batch jobs
redis-cli DEL batch:job_id

# Solution 4: Check job timeout
# Default: 300 seconds (5 minutes)
curl -X POST http://localhost:8000/api/v1/batch/predict \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["test"],
    "timeout_seconds": 600
  }'
```

### Issue: Batch Results Return Empty

**Symptoms:**
- Batch job shows "completed" but results are empty
- `"total_results": 0` in response
- No errors in logs

**Diagnosis:**

```bash
# Check job status first
curl http://localhost:8000/api/v1/batch/status/job_id | jq

# Check Redis for results
redis-cli HGETALL "batch:job_id:results"
redis-cli LLEN "batch:job_id:results"

# Check if job actually processed
redis-cli HGET "batch:job_id" "processed_count"
```

**Solutions:**

```bash
# Solution 1: Check batch processing completed
# Status must be "completed" before retrieving results
status=$(curl -s http://localhost:8000/api/v1/batch/status/job_id | jq .status)
if [ "$status" != "completed" ]; then
    echo "Job still processing..."
    sleep 10
fi

# Solution 2: Check pagination parameters
curl "http://localhost:8000/api/v1/batch/results/job_id?page=1&page_size=100" | jq

# Solution 3: Resubmit batch if data lost
# Resubmit the same texts to create a new job
```

---

## Logging & Tracing

### Enable Debug Logging

```bash
# Set log level to DEBUG
export MLOPS_LOG_LEVEL=DEBUG
export MLOPS_DEBUG=true

# Restart application
docker-compose restart app
# Or: Kill and restart uvicorn

# View debug logs
docker-compose logs -f app | grep DEBUG
```

### Find Request by Correlation ID

```bash
# Correlation ID is in request headers
CORRELATION_ID="550e8400-e29b-41d4a716-446655440000"

# Find all logs for this request
docker-compose logs app | grep "$CORRELATION_ID"

# Or in log file
grep "$CORRELATION_ID" logs/app.log
```

### Structured Logging Format

```json
{
  "timestamp": "2025-11-19T10:30:00Z",
  "level": "INFO",
  "logger": "app.api.routes.predictions",
  "message": "Sentiment prediction completed successfully",
  "operation": "predict_success",
  "correlation_id": "uuid",
  "request_id": "uuid",
  "label": "POSITIVE",
  "score": 0.9823,
  "inference_time_ms": 145.2,
  "cached": false
}
```

### Extract Specific Info

```bash
# Show only errors
docker-compose logs app | jq 'select(.level=="ERROR")'

# Show predictions with timing
docker-compose logs app | jq 'select(.operation=="predict_success") | {message, inference_time_ms}'

# Show failed predictions
docker-compose logs app | jq 'select(.operation=="predict_failed")'
```

---

## Performance Issues

### Slow Inference

**Symptoms:**
- Single predictions take >300ms even uncached
- ONNX backend not faster than PyTorch

**Diagnosis & Fix:**

```bash
# 1. Check if using ONNX backend
curl http://localhost:8000/api/v1/health | jq .backend

# 2. Check model file size (ONNX should be smaller)
ls -lh models/

# 3. Check CPU usage
top -b -n 1 | head -20

# 4. Profile the code (see tools below)

# Solution: Switch to ONNX
export MLOPS_MODEL_BACKEND=onnx
docker-compose restart app
```

### High Memory Usage

**Symptoms:**
- Memory usage increases over time
- Process crashes with OOM killer
- Swap space being used

**Diagnosis & Fix:**

```bash
# Check memory per process
ps aux | grep python | grep app

# Check memory by component
python -c "
import sys
import tracemalloc

tracemalloc.start()
# Import app
from app.main import app
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"

# Solutions:
# 1. Increase memory limit
docker-compose down
# Modify docker-compose.yml: deploy.resources.limits.memory
docker-compose up -d

# 2. Clear cache more frequently
redis-cli FLUSHDB --async

# 3. Limit model caching
export MLOPS_CACHE_MAX_SIZE=500  # Reduce from 1000
```

### Python Profiling

```python
# Add to your route or service
import cProfile
import pstats
import io

pr = cProfile.Profile()
pr.enable()

# Your code here
# ... model inference ...

pr.disable()
s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats(10)  # Top 10 functions
print(s.getvalue())
```

---

## Dependency Issues

### Issue: Import Errors

**Symptoms:**
- `ModuleNotFoundError: No module named 'fastapi'`
- `ImportError: cannot import name 'BaseModel'`

**Diagnosis:**

```bash
# Check virtual environment activated
echo $VIRTUAL_ENV
# Should show path to .venv

# Verify package installed
pip show fastapi

# Check Python path
python -c "import sys; print(sys.path)"
```

**Solutions:**

```bash
# Solution 1: Activate venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Solution 2: Reinstall package
pip install fastapi

# Solution 3: Reinstall all dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Solution 4: Use explicit Python from venv
.venv/bin/python -c "import fastapi; print(fastapi.__version__)"
```

### Issue: Dependency Conflicts

**Symptoms:**
- `pip install` fails with "conflicting requirements"
- Different packages require incompatible versions
- Tests fail but app runs

**Diagnosis:**

```bash
# Check installed versions
pip list

# Check specific package version
pip show pydantic
pip show fastapi

# See dependency tree
pip install pipdeptree
pipdeptree
```

**Solutions:**

```bash
# Solution 1: Update all packages
pip install --upgrade pip
pip install -r requirements.txt --upgrade

# Solution 2: Install compatible versions
pip install 'fastapi>=0.100,<0.110'

# Solution 3: Clear pip cache
pip cache purge
pip install -r requirements.txt

# Solution 4: Recreate venv completely
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Useful Debugging Tools

### cURL

```bash
# Show response headers and body
curl -i http://localhost:8000/api/v1/predict \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# Pretty print JSON response
curl ... | jq

# Follow redirects
curl -L http://localhost:8000/redirect

# Save response to file
curl ... > response.json

# Show request headers
curl -v ...
```

### jq (JSON Processor)

```bash
# Extract specific field
jq '.label' response.json

# Filter responses
jq 'select(.score > 0.8)' response.json

# Format output
curl ... | jq .

# Colorized output
curl ... | jq -C
```

### Docker Commands

```bash
# View service logs
docker-compose logs app

# Follow logs in real-time
docker-compose logs -f app

# View specific service
docker-compose logs redis

# Execute command in container
docker-compose exec app python -c "..."

# Connect to running container
docker-compose exec app bash
```

### Python Debugging

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()

# Print variables
print(f"Variable: {variable}")

# Use logging instead
import logging
logger = logging.getLogger(__name__)
logger.debug("Debug message", extra={"key": "value"})
```

---

## When to Ask for Help

If you've tried all solutions above, consider:

1. **Check documentation**
   - [API_REFERENCE.md](./API_REFERENCE.md)
   - [ERROR_HANDLING.md](./ERROR_HANDLING.md)
   - [CONFIGURATION_PROFILES.md](./CONFIGURATION_PROFILES.md)

2. **Review code**
   - Search for similar issues in codebase
   - Check git history for related changes
   - Review pull requests

3. **Ask on GitHub**
   - Include: OS, Python version, error messages
   - Provide: Steps to reproduce, logs
   - Link: Related issues or PRs

4. **Debug collaboratively**
   - Share reproduction script
   - Provide logs with DEBUG enabled
   - Use minimal example

---

**Last Updated:** 2025-11-19
