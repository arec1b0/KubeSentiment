# KubeSentiment Troubleshooting Guide

> **Last Updated:** 2025-11-19
> **Quick Fix Time:** 5-30 minutes for most issues
> **See Also:** [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) for detailed debugging techniques

## Quick Troubleshooting Decision Tree

```
Is the application running?
├─ No → See "Application Won't Start"
└─ Yes → Is it responding to requests?
    ├─ No → See "Connection Issues"
    └─ Yes → Are the responses correct?
        ├─ No → See "Incorrect Results"
        └─ Yes → Application is working!
```

---

## Startup Issues

### Application Won't Start

**Problem:** `uvicorn` fails to start or crashes immediately

**Quick Fixes (Try These First):**

```bash
# 1. Check Python version
python3 --version  # Must be 3.11+

# 2. Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 3. Check dependencies installed
pip list | grep -E "fastapi|pydantic|uvicorn"

# 4. Install missing dependencies
pip install -r requirements.txt

# 5. Try running directly
PROFILE=local python -m uvicorn app.main:app --reload
```

**If still failing, check:**

- **Python import error**: `python -c "import app.main"`
- **Port already in use**: `lsof -i :8000` (macOS/Linux)
- **Syntax errors**: `python -m py_compile app/**/*.py`

**Solutions by Error Type:**

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError` | Install missing dependency: `pip install <module>` |
| `Port 8000 in use` | Kill process: `lsof -i :8000 \| grep LISTEN \| awk '{print $2}' \| xargs kill -9` |
| `YAML/Config error` | Check `.env` file syntax, remove invalid characters |
| `Permission denied` | Check file permissions, try `chmod +x scripts/` |

---

## Connection Issues

### Cannot Connect to API

**Symptom:** `Connection refused` or `Connection timeout`

**Diagnosis:**

```bash
# Is server running?
curl http://localhost:8000/api/v1/health

# Is port open?
netstat -an | grep 8000

# Check firewall (macOS)
sudo lsof -i :8000

# Check Windows
netstat -ano | findstr :8000
```

**Solutions:**

```bash
# 1. Ensure server is running
# Terminal 1: Start server
PROFILE=local uvicorn app.main:app --reload

# Terminal 2: Test connection
curl http://localhost:8000/api/v1/health

# 2. Try different hostname
curl http://127.0.0.1:8000/api/v1/health

# 3. Check if running in container
docker-compose ps
docker-compose logs app

# 4. Use correct URL (check MLOPS_SERVER_HOST, MLOPS_SERVER_PORT)
```

### DNS/Network Issues

**Symptom:** `Name or service not known` or `Temporary failure in name resolution`

**Solutions:**

```bash
# 1. Use localhost instead of hostname
curl http://localhost:8000  # Instead of http://mypc.local:8000

# 2. Check DNS in Docker
docker-compose exec app ping google.com

# 3. Use IP address
curl http://127.0.0.1:8000
```

---

## Request/Response Issues

### 400 Bad Request - Invalid Input

**Symptom:** POST request returns 400 with error code E1001

**Common Causes:**

| Issue | Solution |
|-------|----------|
| Empty text | Ensure `"text"` field is not empty or whitespace-only |
| Text too long | Keep text under 10,000 characters |
| Missing field | Include `"text"` field in JSON body |
| Invalid JSON | Use proper JSON format, quote strings with `"` |
| Wrong content-type | Set header: `Content-Type: application/json` |

**Test with:**

```bash
# Correct request
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this!"}'

# Common mistakes to avoid
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": ""}'  # ❌ Empty text

curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{text: "I love this!"}'  # ❌ Missing quotes around key
```

### 503 Service Unavailable - Model Not Loaded

**Symptom:** Returns error code E2001 "Model is not loaded"

**Diagnosis & Fix:**

```bash
# Step 1: Check model status
curl http://localhost:8000/api/v1/model-info | jq

# Step 2: Check application logs
docker-compose logs app | grep -i model

# Step 3: Check model file exists
ls -la models/

# Step 4: Restart application
docker-compose restart app
# Wait 30 seconds for model to load

# Step 5: Verify model is loaded
curl http://localhost:8000/api/v1/model-info | jq .is_loaded
# Should show: true
```

