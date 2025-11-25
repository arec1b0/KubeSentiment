# Configuration Troubleshooting

Common configuration issues and how to fix them.

## Table of Contents

1. [Profile Issues](#profile-issues)
2. [Environment Variables](#environment-variables)
3. [Validation Errors](#validation-errors)
4. [Service Connection Issues](#service-connection-issues)
5. [Resource Issues](#resource-issues)
6. [Debugging Techniques](#debugging-techniques)
7. [Getting Help](#getting-help)

---

## Profile Issues

### Profile Not Loading

**Symptom:** Settings don't match expected profile defaults

**Diagnosis:**
```python
from app.core.config import get_settings

settings = get_settings()
print(f"Active environment: {settings.server.environment}")
print(f"Debug mode: {settings.server.debug}")
print(f"Log level: {settings.monitoring.log_level}")
```

**Common Causes:**

1. **Profile not set**
   ```bash
   # Wrong
   python -m uvicorn app.main:app

   # Correct
   export MLOPS_PROFILE=development
   python -m uvicorn app.main:app
   ```

2. **Profile name misspelled**
   ```bash
   # Wrong
   export MLOPS_PROFILE=dev  # Should be 'development'

   # Correct
   export MLOPS_PROFILE=development
   ```

3. **Profile name case-sensitive**
   ```bash
   # Wrong
   export MLOPS_PROFILE=Production

   # Correct
   export MLOPS_PROFILE=production
   ```

**Solution:**
```bash
# Set profile explicitly
export MLOPS_PROFILE=development

# Verify it loaded
python -c "from app.core.config import get_settings; print(get_settings().server.environment)"

# List available profiles
python -c "from app.core.config import ProfileRegistry; print(ProfileRegistry.list_profiles())"
```

---

### Profile Defaults Not Applied

**Symptom:** Some settings use profile defaults, others don't

**Cause:** Environment variables override profile defaults

**Solution:**
Check configuration loading order:
1. Profile defaults (lowest priority)
2. `.env` file values
3. Environment variables (highest priority)

```bash
# Check what's loading
python -c "
from app.core.config import get_settings
settings = get_settings()
print(f'Profile: {settings.server.environment}')
print(f'Workers: {settings.server.workers}')
print(f'Debug: {settings.server.debug}')
"

# Clear env vars and .env file if needed
unset MLOPS_DEBUG
unset MLOPS_WORKERS
```

---

## Environment Variables

### Setting Not Taking Effect

**Symptom:** You set a variable but it doesn't apply

**Diagnosis:**
```bash
# Check if variable is set
echo $MLOPS_MODEL_NAME

# Check if variable is loaded
python -c "
from app.core.config import get_settings
print(get_settings().model.model_name)
"

# Check raw environment
import os
print(os.getenv('MLOPS_MODEL_NAME'))
```

**Common Causes:**

1. **Variable not exported**
   ```bash
   # Wrong - variable not in environment
   MLOPS_MODEL_NAME=my-model python -m uvicorn app.main:app

   # Correct - variable exported to environment
   export MLOPS_MODEL_NAME=my-model
   python -m uvicorn app.main:app
   ```

2. **Wrong variable name**
   ```bash
   # Wrong - typo in variable name
   export MLOPS_MODEL_NAME=my-model  # Missing 'MLOPS_' prefix

   # Correct
   export MLOPS_MODEL_NAME=my-model
   ```

3. **Not loaded from .env file**
   ```bash
   # Create .env file
   cat > .env << EOF
   MLOPS_MODEL_NAME=my-model
   MLOPS_PORT=8000
   EOF

   # Load it (app does this automatically, but you can verify)
   export $(cat .env | xargs)

   # Or unset and let app load
   python -m uvicorn app.main:app
   ```

4. **Kubernetes ConfigMap not mounted**
   ```yaml
   # Check ConfigMap exists
   kubectl get configmap mlops-sentiment-config -n mlops-dev

   # Check pod has volume mounts
   kubectl describe pod -n mlops-dev -l app=mlops-sentiment

   # Check environment in pod
   kubectl exec -n mlops-dev <pod-name> -- env | grep MLOPS
   ```

**Solution:**

```bash
# Method 1: Set via export (temporary)
export MLOPS_MODEL_NAME=my-model
python -m uvicorn app.main:app

# Method 2: Set in .env file (persistent)
echo "MLOPS_MODEL_NAME=my-model" >> .env

# Method 3: Check config is loading
python -c "
import os
from app.core.config import get_settings
print('From environment:', os.getenv('MLOPS_MODEL_NAME'))
print('From settings:', get_settings().model.model_name)
"
```

---

### Finding Variable Names

**Need to find the right variable name?**

```bash
# Search documentation
grep -r "MLOPS_" docs/configuration/ENVIRONMENT_VARIABLES.md

# Or check source code
grep -r "MLOPS_" app/core/config/

# Or check available settings
python -c "
from app.core.config import get_settings
settings = get_settings()

# List server settings
print('Server:', dir(settings.server))

# List model settings
print('Model:', dir(settings.model))

# etc.
"
```

---

## Validation Errors

### Model Not in Allowed Models

**Error:**
```
ValueError: Model 'my-model' must be in allowed_models list
```

**Cause:** Model name not in whitelist

**Solution:**

1. **Check allowed models:**
   ```python
   from app.core.config import get_settings
   print(get_settings().model.allowed_models)
   ```

2. **Add your model to the list:**
   ```bash
   # Via environment variable
   export MLOPS_ALLOWED_MODELS="model1,model2,my-model"

   # Or in .env file
   echo "MLOPS_ALLOWED_MODELS=model1,model2,my-model" >> .env
   ```

3. **Verify it's loaded:**
   ```python
   from app.core.config import get_settings
   assert 'my-model' in get_settings().model.allowed_models
   ```

---

### API Key Too Short

**Error:**
```
ValueError: API key must be at least 8 characters
```

**Cause:** API key is less than 8 characters

**Solution:**

```bash
# Generate a proper API key (min 8 chars, alphanumeric + special chars)
export MLOPS_API_KEY=$(head -c 32 /dev/urandom | base64)

# Verify it
python -c "from app.core.config import get_settings; print(len(get_settings().security.api_key))"
```

---

### Invalid CORS Origin

**Error:**
```
ValueError: CORS origin must be a valid URL (https?://...)
```

**Cause:** CORS origin format is invalid

**Solution:**

```bash
# Wrong formats
export MLOPS_ALLOWED_ORIGINS="localhost:3000"           # Missing protocol
export MLOPS_ALLOWED_ORIGINS="*"                         # Wildcard not allowed in prod

# Correct formats
export MLOPS_ALLOWED_ORIGINS="http://localhost:3000"    # Include protocol
export MLOPS_ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com"

# Verify it
python -c "from app.core.config import get_settings; print(get_settings().security.allowed_origins)"
```

---

### Port Out of Range

**Error:**
```
ValueError: Port must be between 1024 and 65535
```

**Cause:** Port number out of valid range

**Solution:**

```bash
# Wrong
export MLOPS_PORT=80       # Requires root privileges
export MLOPS_PORT=999999   # Out of range

# Correct
export MLOPS_PORT=8000     # Between 1024-65535
export MLOPS_PORT=8080
```

---

## Service Connection Issues

### Redis Connection Failed

**Symptom:** Cannot connect to Redis

**Error:**
```
ConnectionRefusedError: Connection refused
Error: NOAUTH Authentication required
```

**Diagnosis:**

```bash
# Check if Redis is running
redis-cli ping

# Check host/port
python -c "from app.core.config import get_settings; s=get_settings(); print(f'{s.redis.redis_host}:{s.redis.redis_port}')"

# Test connection
redis-cli -h localhost -p 6379 ping

# Check password if needed
redis-cli -h localhost -p 6379 -a <password> ping
```

**Solutions:**

1. **Redis not running**
   ```bash
   # Start Redis
   redis-server

   # Or via Docker
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. **Wrong host/port**
   ```bash
   # Check current settings
   export MLOPS_REDIS_HOST=localhost
   export MLOPS_REDIS_PORT=6379
   ```

3. **Password issue**
   ```bash
   # Set password if needed
   export MLOPS_REDIS_PASSWORD=mypassword
   ```

4. **Disable Redis if not needed**
   ```bash
   export MLOPS_REDIS_ENABLED=false
   ```

---

### Kafka Connection Failed

**Symptom:** Cannot connect to Kafka

**Error:**
```
KafkaError: Failed to create producer/consumer
NoBrokersAvailable: Broker(host=kafka, port=9092) - Connection refused
```

**Diagnosis:**

```bash
# Check Kafka is running
docker ps | grep kafka

# Check bootstrap servers
python -c "from app.core.config import get_settings; print(get_settings().kafka.kafka_bootstrap_servers)"

# Test connection with telnet
telnet localhost 9092

# Check Kafka logs
docker logs <kafka-container>
```

**Solutions:**

1. **Kafka not running**
   ```bash
   # Start Kafka
   docker-compose up kafka

   # Or manually
   docker run -d -p 9092:9092 confluentinc/cp-kafka
   ```

2. **Wrong bootstrap servers**
   ```bash
   # Check what's configured
   echo $MLOPS_KAFKA_BOOTSTRAP_SERVERS

   # Update if needed
   export MLOPS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   ```

3. **Kafka consumer group issues**
   ```bash
   # Check consumer group exists
   kafka-consumer-groups --list --bootstrap-server localhost:9092

   # Create if needed
   kafka-console-consumer --bootstrap-server localhost:9092 \
     --topic test \
     --group my-group
   ```

4. **Disable Kafka if not needed**
   ```bash
   export MLOPS_KAFKA_ENABLED=false
   ```

---

### Vault Connection Failed

**Symptom:** Cannot connect to HashiCorp Vault

**Error:**
```
VaultError: Failed to connect to Vault
ConnectionError: Cannot reach Vault at https://vault:8200
```

**Diagnosis:**

```bash
# Check Vault is running
curl -k https://vault:8200/ui/

# Check Vault address
python -c "from app.core.config import get_settings; print(get_settings().vault.vault_addr)"

# Check Vault token
python -c "from app.core.config import get_settings; print('Token set' if get_settings().vault.vault_token else 'Token not set')"
```

**Solutions:**

1. **Vault not running**
   ```bash
   # Start Vault
   vault server -dev

   # Or via Docker
   docker run -d -p 8200:8200 vault:latest
   ```

2. **Wrong Vault address**
   ```bash
   # Check current setting
   export MLOPS_VAULT_ADDR=http://vault:8200
   ```

3. **Invalid Vault token**
   ```bash
   # Generate new token
   export MLOPS_VAULT_TOKEN=$(vault token create -field=token)
   ```

4. **Disable Vault if not needed (dev only)**
   ```bash
   export MLOPS_VAULT_ENABLED=false
   ```

---

## Resource Issues

### Out of Memory

**Symptom:** Application crashes with OOM

**Cause:** Cache size too large or insufficient memory

**Solution:**

```bash
# Check current cache sizes
python -c "
from app.core.config import get_settings
s = get_settings()
print(f'Model cache: {s.model.prediction_cache_max_size}')
print(f'Redis max connections: {s.redis.redis_max_connections}')
"

# Reduce cache sizes
export MLOPS_PREDICTION_CACHE_MAX_SIZE=100  # Was 10000
export MLOPS_REDIS_MAX_CONNECTIONS=10       # Was 100

# Or disable caching if not needed
export MLOPS_REDIS_ENABLED=false
```

---

### High CPU Usage

**Symptom:** CPU usage very high

**Cause:** Too many workers or async jobs

**Solution:**

```bash
# Check worker count
python -c "from app.core.config import get_settings; print(get_settings().server.workers)"

# Reduce workers
export MLOPS_WORKERS=1

# Or reduce async batch settings
export MLOPS_ASYNC_BATCH_ENABLED=false
export MLOPS_ASYNC_BATCH_MAX_JOBS=100  # Was 1000
```

---

## Debugging Techniques

### Print All Configuration

```python
from app.core.config import get_settings
import json

settings = get_settings()

# Print all settings as dict
print(json.dumps(settings.model_dump(), indent=2, default=str))

# Or specific domain
print("Server config:")
print(json.dumps(settings.server.model_dump(), indent=2))

print("\nKafka config:")
print(json.dumps(settings.kafka.model_dump(), indent=2))
```

---

### Verify Profile Loading

```python
from app.core.config import Settings, ProfileRegistry

# List available profiles
print("Available profiles:")
for name, profile in ProfileRegistry.list_profiles().items():
    print(f"  {name}: {profile.description}")

# Load specific profile and see defaults
profile = ProfileRegistry.get_profile('production')
print(f"\nProduction profile defaults:")
for key, value in profile.get_overrides().items():
    print(f"  {key}: {value}")
```

---

### Check Environment Variables

```python
import os
from app.core.config import get_settings

settings = get_settings()

# Check which variables are set in environment
mlops_vars = {k: v for k, v in os.environ.items() if k.startswith('MLOPS_')}
print("Environment variables:")
for key, value in sorted(mlops_vars.items()):
    # Hide sensitive values
    if 'password' in key.lower() or 'token' in key.lower():
        print(f"  {key}: ***")
    else:
        print(f"  {key}: {value}")
```

---

### Validate Settings

```python
from app.core.config import get_settings
from pydantic import ValidationError

try:
    settings = get_settings()
    print("✅ Configuration is valid")
except ValidationError as e:
    print("❌ Configuration errors:")
    for error in e.errors():
        print(f"  - {error['loc']}: {error['msg']}")
```

---

### Test Configuration in Code

```python
from app.core.config import get_settings

settings = get_settings()

# Test critical settings
assert settings.server.port > 0
assert settings.model.model_name
assert settings.server.environment in ['local', 'development', 'staging', 'production']

if settings.kafka.kafka_enabled:
    assert settings.kafka.kafka_bootstrap_servers
    assert settings.kafka.kafka_topic

if settings.redis.redis_enabled:
    assert settings.redis.redis_host
    assert settings.redis.redis_port

print("✅ All critical settings present")
```

---

## Getting Help

### Check Documentation

| Issue Type | Document |
|-----------|----------|
| "How do I set up...?" | [Quick Start](QUICK_START.md) |
| "What setting controls...?" | [Environment Variables](ENVIRONMENT_VARIABLES.md) |
| "Why is it configured this way?" | [Architecture](ARCHITECTURE.md) |
| "What are the profile defaults?" | [Profiles](PROFILES.md) |
| "How do I deploy to...?" | [Deployment](DEPLOYMENT.md) |
| "I'm upgrading..." | [Migration Guide](MIGRATION.md) |

### Collect Debug Information

When asking for help, provide:

```bash
# Current configuration
python -c "from app.core.config import get_settings; print(get_settings().model_dump())"

# Environment variables
env | grep MLOPS

# Application logs
# (last 50 lines with errors)

# System info
python --version
pip list | grep -E "(pydantic|fastapi|kafka|redis)"
```

### Report Issues

When reporting configuration issues, include:

1. KubeSentiment version
2. Python version
3. What you're trying to do
4. Configuration profile being used
5. Error message (full traceback)
6. Steps to reproduce
7. Debug information from above

---

## Related Documentation

- **[Quick Start](QUICK_START.md)** - Getting started
- **[Environment Variables](ENVIRONMENT_VARIABLES.md)** - Complete settings reference
- **[Deployment](DEPLOYMENT.md)** - Deployment configurations
- **[Architecture](ARCHITECTURE.md)** - Configuration design

---

**Last Updated:** 2025-11-25
**Maintained By:** KubeSentiment Team
