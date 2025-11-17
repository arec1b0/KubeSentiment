# Test Suite Documentation

## Overview

Comprehensive test suite for the KubeSentiment MLOps service with organized structure for unit, integration, and performance tests.

## Test Structure

```plaintext
tests/
├── README.md                          # This file
├── conftest.py                        # Shared pytest configuration and fixtures
├── fixtures/                          # Shared test utilities and fixtures
│   ├── __init__.py
│   ├── common_mocks.py               # Common mock classes (MockModel, MockSettings, etc.)
│   └── common_fixtures.py            # Shared pytest fixtures
├── unit/                             # Unit tests (fast, isolated, heavily mocked)
│   ├── test_api.py                   # API endpoint tests
│   ├── test_anomaly_buffer.py        # Anomaly buffer tests
│   ├── test_config_validators.py     # Config validation tests
│   ├── test_correlation_logging.py   # Correlation ID tests
│   ├── test_dependency_injection.py  # DI tests
│   ├── test_error_handlers.py        # Error handling tests
│   ├── test_health_check.py          # Health check tests
│   ├── test_input_validation.py      # Input validation tests
│   ├── test_load_balancer.py         # Load balancer tests
│   ├── test_logging_adapters.py      # Logging adapter tests
│   ├── test_lru_cache.py             # LRU cache tests
│   ├── test_middleware.py            # Middleware tests
│   ├── test_monitoring_cache.py      # Monitoring cache tests
│   ├── test_refactored_predict.py    # Refactored predict tests
│   └── test_unified_api.py           # Unified API tests
├── integration/                       # Integration tests (slower, test interactions)
│   ├── test_async_batch.py           # Async batch service tests
│   ├── test_integration.py           # Full integration tests
│   ├── test_kafka_consumer.py        # Kafka consumer tests
│   ├── test_model_warmup.py          # Model warmup tests
│   └── test_vault_integration.py     # Vault integration tests
└── performance/                       # Performance and benchmark tests
    └── test_benchmark.py             # Performance benchmarks
```

## Running Tests

### Run All Tests

```bash
# Run all tests
pytest

# Run all tests with verbose output
pytest -v
```

### Run Tests by Category

```bash
# Run only unit tests (fastest)
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run only performance tests
pytest tests/performance/ -v
```

### Run with Coverage

```bash
# All tests with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Unit tests only with coverage
pytest tests/unit/ --cov=app --cov-report=term-missing

# Integration tests with coverage
pytest tests/integration/ --cov=app --cov-report=term-missing
```

### Run Specific Test Markers

```bash
# Unit tests only (using markers)
pytest -m unit

# Integration tests only
pytest -m integration

# Performance tests only
pytest -m performance

# Exclude slow tests
pytest -m "not slow"

# Cache-related tests only
pytest -m cache

# Strategy pattern tests
pytest -m strategy

# Async tests
pytest -m async

# Kafka integration tests
pytest -m kafka

# Vault integration tests
pytest -m vault
```

### Run Specific Test Files

```bash
# Unit test examples
pytest tests/unit/test_lru_cache.py -v
pytest tests/unit/test_unified_api.py -v

# Integration test examples
pytest tests/integration/test_kafka_consumer.py -v
pytest tests/integration/test_vault_integration.py -v

# Performance test
pytest tests/performance/test_benchmark.py -v
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/unit/test_lru_cache.py::TestLRUCache -v

# Run a specific test function
pytest tests/unit/test_lru_cache.py::TestLRUCache::test_lru_eviction_order -v
```

## Test Markers

The test suite uses the following pytest markers (defined in `pyproject.toml`):

| Marker | Description | Usage |
|--------|-------------|-------|
| `@pytest.mark.unit` | Fast, isolated unit tests with heavy mocking | Applied to all tests in `tests/unit/` |
| `@pytest.mark.integration` | Integration tests that test component interactions | Applied to all tests in `tests/integration/` |
| `@pytest.mark.performance` | Performance and benchmark tests | Applied to all tests in `tests/performance/` |
| `@pytest.mark.e2e` | End-to-end tests (full system) | For future E2E tests |
| `@pytest.mark.slow` | Tests that take longer to run | Can be excluded with `-m "not slow"` |
| `@pytest.mark.cache` | Tests for caching functionality | LRU cache tests |
| `@pytest.mark.strategy` | Tests for strategy pattern implementation | Unified API backend tests |
| `@pytest.mark.async` | Tests using async/await | Async batch, Kafka tests |
| `@pytest.mark.kafka` | Kafka-specific integration tests | Kafka consumer tests |
| `@pytest.mark.vault` | Vault-specific integration tests | Vault integration tests |

## Coverage Requirements

- **Minimum Coverage**: 85% (enforced on combined test suite in CI)
- **Target Coverage**: 90%+
- **Coverage Reports**: Generated in `htmlcov/` directory and `coverage.xml`

### Important: Coverage Threshold Behavior

