# KubeSentiment Refactoring Plan

**Version:** 1.0
**Date:** 2025-10-23
**Status:** Proposed

## Executive Summary

The KubeSentiment codebase shows signs of **incomplete refactoring**, resulting in duplicate code, multiple competing API implementations, broken dependencies, and inconsistent import patterns. This plan provides a structured approach to consolidate the codebase into a clean, maintainable state.

**Estimated Effort:** 3-5 days
**Risk Level:** Medium
**Expected Impact:** High (improved maintainability, reduced technical debt)

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Critical Issues](#critical-issues)
3. [Refactoring Strategy](#refactoring-strategy)
4. [Phase 1: Core Infrastructure](#phase-1-core-infrastructure)
5. [Phase 2: API Consolidation](#phase-2-api-consolidation)
6. [Phase 3: Middleware & Logging](#phase-3-middleware--logging)
7. [Phase 4: Monitoring & Cleanup](#phase-4-monitoring--cleanup)
8. [Testing Strategy](#testing-strategy)
9. [Rollback Plan](#rollback-plan)
10. [Success Criteria](#success-criteria)

---

## Current State Analysis

### Code Duplication Summary

| Category | Duplicate Files | Lines | Impact |
|----------|----------------|-------|--------|
| Configuration | `config.py` vs `core/config.py` | 330 vs 400 | HIGH |
| Exceptions | `exceptions.py` vs `utils/exceptions.py` | 203 vs 203 | HIGH |
| Error Codes | `error_codes.py` vs `utils/error_codes.py` | 116 vs 139 | HIGH |
| Logging | `logging_config.py` vs `core/logging.py` | 243 vs 260 | MEDIUM |
| API Implementations | 4 competing versions | ~1200+ | CRITICAL |
| Middleware | 3 implementations | ~250 | MEDIUM |
| Monitoring | 2 implementations | ~500 | MEDIUM |

**Total Duplicate/Dead Code:** ~600-800 lines

### Broken Dependencies

```python
# app/services/prediction.py
from app.models.factory import ModelFactory  # ❌ Does NOT exist
from app.models.base import ModelStrategy    # ❌ Does NOT exist

# Actual location:
# app/ml/model_strategy.py - Contains ModelStrategy protocol
# Missing: app/ml/factory.py - Needs to be created
```

### Import Inconsistencies

```python
# Pattern 1 (Legacy - 7 files)
from .config import get_settings

# Pattern 2 (Correct - 5 files)
from app.core.config import get_settings

# Pattern 3 (Mixed)
from app.config import Settings  # Old path
from app.core.config import get_settings  # New path
```

---

## Critical Issues

### Issue 1: Multiple API Implementations ⚠️ CRITICAL

**Problem:** Four different API implementations coexist:

1. `/app/api.py` (307 lines) - Legacy implementation
2. `/app/api_onnx.py` (319 lines) - ONNX-specific variant
3. `/app/unified_api.py` (330 lines) - Attempted unified version
4. `/app/api/routes/*.py` (organized) - **Currently active** ✓

**Impact:**
- Developer confusion about which implementation to modify
- Bug fixes must be applied to multiple files
- Inconsistent behavior between implementations
- Maintenance burden

**Resolution:** Keep only `/app/api/routes/` structure, delete others.

---

### Issue 2: Duplicate Configuration Classes ⚠️ HIGH

**Problem:** Two `Settings` classes with different capabilities:

```python
# app/config.py - Basic settings (330 lines)
class Settings(BaseSettings):
    # No Vault integration
    # Has duplicate return statement (line 329-330)

# app/core/config.py - Extended settings (400 lines)
class Settings(BaseSettings):
    # With Vault secret management
    # Properly implemented
```

**Impact:**
- Files importing from old location miss Vault features
- Security risk: secrets not properly managed in legacy path
- Validator changes must be duplicated

**Resolution:** Consolidate to `app/core/config.py`, update all imports.

---

### Issue 3: Broken Service Layer ⚠️ CRITICAL

**Problem:** Service layer references non-existent modules:

```python
# app/services/prediction.py
from app.models.factory import ModelFactory  # ❌ Missing
from app.models.base import ModelStrategy    # ❌ Wrong path
```

**Impact:**
- Service layer cannot be imported or used
- Dependency injection system is incomplete
- Forces direct model access, breaking abstraction

**Resolution:** Create `/app/ml/factory.py` with proper implementation.

---

### Issue 4: Duplicate Exceptions & Error Codes ⚠️ HIGH

**Problem:** Identical exception classes and error codes in two locations:

- `app/exceptions.py` vs `app/utils/exceptions.py`
- `app/error_codes.py` vs `app/utils/error_codes.py`

**Impact:**
- Import inconsistencies across codebase
- Exception handlers may not catch exceptions from different modules
- Error code additions must be duplicated

**Resolution:** Consolidate to `/app/utils/` directory.

---

### Issue 5: Code Quality Issues ⚠️ MEDIUM

**Duplicate statements:**
```python
# app/config.py:329-330
return settings
return settings  # ❌ Dead code

# app/utils/error_codes.py:138-139
raise HTTPException(...)
raise HTTPException(...)  # ❌ Unreachable
```

**Resolution:** Fix during consolidation.

---

## Refactoring Strategy

### Approach

1. **Incremental Changes**: Make small, testable changes
2. **Test After Each Phase**: Run test suite to ensure no regressions
3. **Git Commits Per Phase**: Enable easy rollback if needed
4. **Import Updates First**: Fix imports before deleting files
5. **Create Before Delete**: Add missing components before removing old ones

### Risk Mitigation

- Run full test suite after each phase
- Keep deleted files in a `deprecated/` branch for 30 days
- Document all breaking changes
- Create migration guide for any external integrations

---

## Phase 1: Core Infrastructure

**Priority:** CRITICAL
**Estimated Time:** 4-6 hours
**Risk:** Medium

### Objectives

1. Consolidate configuration management
2. Consolidate exception hierarchies
3. Consolidate error code definitions
4. Fix code quality issues (duplicate statements)

### Step 1.1: Consolidate Configuration

**Actions:**

1. **Review differences** between `app/config.py` and `app/core/config.py`
   ```bash
   diff app/config.py app/core/config.py
   ```

2. **Update imports** in affected files:
   - `app/api.py`: Change `from .config` → `from app.core.config`
   - `app/api_onnx.py`: Change `from .config` → `from app.core.config`
   - `app/unified_api.py`: Change `from .config` → `from app.core.config`
   - `app/middleware.py`: Change `from .config` → `from app.core.config`
   - `app/ml/sentiment.py`: Verify uses correct path
   - `app/ml/onnx_optimizer.py`: Verify uses correct path
   - `app/api/middleware/auth.py`: Verify uses correct path

3. **Run tests** to ensure imports work:
   ```bash
   pytest tests/test_config_validators.py -v
   ```

4. **Delete deprecated file**:
   ```bash
   git rm app/config.py
   ```

5. **Commit changes**:
   ```bash
   git add -A
   git commit -m "refactor: Consolidate configuration to app/core/config.py

   - Remove duplicate Settings class from app/config.py
   - Update all imports to use app.core.config
   - Fix duplicate return statement in old config
   - Standardize on Vault-enabled configuration

   Breaking change: Import path changed from app.config to app.core.config"
   ```

**Files Modified:** 7
**Files Deleted:** 1

---

### Step 1.2: Consolidate Exceptions

**Actions:**

1. **Compare exception definitions**:
   ```bash
   diff app/exceptions.py app/utils/exceptions.py
   ```

2. **Verify `app/utils/exceptions.py` has all exceptions:**
   - ServiceError
   - ValidationError
   - AuthenticationError
   - ModelNotLoadedError
   - TextEmptyError
   - TextTooLongError
   - ModelInferenceError
   - InvalidModelError
   - ONNXRuntimeError
   - SecretNotFoundError
   - VaultConnectionError
   - ConfigurationError

3. **Update imports** in affected files:
   - `app/ml/sentiment.py`: Change `from ..exceptions` → `from app.utils.exceptions`
   - `app/ml/onnx_optimizer.py`: Verify correct import
   - `app/api.py`: Change `from .exceptions` → `from app.utils.exceptions`
   - `app/api_onnx.py`: Change import if needed
   - `app/unified_api.py`: Change import if needed

4. **Run tests**:
   ```bash
   pytest tests/test_error_handlers.py -v
   pytest tests/test_api.py -v
   ```

5. **Delete deprecated file**:
   ```bash
   git rm app/exceptions.py
   ```

6. **Commit changes**:
   ```bash
   git add -A
   git commit -m "refactor: Consolidate exceptions to app/utils/exceptions.py

   - Remove duplicate exception definitions from app/exceptions.py
   - Update all imports to use app.utils.exceptions
   - Ensure consistent exception hierarchy across codebase

   Breaking change: Import path changed from app.exceptions to app.utils.exceptions"
   ```

**Files Modified:** 5
**Files Deleted:** 1

---

### Step 1.3: Consolidate Error Codes

**Actions:**

1. **Fix duplicate raise statement** in `app/utils/error_codes.py`:
   ```python
   # Before (lines 138-139):
   raise HTTPException(status_code=status_code, detail=error_response)
   raise HTTPException(status_code=status_code, detail=error_response)  # Remove this

   # After:
   raise HTTPException(status_code=status_code, detail=error_response)
   ```

2. **Update imports** in affected files:
   - `app/api.py`: Change `from .error_codes` → `from app.utils.error_codes`
   - `app/unified_api.py`: Change `from .error_codes` → `from app.utils.error_codes`
   - `app/api/routes/predictions.py`: Verify correct import

3. **Run tests**:
   ```bash
   pytest tests/test_error_handlers.py -v
   ```

4. **Delete deprecated file**:
   ```bash
   git rm app/error_codes.py
   ```

5. **Commit changes**:
   ```bash
   git add -A
   git commit -m "refactor: Consolidate error codes to app/utils/error_codes.py

   - Fix duplicate raise statement in utils/error_codes.py
   - Remove duplicate ErrorCode definitions from app/error_codes.py
   - Update all imports to use app.utils.error_codes

   Breaking change: Import path changed from app.error_codes to app.utils.error_codes"
   ```

**Files Modified:** 3
**Files Deleted:** 1

---

### Step 1.4: Verification

**Test Commands:**
```bash
# Run all tests
pytest tests/ -v

# Check for import errors
python -c "from app.core.config import Settings; print('✓ Config OK')"
python -c "from app.utils.exceptions import ModelNotLoadedError; print('✓ Exceptions OK')"
python -c "from app.utils.error_codes import ErrorCode; print('✓ Error codes OK')"

# Verify no references to old paths
grep -r "from .config import" app/ || echo "✓ No .config imports"
grep -r "from .exceptions import" app/ || echo "✓ No .exceptions imports"
grep -r "from .error_codes import" app/ || echo "✓ No .error_codes imports"
```

**Success Criteria:**
- [ ] All tests pass
- [ ] No imports from deprecated modules
- [ ] Configuration works with Vault integration
- [ ] Exception handling works consistently
- [ ] Error codes map correctly to HTTP responses

---

## Phase 2: API Consolidation

**Priority:** CRITICAL
**Estimated Time:** 6-8 hours
**Risk:** High

### Objectives

1. Establish `/app/api/routes/` as single API implementation
2. Create model factory to fix service layer
3. Remove competing API implementations
4. Fix dependency injection system

### Step 2.1: Create Model Factory

**Problem:** Service layer references missing `app/models/factory.py`

**Action: Create `/app/ml/factory.py`**

```python
"""
Model factory for creating sentiment analysis models.

This module provides a factory for instantiating different ML backends
(PyTorch, ONNX) based on configuration.
"""

from typing import Protocol
from app.core.config import Settings, get_settings
from app.ml.model_strategy import ModelStrategy
from app.ml.sentiment import SentimentAnalyzer, get_sentiment_analyzer
from app.ml.onnx_optimizer import ONNXSentimentAnalyzer, get_onnx_sentiment_analyzer


class ModelFactory:
    """
    Factory for creating sentiment analysis models based on backend type.

    Supports multiple backends:
    - pytorch: Standard PyTorch transformer model
    - onnx: Optimized ONNX Runtime model
    """

    @staticmethod
    def create_model(
        backend: str,
        settings: Settings | None = None
    ) -> ModelStrategy:
        """
        Create a sentiment analysis model based on backend type.

        Args:
            backend: Model backend type ('pytorch' or 'onnx')
            settings: Application settings (optional, will use default if not provided)

        Returns:
            ModelStrategy: Initialized model instance

        Raises:
            ValueError: If backend type is not supported
        """
        if settings is None:
            settings = get_settings()

        backend = backend.lower().strip()

        if backend == "onnx":
            return get_onnx_sentiment_analyzer(settings)
        elif backend in ("pytorch", "torch"):
            return get_sentiment_analyzer(settings)
        else:
            raise ValueError(
                f"Unsupported backend: {backend}. "
                f"Supported backends: pytorch, onnx"
            )

    @staticmethod
    def get_supported_backends() -> list[str]:
        """Return list of supported backend types."""
        return ["pytorch", "onnx"]


# Convenience function for dependency injection
def create_model(backend: str, settings: Settings | None = None) -> ModelStrategy:
    """
    Convenience function to create a model via the factory.

    Args:
        backend: Model backend type
        settings: Application settings (optional)

    Returns:
        ModelStrategy: Initialized model instance
    """
    return ModelFactory.create_model(backend, settings)
```

**Commit:**
```bash
git add app/ml/factory.py
git commit -m "feat: Add model factory for backend abstraction

- Create ModelFactory class for instantiating models
- Support PyTorch and ONNX backends
- Provide convenience function for dependency injection
- Fixes broken service layer dependencies"
```

---

### Step 2.2: Fix Service Layer

**Action: Update `/app/services/prediction.py` imports**

```python
# Before:
from app.models.factory import ModelFactory  # ❌ Wrong path
from app.models.base import ModelStrategy    # ❌ Wrong path

# After:
from app.ml.factory import ModelFactory      # ✓ Correct
from app.ml.model_strategy import ModelStrategy  # ✓ Correct
```

**Test:**
```bash
python -c "from app.services.prediction import PredictionService; print('✓ Service layer OK')"
pytest tests/test_refactored_predict.py -v
```

**Commit:**
```bash
git add app/services/prediction.py
git commit -m "fix: Update service layer imports to use ml.factory

- Change imports from app.models.* to app.ml.*
- Service layer now properly instantiable
- Fixes broken dependency injection"
```

---

### Step 2.3: Update Dependency Injection

**Action: Fix `/app/core/dependencies.py`**

Ensure it imports from the correct factory location:

```python
from app.ml.factory import ModelFactory
from app.ml.model_strategy import ModelStrategy
```

**Test:**
```bash
pytest tests/test_dependency_injection.py -v
```

**Commit:**
```bash
git add app/core/dependencies.py
git commit -m "fix: Update DI to use correct model factory import"
```

---

### Step 2.4: Verify Active API

**Action: Confirm `/app/main.py` uses organized routes**

```python
# app/main.py should have:
from app.api import router  # This imports from app/api/__init__.py
# which imports from app/api/routes/*
```

**Verification:**
```bash
# Check that organized routes are used
grep "from app.api import" app/main.py

# Start the service and test
uvicorn app.main:app --reload &
sleep 5
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"text": "This is a test"}' \
     | jq .
```

---

### Step 2.5: Remove Competing API Implementations

**Actions:**

1. **Remove legacy API files:**
   ```bash
   git rm app/api.py
   git rm app/api_onnx.py
   git rm app/unified_api.py
   ```

2. **Update any remaining references** (shouldn't be any if main.py is correct)

3. **Run full test suite:**
   ```bash
   pytest tests/ -v
   pytest tests/test_api.py -v
   pytest tests/test_unified_api.py -v  # This might need updating
   pytest tests/test_integration.py -v
   ```

4. **Commit changes:**
   ```bash
   git add -A
   git commit -m "refactor: Remove duplicate API implementations

   - Delete app/api.py (legacy implementation)
   - Delete app/api_onnx.py (ONNX-specific variant)
   - Delete app/unified_api.py (superseded by organized routes)
   - Keep only app/api/routes/* as single source of truth

   Reduces codebase by ~950 lines of duplicate code
   All functionality preserved in organized route structure"
   ```

**Files Deleted:** 3 (~950 lines removed)

---

### Step 2.6: Phase 2 Verification

**Test Commands:**
```bash
# Verify model factory works
pytest tests/test_integration.py -v -k "factory"

# Verify service layer works
pytest tests/test_refactored_predict.py -v

# Verify API endpoints work
pytest tests/test_api.py -v

# Test with both backends
curl -X POST "http://localhost:8000/predict?backend=pytorch" \
     -H "Content-Type: application/json" \
     -d '{"text": "Great service!"}'

curl -X POST "http://localhost:8000/predict?backend=onnx" \
     -H "Content-Type: application/json" \
     -d '{"text": "Great service!"}'
```

**Success Criteria:**
- [ ] Model factory successfully creates both PyTorch and ONNX models
- [ ] Service layer imports work without errors
- [ ] Dependency injection provides correct model instances
- [ ] All API endpoints respond correctly
- [ ] No references to deleted API files exist
- [ ] All tests pass

---

## Phase 3: Middleware & Logging

**Priority:** HIGH
**Estimated Time:** 3-4 hours
**Risk:** Low

### Objectives

1. Consolidate logging configuration
2. Consolidate middleware implementations
3. Ensure consistent request/response handling

### Step 3.1: Consolidate Logging

**Actions:**

1. **Compare logging implementations:**
   ```bash
   diff app/logging_config.py app/core/logging.py
   ```

2. **Update imports** in affected files:
   - `app/api.py`: Update (if not deleted yet)
   - `app/api_onnx.py`: Update (if not deleted yet)
   - `app/unified_api.py`: Update (if not deleted yet)
   - `app/ml/sentiment.py`: Change to `from app.core.logging import get_logger`
   - Any other files importing from `app.logging_config`

3. **Verify logging works:**
   ```bash
   pytest tests/test_correlation_logging.py -v
   ```

4. **Delete deprecated file:**
   ```bash
   git rm app/logging_config.py
   ```

5. **Commit:**
   ```bash
   git add -A
   git commit -m "refactor: Consolidate logging to app/core/logging.py

   - Remove duplicate logging setup from app/logging_config.py
   - Update all imports to use app.core.logging
   - Ensure consistent structured logging with correlation IDs

   Breaking change: Import path changed from app.logging_config to app.core.logging"
   ```

**Files Modified:** ~4
**Files Deleted:** 1

---

### Step 3.2: Consolidate Middleware

**Actions:**

1. **Verify `/app/api/middleware/` has all middleware:**
   - `auth.py` - Authentication middleware
   - `correlation.py` - Correlation ID middleware
   - `logging.py` - Request/response logging
   - `metrics.py` - Prometheus metrics

2. **Remove duplicate middleware files:**
   ```bash
   git rm app/middleware.py
   git rm app/correlation_middleware.py
   ```

3. **Verify `app/main.py` uses organized middleware:**
   ```python
   # Should have imports like:
   from app.api.middleware.correlation import CorrelationIdMiddleware
   from app.api.middleware.logging import LoggingMiddleware
   # etc.
   ```

4. **Test middleware:**
   ```bash
   pytest tests/test_middleware.py -v
   pytest tests/test_correlation_logging.py -v
   ```

5. **Commit:**
   ```bash
   git add -A
   git commit -m "refactor: Consolidate middleware to app/api/middleware/

   - Remove duplicate middleware implementations
   - Delete app/middleware.py and app/correlation_middleware.py
   - Use organized middleware structure in app/api/middleware/
   - All middleware functionality preserved"
   ```

**Files Deleted:** 2

---

### Step 3.3: Phase 3 Verification

**Test Commands:**
```bash
# Test structured logging
pytest tests/test_correlation_logging.py -v

# Test middleware
pytest tests/test_middleware.py -v

# Verify correlation IDs in logs
pytest tests/test_api.py -v -s | grep "correlation_id"
```

**Success Criteria:**
- [ ] Logging produces consistent structured output
- [ ] Correlation IDs appear in all log messages
- [ ] Middleware processes requests in correct order
- [ ] No duplicate middleware definitions exist
- [ ] All tests pass

---

## Phase 4: Monitoring & Cleanup

**Priority:** MEDIUM
**Estimated Time:** 2-3 hours
**Risk:** Low

### Objectives

1. Consolidate monitoring implementations
2. Clean up unused imports
3. Run final verification
4. Update documentation

### Step 4.1: Consolidate Monitoring

**Actions:**

1. **Compare monitoring implementations:**
   ```bash
   ls -lh app/monitoring.py
   ls -lh app/monitoring/
   ```

2. **Verify `/app/monitoring/` directory has:**
   - `prometheus.py` - Metrics collection
   - `health.py` - Health check endpoints
   - `vault_health.py` - Vault integration health

3. **Remove duplicate monitoring:**
   ```bash
   git rm app/monitoring.py
   ```

4. **Update imports** in affected files (if any still reference old path)

5. **Test monitoring:**
   ```bash
   pytest tests/test_monitoring_cache.py -v

   # Check metrics endpoint
   curl http://localhost:8000/metrics

   # Check health endpoint
   curl http://localhost:8000/health
   ```

6. **Commit:**
   ```bash
   git add -A
   git commit -m "refactor: Consolidate monitoring to app/monitoring/ directory

   - Remove duplicate monitoring.py implementation
   - Use organized monitoring structure in app/monitoring/
   - Preserve all Prometheus metrics and health checks"
   ```

**Files Deleted:** 1

---

### Step 4.2: Clean Up Unused Imports

**Action: Search for and fix any remaining issues**

```bash
# Check for unused imports
pylint app/ --disable=all --enable=unused-import 2>&1 | grep "unused-import"

# Check for imports from deleted modules
grep -r "from app.config import" app/ 2>&1 || echo "✓ No old config imports"
grep -r "from .config import" app/ 2>&1 || echo "✓ No relative config imports"
grep -r "from app.exceptions import" app/ 2>&1 || echo "✓ No old exception imports"
grep -r "from .exceptions import" app/ 2>&1 || echo "✓ No relative exception imports"
grep -r "from app.error_codes import" app/ 2>&1 || echo "✓ No old error_codes imports"
grep -r "from app.logging_config import" app/ 2>&1 || echo "✓ No old logging imports"
grep -r "from app.monitoring import" app/ 2>&1 | grep -v "from app.monitoring." || echo "✓ No old monitoring imports"
```

**Fix any issues found, then commit:**
```bash
git add -A
git commit -m "chore: Clean up unused imports and references"
```

---

### Step 4.3: Update Documentation

**Actions:**

1. **Update imports in README examples:**
   ```bash
   # Check if README has any import examples
   grep "from app" README.md
   ```

2. **Update architecture documentation:**
   - Edit `docs/architecture.md` to reflect new structure
   - Remove references to deleted modules
   - Update import examples

3. **Create migration guide** (`docs/MIGRATION.md`):
   ```markdown
   # Migration Guide - Refactoring v1.0

   ## Import Path Changes

   | Old Import | New Import |
   |------------|------------|
   | `from app.config import Settings` | `from app.core.config import Settings` |
   | `from app.exceptions import *` | `from app.utils.exceptions import *` |
   | `from app.error_codes import ErrorCode` | `from app.utils.error_codes import ErrorCode` |
   | `from app.logging_config import get_logger` | `from app.core.logging import get_logger` |
   | `from app.api import app` | `from app.main import app` |

   ## Deleted Modules

   - `app/api.py` → Use `app/api/routes/*`
   - `app/api_onnx.py` → Use `app/api/routes/predictions.py` with `backend` param
   - `app/unified_api.py` → Use `app/api/routes/*`
   - `app/config.py` → Use `app/core/config.py`
   - `app/exceptions.py` → Use `app/utils/exceptions.py`
   - `app/error_codes.py` → Use `app/utils/error_codes.py`
   - `app/logging_config.py` → Use `app/core/logging.py`
   - `app/middleware.py` → Use `app/api/middleware/*`
   - `app/correlation_middleware.py` → Use `app/api/middleware/correlation.py`
   - `app/monitoring.py` → Use `app/monitoring/prometheus.py`
   ```

4. **Commit documentation:**
   ```bash
   git add docs/
   git commit -m "docs: Update documentation for refactored structure

   - Update architecture documentation
   - Add migration guide for import path changes
   - Remove references to deleted modules"
   ```

---

### Step 4.4: Final Verification

**Complete Test Suite:**
```bash
# Run all tests
pytest tests/ -v --cov=app --cov-report=html

# Check test coverage (should be 90%+)
open htmlcov/index.html

# Verify no broken imports
python -m py_compile app/**/*.py

# Check for TODO/FIXME comments
grep -r "TODO\|FIXME" app/

# Verify app starts correctly
uvicorn app.main:app --reload &
APP_PID=$!
sleep 5

# Test key endpoints
curl http://localhost:8000/health | jq .
curl http://localhost:8000/metrics | head -20
curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"text": "This refactoring was successful!"}' | jq .

# Kill test server
kill $APP_PID
```

**Code Quality Checks:**
```bash
# Run linter
pylint app/ --rcfile=.pylintrc

# Run type checker
mypy app/ --ignore-missing-imports

# Check code formatting
black --check app/

# Run security scan
bandit -r app/ -ll
```

**Success Criteria:**
- [ ] All tests pass with 90%+ coverage
- [ ] No broken imports
- [ ] App starts without errors
- [ ] All API endpoints respond correctly
- [ ] Monitoring and health checks work
- [ ] Code quality checks pass
- [ ] Documentation is up to date

---

## Testing Strategy

### Test Categories

1. **Unit Tests**
   - Configuration validation: `tests/test_config_validators.py`
   - Exception handling: `tests/test_error_handlers.py`
   - Model factory: Create `tests/test_model_factory.py`

2. **Integration Tests**
   - API endpoints: `tests/test_api.py`
   - Service layer: `tests/test_refactored_predict.py`
   - Full workflow: `tests/test_integration.py`

3. **Middleware Tests**
   - Correlation IDs: `tests/test_correlation_logging.py`
   - Request/response: `tests/test_middleware.py`

4. **Performance Tests**
   - Load testing: `benchmarking/scripts/load-test.py`
   - Resource usage: `benchmarking/scripts/resource-monitor.py`

### Test Execution Schedule

**After Each Phase:**
```bash
# Quick smoke test
pytest tests/test_api.py tests/test_config_validators.py -v

# Full test if quick test passes
pytest tests/ -v
```

**Before Final Commit:**
```bash
# Complete test suite with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Integration tests
pytest tests/test_integration.py -v

# Performance regression check
python benchmarking/scripts/load-test.py --duration 60 --rps 100
```

---

## Rollback Plan

### If Issues Arise During Refactoring

**Option 1: Rollback Last Phase**
```bash
# View recent commits
git log --oneline -10

# Rollback to before phase started
git reset --hard <commit-hash>

# Or use git revert for safer rollback
git revert <commit-hash-1> <commit-hash-2>
```

**Option 2: Create Rollback Branch**
```bash
# Before starting each phase, create a backup
git branch backup/before-phase-1
git branch backup/before-phase-2
# etc.

# Rollback by switching branches
git checkout backup/before-phase-1
git branch -D claude/create-refactoring-*
git checkout -b claude/create-refactoring-retry-*
```

**Option 3: Incremental Rollback**
```bash
# Undo specific file changes
git checkout HEAD~1 -- app/core/config.py

# Restore deleted file
git checkout HEAD~1 -- app/config.py
```

### Recovery Testing

After any rollback:
```bash
# Ensure app still works
pytest tests/ -v
uvicorn app.main:app --reload

# Check for broken references
grep -r "from app.config import" app/
```

---

## Success Criteria

### Quantitative Metrics

- [ ] **Code Reduction:** Remove 600-800 lines of duplicate code
- [ ] **File Reduction:** Delete 10 deprecated files
- [ ] **Test Coverage:** Maintain 90%+ coverage after refactoring
- [ ] **Test Pass Rate:** 100% of existing tests pass
- [ ] **Import Consistency:** 0 imports from deprecated modules
- [ ] **Performance:** No degradation in API response times
- [ ] **Build Time:** No increase in Docker build time

### Qualitative Goals

- [ ] **Single Source of Truth:** Each component has one canonical implementation
- [ ] **Clear Architecture:** Organized directory structure with clear responsibilities
- [ ] **Consistent Patterns:** All files use same import conventions
- [ ] **Working Service Layer:** Dependency injection fully functional
- [ ] **Clean Codebase:** No duplicate statements or unreachable code
- [ ] **Updated Documentation:** All docs reflect new structure

### Validation Checklist

**Code Structure:**
- [ ] No duplicate config, exceptions, error codes, or logging
- [ ] Single API implementation in `app/api/routes/`
- [ ] Model factory exists and works correctly
- [ ] Service layer imports work without errors
- [ ] Middleware organized in `app/api/middleware/`
- [ ] Monitoring organized in `app/monitoring/`

**Code Quality:**
- [ ] No duplicate return/raise statements
- [ ] No unreachable code
- [ ] No broken imports
- [ ] No references to deleted modules
- [ ] Passes pylint with score > 8.0
- [ ] Passes mypy type checking

**Functionality:**
- [ ] App starts without errors
- [ ] All API endpoints work correctly
- [ ] Both PyTorch and ONNX backends work
- [ ] Health checks pass
- [ ] Metrics collection works
- [ ] Logging produces structured output with correlation IDs
- [ ] Vault integration works (if configured)

**Testing:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Test coverage ≥ 90%
- [ ] No test fixtures broken
- [ ] Performance tests show no regression

**Documentation:**
- [ ] Migration guide created
- [ ] Architecture docs updated
- [ ] README updated if needed
- [ ] API docs still accurate
- [ ] Comments in code updated

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Core Infrastructure | 4-6 hours | None |
| Phase 2: API Consolidation | 6-8 hours | Phase 1 complete |
| Phase 3: Middleware & Logging | 3-4 hours | Phase 1 complete |
| Phase 4: Monitoring & Cleanup | 2-3 hours | Phases 1-3 complete |
| **Total Estimated Time** | **15-21 hours** | **~3-5 days** |

### Recommended Schedule

**Day 1:**
- Phase 1: Core Infrastructure (all steps)
- Verification and testing

**Day 2:**
- Phase 2: API Consolidation (Steps 2.1-2.3)
- Testing

**Day 3:**
- Phase 2: API Consolidation (Steps 2.4-2.6)
- Phase 3: Middleware & Logging
- Testing

**Day 4:**
- Phase 4: Monitoring & Cleanup
- Final verification
- Documentation updates

**Day 5:**
- Buffer for issues
- Final testing and validation
- Code review

---

## Post-Refactoring Tasks

1. **Code Review:**
   - Review all changes with team
   - Verify architectural decisions
   - Check for any missed duplicates

2. **Performance Testing:**
   - Run full benchmark suite
   - Compare before/after metrics
   - Validate no regressions

3. **Documentation:**
   - Update team wiki/docs
   - Create demo of new structure
   - Document lessons learned

4. **Monitoring:**
   - Watch production metrics for 48 hours
   - Monitor error rates
   - Check resource usage

5. **Cleanup:**
   - Delete deprecated branches after 30 days
   - Archive old implementation docs
   - Update CI/CD pipelines if needed

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Test failures after consolidation | High | Medium | Run tests after each small change |
| Import errors in production | High | Low | Use absolute imports, verify with static analysis |
| Performance degradation | Medium | Low | Run benchmarks before/after |
| Broken Vault integration | Medium | Low | Test with Vault enabled/disabled |
| Merge conflicts | Low | Medium | Work on dedicated branch, frequent commits |
| Missing edge cases | Medium | Medium | Comprehensive test coverage, manual testing |

---

## Conclusion

This refactoring plan provides a structured approach to consolidating the KubeSentiment codebase. By following this plan incrementally and testing after each phase, we can safely eliminate technical debt while maintaining functionality.

**Expected Benefits:**
- ✅ 600-800 lines of duplicate code removed
- ✅ 10 deprecated files deleted
- ✅ Single source of truth for all components
- ✅ Consistent import patterns
- ✅ Working service layer with proper abstraction
- ✅ Improved maintainability and developer experience
- ✅ Reduced confusion about which implementation to use

**Next Steps:**
1. Review and approve this plan
2. Create backup branch: `backup/before-refactoring`
3. Begin Phase 1 execution
4. Monitor and adjust as needed

---

**Document Version:** 1.0
**Last Updated:** 2025-10-23
**Author:** Claude Code Refactoring Agent
**Review Status:** Pending Team Review
