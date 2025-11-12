# Configuration Migration Guide

This guide helps developers migrate to the new domain-driven configuration architecture.

## Quick Start: Nothing to Change!

**Good news:** All existing code continues to work without any modifications. The refactored configuration system is 100% backward compatible.

```python
# Your existing code still works
from app.core.config import Settings, get_settings

settings = get_settings()
model_name = settings.model_name  # ✅ Still works!
```

## What Changed?

### Before: Monolithic Settings

```python
# app/core/config.py (917 lines)
class Settings(BaseSettings):
    # Server settings
    app_name: str = "ML Model Serving API"
    port: int = 8000

    # Model settings
    model_name: str = "distilbert..."
    max_text_length: int = 512

    # Kafka settings (30+ fields)
    kafka_enabled: bool = False
    kafka_bootstrap_servers: List[str] = ["localhost:9092"]
    # ... 30 more Kafka fields

    # Redis settings
    redis_enabled: bool = False
    # ... more Redis fields

    # ... 90+ total fields
```

**Problems:**
- 917 lines in one file
- 90+ configuration fields mixed together
- Hard to find specific settings
- Difficult to test (must mock entire Settings object)

### After: Domain-Driven Configuration

```python
# app/core/config/server.py
class ServerConfig(BaseSettings):
    app_name: str = "ML Model Serving API"
    port: int = 8000
    # Only server-related settings

# app/core/config/model.py
class ModelConfig(BaseSettings):
    model_name: str = "distilbert..."
    max_text_length: int = 512
    # Only model-related settings

# app/core/config/kafka.py
class KafkaConfig(BaseSettings):
    kafka_enabled: bool = False
    kafka_bootstrap_servers: List[str] = ["localhost:9092"]
    # All 30+ Kafka settings in one focused module

# app/core/config/settings.py
class Settings(BaseSettings):
    server: ServerConfig = ServerConfig()
    model: ModelConfig = ModelConfig()
    kafka: KafkaConfig = KafkaConfig()
    # ... other domain configs

    # Backward compatibility properties
    @property
    def model_name(self) -> str:
        return self.model.model_name
```

**Benefits:**
- 12 focused modules (~100 lines each)
- One domain per configuration class
- Easy to find settings (open relevant module)
- Test only what you need (mock specific domains)
- 100% backward compatible

---

## Migration Scenarios

### Scenario 1: Reading Configuration (No Changes Needed)

#### Your Existing Code
```python
from app.core.config import get_settings

settings = get_settings()

# Access settings
model_name = settings.model_name
kafka_enabled = settings.kafka_enabled
redis_host = settings.redis_host
```

#### What Happens Now
The Settings class has `@property` methods that delegate to domain configs:

```python
# Internally, this happens:
settings.model_name        # → settings.model.model_name
settings.kafka_enabled     # → settings.kafka.kafka_enabled
settings.redis_host        # → settings.redis.redis_host
```

#### Action Required
✅ **None!** Your code continues to work unchanged.

#### Optional: Modernize (Recommended for New Code)
```python
from app.core.config import get_settings

settings = get_settings()

# New style - explicit domain access
model_name = settings.model.model_name
kafka_enabled = settings.kafka.kafka_enabled
redis_host = settings.redis.redis_host
```

**Why modernize?**
- Clearer which domain you're accessing
- Better IDE autocomplete
- Easier to understand dependencies

---

### Scenario 2: FastAPI Dependency Injection (No Changes Needed)

#### Your Existing Code
```python
from fastapi import Depends
from app.core.config import Settings, get_settings

@app.get("/predict")
async def predict(
    text: str,
    settings: Settings = Depends(get_settings)
):
    model_name = settings.model_name  # ✅ Still works
    max_length = settings.max_text_length  # ✅ Still works
    # Your logic...
```

#### Action Required
✅ **None!** Dependency injection works exactly the same.

#### Optional: Inject Specific Domains
```python
from fastapi import Depends
from app.core.config import Settings, get_settings, ModelConfig

def get_model_config(settings: Settings = Depends(get_settings)) -> ModelConfig:
    return settings.model

@app.get("/predict")
async def predict(
    text: str,
    model_config: ModelConfig = Depends(get_model_config)
):
    model_name = model_config.model_name
    max_length = model_config.max_text_length
    # Your logic...
```

**Benefits:**
- Clearer what configuration the endpoint needs
- Easier to mock in tests (just mock ModelConfig)
- Better separation of concerns

---

### Scenario 3: Testing with Mocks (Improved!)

#### Your Old Test Code
```python
from unittest.mock import Mock, patch

def test_prediction_service():
    # Had to mock entire Settings object
    mock_settings = Mock()
    mock_settings.model_name = "test-model"
    mock_settings.max_text_length = 256
    mock_settings.kafka_enabled = False
    mock_settings.redis_enabled = False
    # ... mock 90+ fields even if you only need 2

    service = PredictionService(settings=mock_settings)
    # Test...
```

