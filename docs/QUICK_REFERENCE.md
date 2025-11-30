# ⚠️ DEPRECATED - KubeSentiment Quick Reference Guide

> **Configuration content has been moved.** See **[docs/configuration/QUICK_START.md](docs/configuration/QUICK_START.md)** for configuration quick start.
>
> This page may contain other useful quick reference information. For a consolidated quick reference, see the navigation in **[docs/configuration/README.md](docs/configuration/README.md)**.

> **Last Updated:** 2025-11-19
> **Purpose:** Quick lookup for common development tasks
> **Print Friendly:** Yes - Good for keeping handy

## Table of Contents

- [Setup](#setup)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Git Workflow](#git-workflow)
- [API Testing](#api-testing)
- [Docker Commands](#docker-commands)
- [Debugging](#debugging)
- [Common Issues](#common-issues)

---

## Setup

### Initial Setup

```bash
# Clone repository
git clone https://github.com/arec1b0/KubeSentiment.git
cd KubeSentiment

# Automated setup (recommended)
python scripts/setup_dev_environment.py

# Or manual setup
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS: .venv\Scripts\activate (Windows)
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
```

### Activate Virtual Environment

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Verify (should show (.venv) in prompt)
echo $VIRTUAL_ENV
```

---

## Running the Application

### Local Development (No Dependencies)

```bash
# With hot-reload
PROFILE=local uvicorn app.main:app --reload

# Open browser to http://localhost:8000/docs
```

### Development (With Services)

```bash
# Start services (Redis, Kafka, etc.)
docker-compose up -d

# Start application
PROFILE=development uvicorn app.main:app --reload

# Stop services
docker-compose down
```

### Using Make

```bash
# Show all commands
make help

# Start dev server
make dev

# Run without reload
make run
```

### Production (Simulation)

```bash
# 4 workers, no reload
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

---

## Testing

### Run All Tests

```bash
# Full test suite
make test
pytest tests/

# With coverage
pytest --cov=app --cov-report=html tests/

# View coverage report
open htmlcov/index.html  # macOS
```

### Run Specific Tests

```bash
# File
pytest tests/unit/test_api.py

# Function
pytest tests/unit/test_api.py::test_predict_success

# With output
pytest -v tests/unit/test_api.py

# With debugging
pytest -s tests/unit/test_api.py  # Shows print statements

# Skip slow tests
pytest -m "not slow" tests/
```

### Test Commands

```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Stop on first failure
pytest -x tests/

# Show most recent N failures
pytest --lf tests/

# Parallel execution
pytest -n auto tests/
```

---

## Code Quality

### Format Code

```bash
# Format all
make format

# Format specific directory
black app/
isort app/

# Check formatting (don't modify)
black --check app/
```

### Run Linters

```bash
# All linters
make lint

# Individual linters
black --check app/          # Code format
ruff check app/             # Linting
mypy app/                   # Type checking
bandit -r app/              # Security
radon cc app/ -a            # Complexity

# Fix issues
ruff check app/ --fix       # Auto-fix ruff issues
black app/                  # Auto-format
```

### Check Complexity

```bash
# Show code complexity
make complexity
radon cc app/ -a

# Show metrics
radon mi app/ -a
```

### Pre-commit Hooks

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Uninstall (if needed)
pre-commit uninstall

# Reinstall
pre-commit install
```

---

## Git Workflow

### Create Feature Branch

```bash
# Create and switch to branch
git checkout -b feature/my-feature

# Or: Create from main
git checkout -b feature/my-feature origin/main

# List branches
git branch -a
```

### Commit Changes

```bash
# Stage changes
git add app/
git add tests/

# Or interactive
git add -p

# Commit (pre-commit hooks run automatically)
git commit -m "feat(api): add new endpoint"

# Bypass hooks (not recommended)
git commit --no-verify -m "message"

# Amend last commit
git commit --amend --no-edit
```

### Conventional Commit Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** feat, fix, docs, style, refactor, test, chore, perf, ci

**Examples:**

```
feat(api): add batch prediction endpoint
fix(model): resolve ONNX loading issue
docs(api): update API reference
test(api): add unit tests for predict endpoint
refactor(config): simplify settings structure
```

### Push & Pull Request

```bash
# Push to remote
git push -u origin feature/my-feature

# Pull latest changes
git pull origin main

# Fetch without merge
git fetch origin

# Rebase on main
git rebase origin/main

# Merge branch locally
git merge origin/feature/other-feature
```

---

## API Testing

### Test with cURL

```bash
# Single prediction
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this!"}'

# Pretty-print JSON
curl ... | jq

# Save response
curl ... > response.json

# Show headers
curl -i http://localhost:8000/api/v1/health

# Show full request/response
curl -v http://localhost:8000/api/v1/health
```

### Test with Python

```python
import requests

# Single prediction
response = requests.post(
    "http://localhost:8000/api/v1/predict",
    json={"text": "I love this!"}
)
print(response.json())

# Batch prediction
response = requests.post(
    "http://localhost:8000/api/v1/batch/predict",
    json={"texts": ["text1", "text2"], "priority": "high"}
)
job = response.json()
print(f"Job ID: {job['job_id']}")

# Check status
response = requests.get(
    f"http://localhost:8000/api/v1/batch/status/{job['job_id']}"
)
print(response.json())
```

### Test with JavaScript

```javascript
// Single prediction
fetch('http://localhost:8000/api/v1/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'I love this!' })
})
  .then(r => r.json())
  .then(data => console.log(data));

// Batch prediction
fetch('http://localhost:8000/api/v1/batch/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    texts: ['text1', 'text2'],
    priority: 'high'
  })
})
  .then(r => r.json())
  .then(job => console.log(`Job: ${job.job_id}`));
```

### API Endpoints Cheat Sheet

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/predict` | POST | Single prediction |
| `/api/v1/batch/predict` | POST | Submit batch job |
| `/api/v1/batch/status/{job_id}` | GET | Check job status |
| `/api/v1/batch/results/{job_id}` | GET | Get results |
| `/api/v1/batch/jobs/{job_id}` | DELETE | Cancel job |
| `/api/v1/health` | GET | Health check |
| `/api/v1/health/details` | GET | Detailed health |
| `/api/v1/model-info` | GET | Model metadata |
| `/api/v1/metrics` | GET | System metrics |
| `/api/v1/batch/metrics` | GET | Batch metrics |

---

## Docker Commands

### Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f app

# Specific service logs
docker-compose logs redis

# Execute command in container
docker-compose exec app bash
docker-compose exec app python -c "..."

# Rebuild images
docker-compose build

# Remove data volumes
docker-compose down -v

# View running services
docker-compose ps
```

### Docker

```bash
# Build image
docker build -t sentiment-api:latest .

# Run container
docker run -p 8000:8000 sentiment-api:latest

# View images
docker images

# Remove image
docker rmi sentiment-api:latest

# View container logs
docker logs container_id

# Enter container
docker exec -it container_id bash
```

### Docker Troubleshooting

```bash
# Remove all stopped containers
docker container prune

# Remove dangling images
docker image prune

# Clean up everything
docker system prune -a

# Check disk usage
docker system df
```

---

## Debugging

### Enable Debug Mode

```bash
# Set environment variables
export MLOPS_DEBUG=true
export MLOPS_LOG_LEVEL=DEBUG

# Restart application
docker-compose restart app

# View debug logs
docker-compose logs -f app | grep DEBUG
```

### View Logs

```bash
# Container logs
docker-compose logs app

# Follow logs (real-time)
docker-compose logs -f app

# Last 100 lines
docker-compose logs --tail=100 app

# Specific time range
docker-compose logs --since 10m app

# Filter by pattern
docker-compose logs app | grep ERROR
```

### Search Logs

```bash
# Find correlation ID
CORRELATION_ID="uuid-here"
docker-compose logs app | grep "$CORRELATION_ID"

# Find specific error
docker-compose logs app | grep "E2001"

# Chain with jq (JSON logs)
docker-compose logs app | jq 'select(.level=="ERROR")'
```

### Python Debugging

```python
# Add breakpoint
breakpoint()  # Press 'c' to continue, 'n' for next line

# Or older style
import pdb; pdb.set_trace()

# Print with context
import logging
logger = logging.getLogger(__name__)
logger.debug("Variable:", extra={"var": value})
```

### Profile Code

```bash
# Run with profiler
python -m cProfile -s cumtime app/main.py

# Save profile results
python -m cProfile -o profile.stats app/main.py

# Analyze results
python -m pstats profile.stats
```

---

## Common Issues

### Application Won't Start

```bash
# Check Python version
python --version  # Must be 3.11+

# Check dependencies
pip list | grep fastapi

# Activate venv
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process (macOS/Linux)
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

### Model Not Loaded

```bash
# Check status
curl http://localhost:8000/api/v1/model-info | jq

# Restart app
docker-compose restart app

# Check logs
docker-compose logs app | grep -i model
```

### Redis Connection Failed

```bash
# Start Redis
docker-compose up -d redis

# Test connection
redis-cli ping

# View logs
docker-compose logs redis
```

### Slow Responses

```bash
# Check if caching
curl ... | jq .cached

# Check backend
curl http://localhost:8000/api/v1/health | jq .backend
# Should be "onnx" for production

# Switch to ONNX
export MLOPS_MODEL_BACKEND=onnx
docker-compose restart app
```

---

## Environment Variables

> **Configuration quick reference has been moved.** For complete environment variable reference, see **[docs/configuration/ENVIRONMENT_VARIABLES.md](configuration/ENVIRONMENT_VARIABLES.md)**.

### Quick Reference

```bash
# Set profile (applies 50+ defaults automatically)
export MLOPS_PROFILE=local  # or development, staging, production

# Override specific settings as needed
export MLOPS_REDIS_HOST=my-redis-server
export MLOPS_KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

**See also:**
- **[Environment Variables Reference](configuration/ENVIRONMENT_VARIABLES.md)** - Complete list of all settings
- **[Configuration Profiles](configuration/PROFILES.md)** - Profile defaults
- **[Quick Start](configuration/QUICK_START.md)** - Setup guide

---

## Make Commands

```bash
make help                   # Show all commands
make install-dev            # Install dev dependencies
make format                 # Format code
make lint                   # Run linters
make test                   # Run tests
make coverage               # Generate coverage report
make dev                    # Start dev server
make run                    # Run app (no reload)
make build                  # Build Docker image
make deploy-dev             # Deploy to dev
make deploy-staging         # Deploy to staging
make complexity             # Check complexity
make security               # Security scan
make clean                  # Remove build artifacts
make shell                  # Python interactive shell
```

---

## Useful Links

- **Documentation**: `docs/` directory
- **API Docs**: http://localhost:8000/docs
- **ADRs**: `docs/architecture/decisions/`
- **README**: `README.md`
- **Contributing**: `CONTRIBUTING.md`

---

## Keyboard Shortcuts

### VS Code

| Shortcut | Action |
|----------|--------|
| Ctrl+\` | Open terminal |
| Ctrl+Shift+D | Debug view |
| F5 | Start debugging |
| Ctrl+Shift+B | Build |
| Ctrl+Shift+P | Command palette |

### PyCharm

| Shortcut | Action |
|----------|--------|
| Shift+Shift | Search everywhere |
| Ctrl+Alt+L | Reformat code |
| Shift+F10 | Run |
| Shift+F9 | Debug |
| Ctrl+/ | Comment line |

---

## Print This Page

**Print Shortcuts:**
- Chrome/Firefox: Ctrl+P (Cmd+P on Mac)
- Recommendation: Print to PDF for easy searching

---

**Last Updated:** 2025-11-19

**Need More Help?**
- [DEVELOPER_SETUP.md](./DEVELOPER_SETUP.md) - Full setup guide
- [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) - Advanced debugging
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues
- [API_REFERENCE.md](./API_REFERENCE.md) - API documentation