**If still not working:**

```bash
# Force model download
python -c "
from transformers import AutoModel
AutoModel.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english')
"

# Check disk space
df -h
# Ensure >500MB free space

# Check model cache directory
export MLOPS_MODEL_CACHE_DIR='./models'
mkdir -p ./models
chmod 755 ./models
```

### 404 Not Found

**Symptom:** Endpoint returns 404 error

**Solutions:**

```bash
# 1. Check correct endpoint path
# ✅ /api/v1/predict
# ❌ /predict (unless in local mode)
# ❌ /api/v1/predictions (should be singular)

# 2. Try health check to verify server
curl http://localhost:8000/api/v1/health

# 3. Check API prefix
PROFILE=local  # Uses /predict (no /api/v1)
PROFILE=development  # Uses /api/v1/predict

# 4. List all available endpoints
curl http://localhost:8000/docs  # See Swagger UI
```

### 500 Internal Server Error

**Symptom:** API returns 500 error with generic message

**Diagnosis:**

```bash
# 1. Check application logs
docker-compose logs app | grep -A5 ERROR

# 2. Enable debug mode
export MLOPS_DEBUG=true
export MLOPS_LOG_LEVEL=DEBUG

# 3. Restart with debug
docker-compose restart app

# 4. Try request again and check logs
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# 5. Check error details
docker-compose logs app | tail -50
```

---

## Performance Issues

### API Response Very Slow (>500ms)

**Symptom:** Single prediction takes several seconds

**Quick Checks:**

```bash
# Check response timing
curl -w "@curl-format.txt" -o /dev/null -s \
  -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# Check if cached
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}' | jq .cached
# Should show: true (on second request)

# Check system resources
top -l 1 | head -20  # macOS
free -h              # Linux
```

**Solutions:**

```bash
# 1. Check if using ONNX backend (faster)
curl http://localhost:8000/api/v1/health | jq .backend

# 2. If using PyTorch, switch to ONNX
export MLOPS_MODEL_BACKEND=onnx
docker-compose restart app

# 3. Ensure Redis is running for caching
docker-compose ps redis
# If not running: docker-compose up -d redis

# 4. Check system CPU/Memory
# Is system busy with other processes?
# Kill unnecessary processes or restart

# 5. Profile the code
# See DEBUGGING_GUIDE.md for profiling steps
```

### Batch Processing Too Slow

**Symptom:** Batch job with 100 items takes >5 minutes

**Typical Performance:**

- 100 items: 10-30 seconds
- 500 items: 45-90 seconds
- 1000 items: 90-180 seconds

**If slower than expected:**

```bash
# 1. Check system resources
docker stats

# 2. Check if Kafka is bottleneck
docker-compose logs kafka | grep -i error

# 3. Adjust batch size
# Smaller batches = faster per-item but more overhead
# Optimal: 100-500 items

# 4. Check Redis queue
redis-cli DBSIZE

# 5. Monitor batch metrics
curl http://localhost:8000/api/v1/batch/metrics | jq
```

---

## Docker/Docker-Compose Issues

### Container Won't Start

**Symptom:** `docker-compose up` fails or container exits immediately

**Diagnosis:**

```bash
# Check logs
docker-compose logs app

# Check exit code
docker-compose ps
# Look for "Exited (1)" status

# Try building again
docker-compose build --no-cache

# Check Docker daemon
docker info
```

**Common Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Port already in use | `docker-compose down` or `lsof -i :8000 \| grep LISTEN` |
| Out of memory | Increase Docker memory limit in settings |
| Image build failed | Check Dockerfile, build logs |
| Volume permission error | Check directory permissions: `ls -la ./` |

### Redis Connection Failed

**Symptom:** `ConnectionError: Error 111 connecting to localhost:6379`

**Solutions:**

```bash
# 1. Start Redis
docker-compose up -d redis

# 2. Wait for startup
sleep 10

# 3. Test connection
redis-cli ping
# Should return: PONG

# 4. Check if running
docker-compose ps redis

# 5. View logs
docker-compose logs redis

# 6. Reset Redis
docker-compose down
docker volume rm kubesentiment_redis_data  # Remove data
docker-compose up -d redis
```

