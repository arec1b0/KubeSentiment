# ADR 009: Implement Profile-Based Configuration System

**Status:** Accepted
**Date:** 2024-03-15
**Authors:** KubeSentiment Team

## Context

KubeSentiment needs to run across multiple environments with different configurations:

1. **Multiple environments**: Local, development, staging, production
2. **Configuration complexity**: 50+ configuration parameters across 10+ domains
3. **Environment-specific settings**: Different values for each environment
4. **Developer experience**: Easy local development without complex setup
5. **Backward compatibility**: Migrate from monolithic configuration
6. **Type safety**: Catch configuration errors at startup, not runtime
7. **Secret management**: Sensitive values must not be in code

Current challenges with existing configuration:
- Single large settings file (1000+ lines)
- Hard to understand which settings apply to which domain
- Difficult to override for different environments
- No clear defaults for local development
- Type errors discovered at runtime

Key requirements:
- **Profile-based defaults**: Sensible defaults per environment
- **Domain separation**: Group related settings together
- **Environment overrides**: Easy to override via environment variables
- **Type validation**: Pydantic validation at startup
- **Documentation**: Self-documenting configuration
- **Backward compatibility**: Migrate existing deployments smoothly

## Decision

We will implement a **profile-based configuration system** with modular domain-specific settings using Pydantic Settings.

### Implementation Strategy

1. **Configuration Domains**:
   - Server (host, port, workers)
   - Model (model name, backend, paths)
   - Redis (connection, pooling)
   - Kafka (brokers, topics, consumer groups)
   - Security (CORS, authentication, rate limiting)
   - Observability (logging, tracing, metrics)
   - MLOps (MLflow, experiment tracking)
   - Data Lake (S3, GCS, Azure Blob)
   - Vault (secrets management)

2. **Profile System**:
   - **local**: Developer laptop, minimal dependencies
   - **development**: Shared dev environment
   - **staging**: Pre-production testing
   - **production**: Production environment

3. **Configuration Hierarchy**:
   ```
   1. Profile defaults (lowest priority)
   2. .env file
   3. Environment variables
   4. Vault secrets (highest priority)
   ```

4. **Directory Structure**:
   ```
   app/core/config/
   ├── __init__.py
   ├── settings.py           # Main settings aggregator
   ├── base.py               # Base settings class
   ├── server.py             # Server configuration
   ├── model.py              # Model configuration
   ├── redis.py              # Redis configuration
   ├── kafka.py              # Kafka configuration
   ├── security.py           # Security settings
   ├── observability.py      # Observability settings
   ├── mlops.py              # MLOps configuration
   ├── data_lake.py          # Data lake settings
   └── vault.py              # Vault configuration
   ```

## Consequences

### Positive

- **Clear organization**: Settings grouped by domain
- **Easy local development**: `PROFILE=local` provides sensible defaults
- **Type safety**: Pydantic catches configuration errors at startup
- **Self-documenting**: Field descriptions serve as documentation
- **Environment flexibility**: Easy to override any setting
- **Validation**: Invalid configurations fail fast
- **IDE support**: Autocomplete and type hints
- **Testability**: Easy to inject test configurations
- **Backward compatible**: Old environment variables still work

### Negative

- **Migration effort**: Existing deployments need to update environment variables
- **More files**: 10+ configuration files vs. 1 monolithic file
- **Learning curve**: Team needs to understand profile system
- **Indirection**: Need to know which file contains which setting
- **Import complexity**: Multiple imports vs. single settings object

### Neutral

- **File count**: More files but smaller and focused
- **Nesting**: Settings accessed via `settings.redis.host` vs `settings.REDIS_HOST`

## Alternatives Considered

### Alternative 1: Monolithic Settings File

**Pros:**
- Simple single file
- All settings in one place
- Easy to search

**Cons:**
- Becomes huge (1000+ lines)
- No logical grouping
- Hard to maintain
- No domain separation

