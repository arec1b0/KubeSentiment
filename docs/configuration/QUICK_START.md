# Configuration Quick Start

Get KubeSentiment running locally in 5 minutes.

## Local Development (Minimal Setup)

### Step 1: Set Profile
```bash
export MLOPS_PROFILE=local
```

### Step 2: Run Application
```bash
python -m uvicorn app.main:app --reload
```

### Step 3: Test
```bash
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This is great!"}'
```

**Done!** All configuration defaults are applied automatically.

---

## Local Development (With Services)

If you need Redis, Kafka, or other services:

### Option A: Docker Compose

```bash
# 1. Copy template
cp .env.development.template .env

# 2. Start services
docker-compose up

# 3. Test
curl http://localhost:8000/api/v1/health
```

**What's included:** API + Redis + Kafka + Vault mock

### Option B: Manual Setup

```bash
# 1. Create .env file
cp .env.development.template .env

# 2. Start Redis (separate terminal)
redis-server

# 3. Start Kafka (separate terminal)
# ... see https://kafka.apache.org/quickstart

# 4. Run app
python -m uvicorn app.main:app --reload
```

---

## Configuration Profiles

| Profile | Best For | Setup |
|---------|----------|-------|
| **local** | Quick testing, no external services | `export MLOPS_PROFILE=local` |
| **development** | Feature development, optional services | `export MLOPS_PROFILE=development` |
| **staging** | Pre-prod testing, production-like | `export MLOPS_PROFILE=staging` |
| **production** | Live deployment | `export MLOPS_PROFILE=production` |

All profiles include automatic defaults. Override only what's different:

```bash
export MLOPS_PROFILE=development
export MLOPS_REDIS_ENABLED=true      # Override: enable Redis
export MLOPS_REDIS_HOST=localhost    # Override: custom Redis host
```

---

## Environment Variables (If Needed)

### Commonly Used

```bash
# Server
export MLOPS_PROFILE=development
export MLOPS_HOST=0.0.0.0
export MLOPS_PORT=8000

# Model
export MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
export MLOPS_MAX_TEXT_LENGTH=512

# Redis (optional)
export MLOPS_REDIS_ENABLED=true
export MLOPS_REDIS_HOST=localhost
export MLOPS_REDIS_PORT=6379

# Kafka (optional)
export MLOPS_KAFKA_ENABLED=true
export MLOPS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

See **[Environment Variables](ENVIRONMENT_VARIABLES.md)** for complete reference.

---

## Using .env Files

Instead of exporting environment variables:

```bash
# 1. Create .env file
cat > .env << EOF
MLOPS_PROFILE=development
MLOPS_REDIS_ENABLED=true
MLOPS_REDIS_HOST=localhost
EOF

# 2. Load it (optional, app loads automatically)
export $(cat .env | xargs)

# 3. Run app
python -m uvicorn app.main:app --reload
```

The app automatically loads `.env` files using `python-dotenv`.

---

## IDE Setup

### VS Code

1. Install Python extension
2. Create `.vscode/settings.json`:
   ```json
   {
     "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
     "python.linting.enabled": true,
     "python.linting.pylintEnabled": true
   }
   ```
3. Set `MLOPS_PROFILE=local` in terminal

### PyCharm

1. Go to `Settings → Project → Python Interpreter`
2. Add interpreter from `.venv/bin/python`
3. Set `MLOPS_PROFILE=local` in Run Configuration

---

## Docker Setup

### Build Image

```bash
docker build -t kubesentiment:local .
```

### Run Container

```bash
docker run -e MLOPS_PROFILE=local \
  -p 8000:8000 \
  kubesentiment:local
```

### With Services (Docker Compose)

```bash
docker-compose up
```

---

## Kubernetes Setup

### Deploy to Local Cluster

```bash
# 1. Create namespace
kubectl create namespace mlops-dev

# 2. Apply configuration
kubectl apply -f docs/configuration/examples/kubernetes-dev.yaml

# 3. Port forward
kubectl port-forward -n mlops-dev svc/mlops-sentiment 8000:80

# 4. Test
curl http://localhost:8000/api/v1/health
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
export MLOPS_PORT=8001
python -m uvicorn app.main:app --reload
```

### Settings Not Loading

Check active profile:
```python
from app.core.config import get_settings
settings = get_settings()
print(f"Profile: {settings.environment}")
print(f"Debug: {settings.server.debug}")
```

### Model Not Loading

```bash
# Check model settings
export MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english

# Verify it's in allowed models
python -c "from app.core.config import get_settings; print(get_settings().model.allowed_models)"
```

### Module Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## What's Next?

- **Run tests:** `pytest tests/`
- **Format code:** `make format`
- **Lint code:** `make lint`
- **View API docs:** http://localhost:8000/docs
- **View metrics:** http://localhost:8000/api/v1/metrics

---

## Learn More

- **[Configuration Architecture](ARCHITECTURE.md)** - Understand the design
- **[Profiles](PROFILES.md)** - Profile defaults and customization
- **[Environment Variables](ENVIRONMENT_VARIABLES.md)** - Complete settings reference
- **[Deployment](DEPLOYMENT.md)** - Production setup
- **[Examples](examples/)** - Copy-paste configurations

---

**Last Updated:** 2025-11-25
