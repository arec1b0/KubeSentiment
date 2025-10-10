# Test Suite Documentation

## Overview

Comprehensive test suite for the refactored MLOps sentiment analysis service, covering:

- LRU cache implementation
- Refactored predict() methods
- Unified API with strategy pattern
- Config validators
- Integration tests

## Test Structure

```plaintext
tests/
├── README.md                      # This file
├── test_api.py                    # Original API tests
├── test_correlation_logging.py   # Correlation ID tests
├── test_dependency_injection.py  # Dependency injection tests
├── test_error_handlers.py         # Error handling tests
├── test_input_validation.py       # Input validation tests
├── test_integration.py            # Integration tests
├── test_middleware.py             # Middleware tests
├── test_monitoring_cache.py       # Monitoring cache tests
├── test_lru_cache.py              # NEW: LRU cache tests
├── test_refactored_predict.py     # NEW: Refactored predict tests
├── test_unified_api.py            # NEW: Unified API tests
└── test_config_validators.py      # NEW: Config validator tests
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html --cov-report=term
```

### Run Specific Test Markers

**Unit Tests Only:**

```bash
pytest -m unit
```

**Integration Tests Only:**

```bash
pytest -m integration
```

**Cache Tests:**

```bash
pytest -m cache
```

**Strategy Pattern Tests:**

```bash
pytest -m strategy
```

### Run Specific Test Files

```bash
# LRU cache tests
pytest tests/test_lru_cache.py -v

# Refactored predict tests
pytest tests/test_refactored_predict.py -v

# Unified API tests
pytest tests/test_unified_api.py -v

# Config validator tests
pytest tests/test_config_validators.py -v
```

### Run Tests with Different Verbosity

```bash
# Minimal output
pytest -q

# Verbose output
pytest -v

# Very verbose output
pytest -vv
```

## Test Markers

The test suite uses the following pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, require dependencies)
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.cache` - Tests for caching functionality
- `@pytest.mark.strategy` - Tests for strategy pattern

## Coverage Requirements

- **Minimum Coverage**: 85%
- **Target Coverage**: 90%+
- **Coverage Reports**: Generated in `htmlcov/` directory

### View Coverage Report

```bash
# Generate and open HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Test Categories

### 1. LRU Cache Tests (`test_lru_cache.py`)

Tests for the LRU cache implementation:

- Cache key generation with BLAKE2b
- LRU eviction order
- Cache move-to-end on access
- Cache clearing
- Cache hit/miss behavior
- Performance benchmarks

**Example:**

```bash
pytest tests/test_lru_cache.py::TestLRUCache::test_lru_eviction_order -v
```

### 2. Refactored Predict Tests (`test_refactored_predict.py`)

Tests for the refactored predict() method and helper functions:

- `_validate_input_text()`
- `_try_get_cached_result()`
- `_preprocess_text()`
- `_run_model_inference()`
- `_record_prediction_metrics()`
- Full orchestration workflow

**Example:**

```bash
pytest tests/test_refactored_predict.py::TestValidateInputText -v
```

### 3. Unified API Tests (`test_unified_api.py`)

Tests for the unified API with strategy pattern:

- Backend selection logic
- Strategy pattern implementation
- API endpoint consistency
- Protocol compliance
- Multi-backend support

**Example:**

```bash
pytest tests/test_unified_api.py::TestBackendSelection -v
```

### 4. Config Validator Tests (`test_config_validators.py`)

Tests for extracted config validators:

- `_validate_model_in_allowed_list()`
- `_validate_worker_count_consistency()`
- `_validate_cache_memory_usage()`
- Field validators
- CORS validation
- API key validation

**Example:**

```bash
pytest tests/test_config_validators.py::TestConfigValidators -v
```

## CI/CD Integration

Tests run automatically in GitHub Actions on:

- Push to `main` or `develop` branches
- Pull requests

### CI Pipeline Steps

1. **Code Quality Checks** - black, isort, ruff, flake8, mypy
2. **Unit Tests** - Fast unit tests with coverage
3. **Integration Tests** - Integration tests with coverage
4. **Coverage Report** - Uploaded to Codecov

## Writing New Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test Structure

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestMyFeature:
    """Test suite for my feature."""
    
    @pytest.fixture
    def mock_dependency(self):
        """Fixture for mocking dependencies."""
        return Mock()
    
    def test_feature_success(self, mock_dependency):
        """Test feature works correctly."""
        # Arrange
        expected = "result"
        
        # Act
        result = my_feature(mock_dependency)
        
        # Assert
        assert result == expected
```

### Best Practices

1. **Use fixtures** for common setup
2. **Mock external dependencies** (models, APIs, databases)
3. **Follow AAA pattern** (Arrange, Act, Assert)
4. **Test edge cases** and error conditions
5. **Use descriptive names** for tests
6. **Keep tests isolated** and independent
7. **Add docstrings** to explain test purpose

## Debugging Tests

### Run Specific Test with Debug Output

```bash
pytest tests/test_lru_cache.py::TestLRUCache::test_lru_eviction_order -vv -s
```

### Drop into PDB on Failure

```bash
pytest --pdb
```

### Show Local Variables on Failure

```bash
pytest -l
```

### Stop on First Failure

```bash
pytest -x
```

## Performance Testing

### Run Performance Benchmarks

```bash
pytest tests/test_lru_cache.py::TestLRUCache::test_performance_blake2b_vs_sha256 -v
```

### Profile Tests

```bash
pytest --profile
```

## Continuous Monitoring

### Watch Mode (with pytest-watch)

```bash
pip install pytest-watch
ptw tests/
```

### Coverage Tracking

```bash
# Track coverage over time
pytest --cov=app --cov-report=term-missing | tee coverage.log
```

## Troubleshooting

### Common Issues

**Issue**: Tests fail with import errors

```bash
# Solution: Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio
```

**Issue**: Coverage too low

```bash
# Solution: Check uncovered lines
pytest --cov=app --cov-report=term-missing
```

**Issue**: Slow tests

```bash
# Solution: Run without slow tests
pytest -m "not slow"
```

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