### Kafka Connection Failed

**Symptom:** `ConnectionError to Kafka broker` or batch processing fails

**Solutions:**

```bash
# 1. Start Kafka
docker-compose up -d kafka

# 2. Wait for startup (takes ~30 seconds)
sleep 30

# 3. Check if running
docker-compose ps kafka

# 4. Test connection
docker-compose exec kafka kafka-broker-api-versions \
  --bootstrap-server localhost:9092

# 5. View logs
docker-compose logs kafka

# 6. Restart Kafka
docker-compose restart kafka
sleep 30
docker-compose logs kafka | grep "started"
```

---

## Data & Cache Issues

### Cache Not Working

**Symptom:** Every request shows `"cached": false`

**Diagnosis:**

```bash
# Check if Redis is enabled
echo $MLOPS_REDIS_ENABLED

# Check if Redis is running
redis-cli ping

# Check cache keys
redis-cli KEYS "prediction:*" | head
```

**Solutions:**

```bash
# Enable Redis
export MLOPS_REDIS_ENABLED=true

# Start Redis
docker-compose up -d redis

# Test caching
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# Run same request again
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'  # Should show cached: true

# Check cache manually
redis-cli --scan --pattern "prediction:*"
```

### Batch Results Lost

**Symptom:** Batch job completes but results are gone/inaccessible

**Solutions:**

```bash
# 1. Check job status
curl http://localhost:8000/api/v1/batch/status/job_id | jq

# 2. Check if data in Redis
redis-cli EXISTS batch:job_id:results

# 3. Check Redis memory limit (might be evicting data)
redis-cli INFO stats | grep evicted

# 4. Increase Redis memory
docker-compose down
# Edit docker-compose.yml:
#   environment:
#     - maxmemory=2gb
#     - maxmemory-policy=allkeys-lru
docker-compose up -d redis

# 5. Re-submit batch if lost
curl -X POST http://localhost:8000/api/v1/batch/predict \
  -H "Content-Type: application/json" \
  -d '{"texts": [...]}'
```

---

## Code & Configuration Issues

> **Configuration-specific troubleshooting has been moved.** For profile issues, environment variables, validation errors, and service connection problems, see **[docs/configuration/TROUBLESHOOTING.md](configuration/TROUBLESHOOTING.md)**.

### Quick Reference