#### New Test Code (Better!)
```python
from unittest.mock import Mock
from app.core.config import Settings, ModelConfig

def test_prediction_service():
    # Mock only the domain you need
    mock_model_config = Mock(spec=ModelConfig)
    mock_model_config.model_name = "test-model"
    mock_model_config.max_text_length = 256

    settings = Settings()
    settings.model = mock_model_config
    # Don't need to mock Kafka, Redis, etc.

    service = PredictionService(settings=settings)
    # Test...
```

#### Action Required
✅ **Optional:** Update tests to use domain-specific mocks for cleaner tests.

**Benefits:**
- Only mock what you test
- Clearer test intent
- Less boilerplate

---

### Scenario 4: Environment Variables (No Changes)

#### Your Existing Environment Variables
```bash
export MLOPS_MODEL_NAME="my-model"
export MLOPS_PORT=8080
export MLOPS_KAFKA_ENABLED=true
export MLOPS_REDIS_HOST="redis-server"
```

#### What Happens Now
Environment variables work exactly the same. They're automatically loaded into the appropriate domain config:

```python
MLOPS_MODEL_NAME       → settings.model.model_name
MLOPS_PORT            → settings.server.port
MLOPS_KAFKA_ENABLED   → settings.kafka.kafka_enabled
MLOPS_REDIS_HOST      → settings.redis.redis_host
```

#### Action Required
✅ **None!** All environment variables work unchanged.

---

### Scenario 5: Validators and Cross-Field Checks (No Changes)

#### Existing Validators Still Work
```python
from app.core.config import get_settings

settings = get_settings()

# These validators still run:
# - Model name must be in allowed_models list
# - Debug mode incompatible with multiple workers
# - Cache memory usage check

# If validation fails, you still get ValueError
```

#### Action Required
✅ **None!** All validators continue to work.

---

## Migration Checklist

Use this checklist to assess if you need to make any changes:

### Do You Need to Change Anything?

- [ ] **Do you import Settings or get_settings?**
  - ✅ No changes needed - imports work the same

- [ ] **Do you access settings with `settings.model_name`, `settings.port`, etc.?**
  - ✅ No changes needed - backward compatibility properties exist

- [ ] **Do you use environment variables like `MLOPS_MODEL_NAME`?**
  - ✅ No changes needed - environment variables work the same

- [ ] **Do you use dependency injection with `Depends(get_settings)`?**
  - ✅ No changes needed - dependency injection works the same

- [ ] **Do you have tests that mock the Settings object?**
  - ⚠️ Optional: Consider using domain-specific mocks for cleaner tests

### Optional Improvements

- [ ] **Update new code to use domain access:** `settings.model.model_name`
- [ ] **Update tests to mock only needed domains**
- [ ] **Create domain-specific dependency injection functions**
- [ ] **Document which configuration domains your components need**

---

## Code Examples by Use Case

### Use Case 1: Service Initialization

#### Before (Still Works)
```python
from app.core.config import get_settings

class PredictionService:
    def __init__(self):
        self.settings = get_settings()
        self.model_name = self.settings.model_name
        self.max_length = self.settings.max_text_length
```

#### After (Optional Improvement)
```python
from app.core.config import get_settings

class PredictionService:
    def __init__(self):
        self.settings = get_settings()
        self.model_config = self.settings.model
        self.model_name = self.model_config.model_name
        self.max_length = self.model_config.max_text_length
```

---

### Use Case 2: Kafka Consumer Setup

#### Before (Still Works)
```python
from app.core.config import get_settings

settings = get_settings()

if settings.kafka_enabled:
    consumer = KafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        auto_offset_reset=settings.kafka_auto_offset_reset,
        # ... 30+ more settings
    )
```

#### After (Optional Improvement)
```python
from app.core.config import get_settings

settings = get_settings()
kafka_config = settings.kafka

if kafka_config.kafka_enabled:
    consumer = KafkaConsumer(
        kafka_config.kafka_topic,
        bootstrap_servers=kafka_config.kafka_bootstrap_servers,
        group_id=kafka_config.kafka_consumer_group,
        auto_offset_reset=kafka_config.kafka_auto_offset_reset,
        # All Kafka settings from kafka_config
    )
```

**Benefits:**
- Clear that all settings come from kafka_config
- Autocomplete shows only Kafka-related settings
- Easier to understand dependencies

---

### Use Case 3: Conditional Features

#### Before (Still Works)
```python
from app.core.config import get_settings

settings = get_settings()

if settings.redis_enabled:
    setup_redis_cache()

if settings.vault_enabled:
    setup_vault_client()

if settings.kafka_enabled:
    start_kafka_consumer()
```

#### After (Optional Improvement)
```python
from app.core.config import get_settings

settings = get_settings()

if settings.redis.redis_enabled:
    setup_redis_cache(settings.redis)

if settings.vault.vault_enabled:
    setup_vault_client(settings.vault)

if settings.kafka.kafka_enabled:
    start_kafka_consumer(settings.kafka)
```

---

### Use Case 4: Configuration Validation

#### Before (Still Works)
```python
from app.core.config import get_settings

settings = get_settings()

# Validation happens automatically
# ValueError raised if configuration is invalid
```