**Rejected because**: Does not scale with application complexity.

### Alternative 2: YAML/JSON Configuration Files

**Pros:**
- Language-agnostic
- Human-readable
- Hierarchical structure
- Common pattern

**Cons:**
- No type validation
- Errors discovered at runtime
- No IDE autocomplete
- Requires parsing and validation code
- Secret management complexity

**Rejected because**: Lacks type safety and IDE support.

### Alternative 3: Config Management Tools (etcd, Consul)

**Pros:**
- Centralized configuration
- Dynamic updates
- Versioning
- Audit trail

**Cons:**
- Additional infrastructure
- Complexity for simple use case
- Network dependency
- Overkill for application config

**Rejected because**: Too complex for application-level configuration; better suited for service discovery.

### Alternative 4: Feature Flags Service (LaunchDarkly, Split)

**Pros:**
- Dynamic feature toggles
- A/B testing support
- User segmentation
- Real-time changes

**Cons:**
- Commercial service (cost)
- Designed for feature flags, not configuration
- Network dependency
- Overkill for static configuration

**Rejected because**: Designed for feature flags, not application configuration.

### Alternative 5: Environment Variables Only

**Pros:**
- 12-factor app compliant
- Simple to understand
- No code needed

**Cons:**
- No defaults or validation
- Hard to manage 50+ variables
- No grouping or organization
- Type conversion errors

**Rejected because**: No defaults, validation, or organization for complex applications.

## Implementation Details

### Profile System

```python
# app/core/config/base.py
from enum import Enum
from pydantic_settings import BaseSettings

class Profile(str, Enum):
    """Environment profiles with different defaults."""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class BaseConfig(BaseSettings):
    """Base configuration with common settings."""

    PROFILE: Profile = Profile.LOCAL

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Backward compatibility
```

### Domain-Specific Settings

```python
# app/core/config/server.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class ServerSettings(BaseSettings):
    """Server configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="MLOPS_SERVER_",
        case_sensitive=True
    )

    host: str = Field(
        default="0.0.0.0",
        description="Server host address"
    )

    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Server port number"
    )

    workers: int = Field(
        default=4,
        ge=1,
        description="Number of worker processes"
    )

    reload: bool = Field(
        default=False,
        description="Enable auto-reload for development"
    )

    log_level: str = Field(
        default="info",
        description="Logging level"
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.reload or self.log_level == "debug"


# app/core/config/model.py
class ModelSettings(BaseSettings):
    """Model configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="MLOPS_MODEL_",
        case_sensitive=True
    )

    name: str = Field(
        default="distilbert-base-uncased-finetuned-sst-2-english",
        description="Hugging Face model name"
    )

    backend: str = Field(
        default="onnx",
        description="Model backend (onnx, pytorch, mock)"
    )

    cache_dir: str = Field(
        default="./models",
        description="Model cache directory"
    )

    max_length: int = Field(
        default=512,
        ge=1,
        le=512,
        description="Maximum input sequence length"
    )
```

### Settings Aggregator