The 85% coverage threshold is **NOT** enforced on individual test categories (unit/integration/performance) when run separately. This is intentional:

- **Unit tests alone** may only cover 40-50% of the codebase
- **Integration tests alone** may cover different 40-50% of the codebase
- **Combined tests** achieve the required 85%+ coverage

**In CI**: The threshold is enforced only in the `coverage-check` job that runs all tests together.

**Locally**: You can run tests without threshold enforcement:
```bash
# Run individual test categories (no threshold check)
pytest tests/unit/ --cov=app
pytest tests/integration/ --cov=app

# Run all tests with threshold enforcement
pytest tests/ --cov=app --cov-fail-under=85
```

### View Coverage Report

```bash
# Generate and open HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html      # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html     # Windows
```

## Shared Fixtures and Mocks

The test suite provides shared fixtures and mocks to reduce duplication:

### Common Mocks (`tests/fixtures/common_mocks.py`)

- `MockModel` - Mock ML model for prediction testing
- `MockAsyncModel` - Mock async ML model
- `MockSettings` - Mock application settings
- `MockPerformanceConfig` - Mock performance configuration
- `MockKafkaSettings` - Mock Kafka settings
- `create_mock_analyzer()` - Factory for mock SentimentAnalyzer

### Common Fixtures (`tests/fixtures/common_fixtures.py`)

- `mock_model` - Provides MockModel instance
- `mock_settings` - Provides MockSettings instance
- `mock_analyzer` - Provides mock SentimentAnalyzer
- `test_app` - Provides configured FastAPI test app
- `client` - Provides FastAPI TestClient

### Usage Example

```python
import pytest
from tests.fixtures.common_mocks import MockModel, MockSettings

@pytest.mark.unit
class TestMyFeature:
    """Test my feature using shared fixtures."""

    def test_with_shared_fixtures(self, mock_model, mock_settings):
        """Test using shared fixtures from conftest."""
        # Fixtures are automatically available
        assert mock_model.is_ready()
        assert mock_settings.enable_metrics

    def test_with_custom_mock(self):
        """Test with custom mock instance."""
        # Can also create custom instances
        model = MockModel()
        assert model.is_ready()
```

## CI/CD Integration

Tests run automatically in GitHub Actions (`.github/workflows/ci.yml`) with separate stages:

### CI Pipeline Stages

1. **Code Quality (`lint`)** - Runs in parallel
   - black, isort, ruff, flake8, mypy checks

2. **Unit Tests (`unit-tests`)** - Runs in parallel with lint
   - Fast, isolated tests
   - Coverage collected (no threshold enforcement)
   - Coverage uploaded with `unit` flag

3. **Integration Tests (`integration-tests`)** - Runs after unit tests
   - Component interaction tests
   - Coverage collected (no threshold enforcement)
   - Coverage uploaded with `integration` flag

4. **Performance Tests (`performance-tests`)** - Runs after unit tests
   - Benchmark tests
   - Coverage collected (no threshold enforcement)
   - Coverage uploaded with `performance` flag

5. **Coverage Verification (`coverage-check`)** - Runs after all test stages
   - **Enforces 85% coverage threshold on combined test suite**
   - Runs all tests together to verify total coverage
   - Uploads combined coverage report
   - **CI fails here if coverage < 85%**

6. **Build** - Runs after lint and coverage check pass
   - Docker image build and push

### CI Test Commands

```bash
# Lint
black --check app/ tests/
isort --check-only app/ tests/
ruff check app/ tests/
flake8 app/ tests/

# Unit tests (no threshold)
pytest tests/unit/ -v -m "unit" --cov=app

# Integration tests (no threshold)
pytest tests/integration/ -v -m "integration" --cov=app

# Performance tests (no threshold)
pytest tests/performance/ -v -m "performance" --cov=app

# Coverage verification (enforces 85% threshold)
pytest tests/ -v --cov=app --cov-fail-under=85
```

## Writing New Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Choosing Test Category

**Unit Tests (`tests/unit/`)**
- Test single functions/classes in isolation
- Heavy use of mocking
- No external dependencies (database, Kafka, Vault, etc.)
- Fast execution (< 1 second per test)
- Examples: validators, utilities, pure functions

**Integration Tests (`tests/integration/`)**
- Test multiple components working together
- May use real services or complex mocks
- Test data flow between components
- Slower execution (1-10 seconds per test)
- Examples: API routes, service layer, message processing

**Performance Tests (`tests/performance/`)**
- Benchmark performance metrics
- Test throughput, latency, resource usage
- May run longer to get accurate measurements
- Examples: cache performance, batch processing speed

### Example Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from tests.fixtures.common_mocks import MockModel, MockSettings