- **Profile not loading?** → [Configuration Troubleshooting: Profile Issues](configuration/TROUBLESHOOTING.md#profile-issues)
- **Environment variable not working?** → [Configuration Troubleshooting: Environment Variables](configuration/TROUBLESHOOTING.md#environment-variables)
- **Validation errors?** → [Configuration Troubleshooting: Validation Errors](configuration/TROUBLESHOOTING.md#validation-errors)
- **Redis/Kafka/Vault connection issues?** → [Configuration Troubleshooting: Service Connection Issues](configuration/TROUBLESHOOTING.md#service-connection-issues)

### Import/Module Errors

**Symptom:** `ModuleNotFoundError` or `ImportError` when starting app

**Solutions:**

```bash
# 1. Ensure virtual environment activated
source .venv/bin/activate

# 2. Check Python path
python -c "import sys; print(sys.path)"

# 3. Install missing package
pip install <missing-package>

# 4. Reinstall all requirements
pip install -r requirements.txt --force-reinstall

# 5. Check for conflicting versions
pip list | grep -E "fastapi|pydantic"

# 6. Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

---

## Batch Processing Issues

### Batch Job Status Shows "pending" Forever

**Symptom:** Job stuck in pending state for hours

**Quick Fix:**

```bash
# 1. Check Kafka
docker-compose ps kafka
# Should show "Up"

# 2. Check if batch service running
curl http://localhost:8000/api/v1/health/details | jq

# 3. Restart batch service
docker-compose restart app

# 4. Re-submit batch
curl -X POST http://localhost:8000/api/v1/batch/predict \
  -H "Content-Type: application/json" \
  -d '{"texts": ["test1", "test2"]}'
```

### Cannot Submit Batch (503 error)

**Symptom:** `POST /batch/predict` returns 503 "Service unavailable"

**Solutions:**

```bash
# 1. Check batch service status
curl http://localhost:8000/api/v1/health/details | \
  jq '.dependencies[] | select(.component_name=="async_batch")'

# 2. Check Kafka is running
docker-compose up -d kafka
sleep 30

# 3. Check queue status
curl http://localhost:8000/api/v1/batch/queue/status | jq

# 4. Check logs
docker-compose logs app | grep -i batch | tail -20

# 5. Restart application
docker-compose restart app
```

---

## Testing Issues

### Tests Failing

**Symptom:** `pytest` shows test failures

**Common Issues & Fixes:**

```bash
# 1. Ensure dependencies installed
pip install -r requirements-test.txt

# 2. Run tests with verbose output
pytest -v tests/

# 3. Run specific test
pytest tests/unit/test_api.py::test_predict_success -v

# 4. Check test database
# Tests use temporary database, no setup needed

# 5. View fixture setup
grep "@pytest.fixture" tests/ -r

# 6. Mock external services (models are mocked by default)
```

### Coverage Report Failing

**Symptom:** `pytest --cov` shows errors or missing coverage

**Solutions:**

```bash
# 1. Install coverage
pip install pytest-cov

# 2. Generate report
pytest --cov=app --cov-report=html tests/

# 3. View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov\index.html  # Windows

# 4. Check coverage by file
pytest --cov=app --cov-report=term-missing tests/
```

---

## Pre-commit Issues

### Pre-commit Hooks Failing

**Symptom:** `git commit` fails with hook errors

**Solutions:**

```bash
# 1. See what hooks will run
pre-commit run --all-files

# 2. Run specific hook
pre-commit run black --all-files

# 3. Fix issues manually
black app/
ruff check app/ --fix
mypy app/

# 4. Commit again
git commit -m "message"

# 5. If hook conflicts, temporarily disable
git commit --no-verify  # ⚠️ Not recommended
```

### Pre-commit Not Installed

**Symptom:** `pre-commit` command not found

**Solutions:**

```bash
# 1. Install pre-commit
pip install pre-commit

# 2. Install git hooks
pre-commit install

# 3. Verify installed
pre-commit --version
cat .git/hooks/pre-commit | head
```

---

## Getting Additional Help

### When Nothing Else Works

**Step 1: Gather Information**

```bash
# System info
python --version
pip list | grep -E "fastapi|pydantic"
docker --version

# Application logs
docker-compose logs app > logs.txt

# Configuration
env | grep MLOPS > config.txt

# Test request
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}' > response.json
```

**Step 2: Check Documentation**

- [API_REFERENCE.md](./API_REFERENCE.md) - API endpoints
- [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) - Detailed debugging
- [ERROR_HANDLING.md](./ERROR_HANDLING.md) - Error codes
- [CONFIGURATION_PROFILES.md](./CONFIGURATION_PROFILES.md) - Configuration
- [CLAUDE.md](../CLAUDE.md) - Development guide

**Step 3: Reproduce Minimum Example**

```bash
# Create simple test script
python3 << 'EOF'
import requests

response = requests.post(
    "http://localhost:8000/api/v1/predict",
    json={"text": "test"}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
EOF
```

**Step 4: Report Issue**

Create GitHub issue with:
- Python version: `python --version`
- OS: Windows/Mac/Linux
- Steps to reproduce (in minimum example above)
- Error message and logs
- What you've already tried
- Link to similar issues (if any)

---

## Reference: Common Error Codes

| Code | Meaning | See |
|------|---------|-----|
| E1001 | Invalid input text | Invalid Input section |
| E2001 | Model not loaded | Model Not Loaded section |
| E2002 | Inference failed | Model Not Loaded section |
| E4001 | Service unavailable | Connection Issues section |
| E4003 | Resource not found | Not Found section |

---

**Last Updated:** 2025-11-19

**Quick Links:**
- [Debugging Guide](./DEBUGGING_GUIDE.md)
- [API Reference](./API_REFERENCE.md)
- [Error Handling](./ERROR_HANDLING.md)
- [Developer Setup](./DEVELOPER_SETUP.md)