```python
# app/core/config/settings.py
from functools import lru_cache
from .base import BaseConfig, Profile
from .server import ServerSettings
from .model import ModelSettings
from .redis import RedisSettings
from .kafka import KafkaSettings
from .security import SecuritySettings
from .observability import ObservabilitySettings

class Settings(BaseConfig):
    """Main settings aggregator with profile-based defaults."""

    # Profile
    PROFILE: Profile = Profile.LOCAL

    # Domain-specific settings
    server: ServerSettings = Field(default_factory=ServerSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    def __init__(self, **kwargs):
        """Initialize settings with profile-based defaults."""
        super().__init__(**kwargs)
        self._apply_profile_defaults()

    def _apply_profile_defaults(self):
        """Apply profile-specific defaults."""
        if self.PROFILE == Profile.LOCAL:
            self._apply_local_defaults()
        elif self.PROFILE == Profile.DEVELOPMENT:
            self._apply_development_defaults()
        elif self.PROFILE == Profile.STAGING:
            self._apply_staging_defaults()
        elif self.PROFILE == Profile.PRODUCTION:
            self._apply_production_defaults()

    def _apply_local_defaults(self):
        """Defaults for local development."""
        if not os.getenv("MLOPS_SERVER_RELOAD"):
            self.server.reload = True
        if not os.getenv("MLOPS_SERVER_WORKERS"):
            self.server.workers = 1
        if not os.getenv("MLOPS_MODEL_BACKEND"):
            self.model.backend = "mock"  # Fast startup
        if not os.getenv("MLOPS_REDIS_ENABLED"):
            self.redis.enabled = False  # Optional
        if not os.getenv("MLOPS_OBSERVABILITY_TRACING_ENABLED"):
            self.observability.tracing_enabled = False

    def _apply_production_defaults(self):
        """Defaults for production."""
        if not os.getenv("MLOPS_SERVER_RELOAD"):
            self.server.reload = False
        if not os.getenv("MLOPS_SERVER_WORKERS"):
            self.server.workers = 4
        if not os.getenv("MLOPS_MODEL_BACKEND"):
            self.model.backend = "onnx"
        if not os.getenv("MLOPS_REDIS_ENABLED"):
            self.redis.enabled = True
        if not os.getenv("MLOPS_SECURITY_RATE_LIMIT_ENABLED"):
            self.security.rate_limit_enabled = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### Usage in Application

```python
# app/main.py
from app.core.config import get_settings

settings = get_settings()

# Access settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins,
    allow_credentials=True,
)

# Use profile-based behavior
if settings.PROFILE == Profile.PRODUCTION:
    # Production-specific setup
    setup_sentry(settings.observability.sentry_dsn)
```

### Environment Variable Override

```bash
# .env.local
PROFILE=local
MLOPS_SERVER_PORT=8000
MLOPS_SERVER_RELOAD=true
MLOPS_MODEL_BACKEND=mock

# .env.development
PROFILE=development
MLOPS_SERVER_PORT=8000
MLOPS_REDIS_HOST=redis-dev.example.com
MLOPS_KAFKA_BOOTSTRAP_SERVERS=kafka-dev.example.com:9092

# .env.production
PROFILE=production
MLOPS_SERVER_PORT=8000
MLOPS_SERVER_WORKERS=8
MLOPS_REDIS_HOST=redis-prod.example.com
MLOPS_REDIS_PASSWORD=${REDIS_PASSWORD}
```

### Validation Example

```python
# app/core/config/redis.py
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    enabled: bool = Field(default=True, description="Enable Redis caching")
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    password: str | None = Field(default=None, description="Redis password")
    max_connections: int = Field(default=50, ge=1, description="Max connections")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate Redis host is not empty."""
        if not v or v.strip() == "":
            raise ValueError("Redis host cannot be empty")
        return v

    @property
    def url(self) -> str:
        """Construct Redis URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"
```

## Profile Comparison

| Setting | Local | Development | Staging | Production |
|---------|-------|-------------|---------|------------|
| Reload | ✅ | ❌ | ❌ | ❌ |
| Workers | 1 | 2 | 4 | 8 |
| Model Backend | mock | onnx | onnx | onnx |
| Redis | Optional | ✅ | ✅ | ✅ |
| Kafka | Optional | ✅ | ✅ | ✅ |
| Tracing | ❌ | ✅ | ✅ | ✅ |
| Rate Limiting | ❌ | ❌ | ✅ | ✅ |
| Debug Logging | ✅ | ✅ | ❌ | ❌ |

## Migration Strategy

### Backward Compatibility

```python
# Support legacy environment variables
class Settings(BaseConfig):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._migrate_legacy_env_vars()

    def _migrate_legacy_env_vars(self):
        """Map legacy environment variables to new structure."""
        # Legacy: REDIS_HOST -> New: MLOPS_REDIS_HOST
        if os.getenv("REDIS_HOST") and not os.getenv("MLOPS_REDIS_HOST"):
            self.redis.host = os.getenv("REDIS_HOST")

        # Legacy: MODEL_NAME -> New: MLOPS_MODEL_NAME
        if os.getenv("MODEL_NAME") and not os.getenv("MLOPS_MODEL_NAME"):
            self.model.name = os.getenv("MODEL_NAME")