@pytest.mark.unit  # Always add appropriate marker
class TestMyFeature:
    """Test suite for my feature."""

    @pytest.fixture
    def custom_fixture(self, mock_settings):
        """Custom fixture using shared fixtures."""
        # Can build on shared fixtures
        mock_settings.my_custom_setting = True
        return mock_settings

    def test_feature_success(self, mock_model, custom_fixture):
        """Test feature works correctly.

        This test verifies that...
        """
        # Arrange
        expected_result = {"status": "success"}

        # Act
        result = my_feature(mock_model, custom_fixture)

        # Assert
        assert result == expected_result
        assert mock_model.is_ready()

    def test_feature_error_handling(self, mock_model):
        """Test feature handles errors correctly."""
        # Arrange
        mock_model.predict_batch.side_effect = Exception("Test error")

        # Act & Assert
        with pytest.raises(Exception, match="Test error"):
            my_feature(mock_model)
```

### Best Practices

1. **Use shared fixtures** from `conftest.py` and `fixtures/`
2. **Add markers** to all test classes/functions
3. **Follow AAA pattern** (Arrange, Act, Assert)
4. **Test edge cases** and error conditions
5. **Use descriptive names** that explain what is tested
6. **Keep tests isolated** and independent
7. **Add docstrings** explaining test purpose
8. **Mock external dependencies** (don't make real API calls)
9. **Place tests in correct directory** (unit/integration/performance)
10. **Keep tests fast** - especially unit tests

## Debugging Tests

### Run with Debug Output

```bash
# Verbose output with print statements
pytest tests/unit/test_lru_cache.py -vv -s

# Show local variables on failure
pytest tests/unit/test_lru_cache.py -l

# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Drop into debugger on error (not assertion failure)
pytest --pdbcls=IPython.terminal.debugger:TerminalPdb --pdb
```

### Common Debug Commands

```bash
# Run single test with full output
pytest tests/unit/test_api.py::TestPredictEndpoint::test_predict_success -vv -s

# See test collection without running
pytest --collect-only

# Show available fixtures
pytest --fixtures

# Show test duration
pytest --durations=10
```

## Performance Testing

### Run Benchmarks

```bash
# All performance tests
pytest tests/performance/ -v

# Specific benchmark
pytest tests/performance/test_benchmark.py::TestCachePerformance -v

# With timing information
pytest tests/performance/ --durations=0
```

### Profiling Tests

```bash
# Profile test execution
pytest --profile tests/

# Profile with cProfile
python -m cProfile -o profile.stats -m pytest tests/unit/

# Analyze profile
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

## Continuous Monitoring

### Watch Mode

```bash
# Install pytest-watch
pip install pytest-watch

# Watch for changes and re-run tests
ptw tests/

# Watch specific directory
ptw tests/unit/
```

### Coverage Tracking

```bash
# Track coverage over time
pytest --cov=app --cov-report=term-missing | tee coverage.log

# Fail if coverage drops below threshold
pytest --cov=app --cov-fail-under=85
```

## Troubleshooting

### Common Issues

**Issue**: Tests fail with import errors

```bash
# Solution: Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

**Issue**: Coverage too low

```bash
# Solution: Check uncovered lines
pytest --cov=app --cov-report=term-missing

# Generate detailed HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

**Issue**: Slow test execution

```bash
# Solution: Run only fast unit tests
pytest tests/unit/ -v

# Skip slow tests
pytest -m "not slow"

# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest -n auto
```

**Issue**: Fixture not found

```bash
# Solution: Check fixture is in conftest.py or imported
pytest --fixtures | grep fixture_name

# Verify conftest.py is being loaded
pytest --setup-show
```

**Issue**: Tests pass locally but fail in CI

```bash
# Solution: Run with same environment variables
MLOPS_DEBUG=true MLOPS_LOG_LEVEL=DEBUG pytest tests/

# Check for missing dependencies
pip freeze > local-requirements.txt
diff local-requirements.txt requirements.txt
```

## Migration Guide

If you have existing tests, here's how to migrate them:

1. **Determine test category**: Unit, Integration, or Performance
2. **Move test file** to appropriate directory
3. **Add test marker**: `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.performance`
4. **Update imports**: Use shared fixtures from `tests.fixtures.common_fixtures`
5. **Update mocks**: Replace custom mocks with shared mocks from `tests.fixtures.common_mocks`
6. **Run tests**: Verify tests still pass

Example migration:

```python
# Before (old structure)
# tests/test_my_feature.py
class TestMyFeature:
    def mock_model(self):
        # Custom mock implementation
        pass

# After (new structure)
# tests/unit/test_my_feature.py
import pytest

@pytest.mark.unit  # Added marker
class TestMyFeature:
    def test_my_feature(self, mock_model):  # Using shared fixture
        # mock_model automatically available
        pass
```

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [GitHub Actions CI/CD](https://docs.github.com/en/actions)

## Contributing

When adding new tests:

1. Place in correct directory (`unit/`, `integration/`, or `performance/`)
2. Add appropriate markers
3. Use shared fixtures and mocks when possible
4. Follow naming conventions
5. Add docstrings
6. Ensure tests pass locally before committing
7. Update this README if adding new test categories