#### After (Same Behavior)
```python
from app.core.config import get_settings

settings = get_settings()

# Validation still happens automatically
# Each domain config validates its own fields
# Root Settings validates cross-field constraints
```

---

## Testing Migration Examples

### Example 1: Unit Test with Mock

#### Before
```python
def test_kafka_consumer():
    mock_settings = Mock()
    mock_settings.kafka_enabled = True
    mock_settings.kafka_bootstrap_servers = ["localhost:9092"]
    mock_settings.kafka_topic = "test-topic"
    # ... mock all other settings even if not used

    consumer = KafkaConsumer(mock_settings)
    assert consumer.is_enabled()
```

#### After (Improved)
```python
from app.core.config import KafkaConfig

def test_kafka_consumer():
    mock_kafka = Mock(spec=KafkaConfig)
    mock_kafka.kafka_enabled = True
    mock_kafka.kafka_bootstrap_servers = ["localhost:9092"]
    mock_kafka.kafka_topic = "test-topic"
    # Only mock Kafka settings

    consumer = KafkaConsumer(mock_kafka)
    assert consumer.is_enabled()
```

### Example 2: Integration Test

#### Before (Still Works)
```python
def test_prediction_endpoint(client):
    response = client.post("/predict", json={"text": "test"})
    assert response.status_code == 200
    # Settings loaded automatically
```

#### After (Same)
```python
def test_prediction_endpoint(client):
    response = client.post("/predict", json={"text": "test"})
    assert response.status_code == 200
    # Settings loaded automatically (no changes)
```

---

## Common Questions

### Q: Do I need to update my code?
**A:** No! All existing code works without changes. The refactoring is 100% backward compatible.

### Q: Should I update my code?
**A:** For new code, using domain-specific access (`settings.model.model_name`) is recommended for clarity. For existing code, updates are optional.

### Q: What if I add new configuration settings?
**A:** Add them to the appropriate domain config module (e.g., new Kafka setting → `kafka.py`). Don't add to the root `Settings` class.

### Q: How do I know which domain a setting belongs to?
**A:** Look at the setting's purpose:
- Server/app related → `ServerConfig`
- Model related → `ModelConfig`
- Kafka related → `KafkaConfig`
- etc.

### Q: Do environment variables need to change?
**A:** No, all `MLOPS_*` environment variables work exactly the same.

### Q: What about .env files?
**A:** No changes needed. `.env` files are loaded automatically as before.

### Q: Are there breaking changes?
**A:** No breaking changes. All existing APIs are preserved.

### Q: Should I refactor my tests?
**A:** Optional but recommended. Domain-specific mocks make tests cleaner and more focused.

### Q: What if I import from app.core.config.py?
**A:** Still works! The file now re-exports everything from the `app.core.config` package.

---

## Troubleshooting

### Issue: Import Error
```python
ImportError: cannot import name 'Settings' from 'app.core.config'
```

**Solution:** Make sure you're importing from the correct location:
```python
# Correct
from app.core.config import Settings, get_settings

# Also correct
from app.core.config.settings import Settings, get_settings
```

### Issue: Attribute Error
```python
AttributeError: 'Settings' object has no attribute 'model_name'
```

**Solution:** The backward compatibility properties should work. If you see this, check:
1. Are you using the latest Settings class?
2. Try accessing via domain: `settings.model.model_name`

### Issue: Validator Failure
```python
ValueError: Model 'my-model' must be in allowed_models list
```

**Solution:** This is expected behavior. Validators still run:
1. Check that your model is in the `allowed_models` list
2. Update the `allowed_models` list in configuration
3. Or set via environment: `MLOPS_ALLOWED_MODELS="model1,model2,my-model"`

---

## Summary

### Key Points

1. **✅ No Changes Required** - All existing code works
2. **✅ Backward Compatible** - 50+ @property methods preserve old API
3. **✅ Environment Variables Unchanged** - All MLOPS_* vars work
4. **✅ Dependency Injection Works** - No changes to Depends(get_settings)
5. **⚡ Optional Improvements** - Domain access for new code

### Recommended Approach

**For Existing Code:**
- Leave it as-is (it works!)
- Update when you're already modifying the code

**For New Code:**
- Use domain-specific access: `settings.model.model_name`
- Inject specific domains when possible
- Mock only needed domains in tests

### Next Steps

1. Read the [Configuration Architecture Documentation](./CONFIGURATION_ARCHITECTURE.md)
2. Review examples in this guide
3. Try domain-specific access in new code
4. Gradually update tests to use domain mocks (optional)

---

## Getting Help

If you have questions:
1. Check [Configuration Architecture Documentation](./CONFIGURATION_ARCHITECTURE.md)
2. Look at the examples in this migration guide
3. Review the docstrings in each config module
4. Ask the development team

## Related Documentation

- [Configuration Architecture](./CONFIGURATION_ARCHITECTURE.md) - Full documentation
- [Environment Configuration](./ENVIRONMENT_CONFIGURATIONS.md) - Deployment guide
- [Contributing Guide](../CONTRIBUTING.md) - Development guidelines