```

### Migration Path

1. **Phase 1** (Complete): Implement new configuration system
2. **Phase 2** (Complete): Add backward compatibility layer
3. **Phase 3** (In Progress): Update documentation
4. **Phase 4** (Planned): Migrate existing deployments
5. **Phase 5** (Future): Deprecate legacy environment variables

## Benefits Demonstrated

### Before (Monolithic)

```python
# Old: Single large file, no organization
class Settings(BaseSettings):
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    MODEL_NAME: str = "distilbert..."
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    # ... 50+ more settings
```

### After (Profile-Based)

```python
# New: Organized, typed, documented
settings = get_settings()

# Clear domain separation
settings.server.host
settings.server.port

settings.redis.host
settings.redis.port

settings.model.name
settings.kafka.bootstrap_servers

# Profile-based defaults
if settings.PROFILE == Profile.LOCAL:
    # Automatically gets local-friendly defaults
```

## Operational Considerations

### Configuration Discovery

```bash
# List all settings
python -c "from app.core.config import get_settings; print(get_settings().model_dump_json(indent=2))"

# Validate configuration
python -c "from app.core.config import get_settings; get_settings()"
```

### Secret Management Integration

```python
# app/core/config/vault.py
from app.core.secrets import VaultClient

class Settings(BaseConfig):
    def __post_init__(self):
        """Load secrets from Vault after initialization."""
        if self.vault.enabled:
            vault = VaultClient(self.vault.url, self.vault.role)

            # Override sensitive settings from Vault
            secrets = vault.get_secret("kubesentiment/config")
            self.redis.password = secrets.get("redis_password")
            self.kafka.password = secrets.get("kafka_password")
```

## Testing

### Test Configuration

```python
# tests/conftest.py
import pytest
from app.core.config import Settings, Profile

@pytest.fixture
def test_settings():
    """Provide test configuration."""
    return Settings(
        PROFILE=Profile.LOCAL,
        server={"port": 8001, "reload": False},
        model={"backend": "mock"},
        redis={"enabled": False},
    )

# Usage in tests
def test_endpoint(test_settings):
    app.dependency_overrides[get_settings] = lambda: test_settings
    # Test with mock configuration
```

## References

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/usage/pydantic_settings/)
- [12-Factor App Configuration](https://12factor.net/config)
- [Settings Implementation](../../app/core/config/settings.py)
- [Configuration Domains](../../app/core/config/)
- [Environment Templates](../../.env.*.template)

## Related ADRs

- [ADR 002: Use Redis for Distributed Caching](002-use-redis-for-distributed-caching.md) - Redis configuration
- [ADR 003: Use Kafka for Async Processing](003-use-kafka-for-async-processing.md) - Kafka configuration
- [ADR 006: Use HashiCorp Vault for Secrets Management](006-use-hashicorp-vault-for-secrets.md) - Vault integration
- [ADR 004: Use FastAPI as Web Framework](004-use-fastapi-as-web-framework.md) - Settings dependency injection
- [ADR 011: Standardize Concurrency and Serialization](011-standardize-concurrency-serialization.md) - Uses profile configuration for thread settings

## Change History

- 2024-03-15: Initial decision
- 2024-04-01: Implementation complete
- 2024-04-20: Backward compatibility layer added
- 2024-05-15: All environments migrated
- 2025-11-18: Added to ADR repository
