# KubeSentiment Testing Guide

This comprehensive guide covers all testing strategies for the KubeSentiment MLOps platform, including unit tests, integration tests, load tests, and chaos engineering.

---

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Types Overview](#test-types-overview)
3. [Unit & Integration Tests](#unit--integration-tests)
4. [Load Testing](#load-testing)
5. [Chaos Engineering](#chaos-engineering)
6. [Security Testing](#security-testing)
7. [Performance Benchmarking](#performance-benchmarking)
8. [CI/CD Integration](#cicd-integration)
9. [Best Practices](#best-practices)

---

## Testing Philosophy

KubeSentiment follows a comprehensive testing strategy based on the Testing Pyramid:

```
    /\          E2E Tests (Chaos Engineering)
   /  \         ↑ High confidence, Slow, Expensive
  /----\        Integration Tests
 /------\       ↑ Medium confidence, Medium speed
/--------\      Unit Tests
                ↑ Low-level, Fast, Cheap
```

### Testing Goals

- **85% Code Coverage**: Minimum requirement enforced in CI/CD
- **Fast Feedback**: Unit tests run in <30 seconds
- **Production-like**: Integration tests use realistic scenarios
- **Resilience**: Chaos tests validate fault tolerance
- **Performance**: Load tests ensure scalability targets

---

## Test Types Overview

| Test Type | Purpose | Frequency | Duration | Environment |
|-----------|---------|-----------|----------|-------------|
| Unit Tests | Validate individual components | Every commit | <30s | Local/CI |
| Integration Tests | Test component interactions | Every commit | 1-2min | Local/CI |
| Load Tests | Validate performance under load | Daily/Weekly | 5-60min | Staging/Prod |
| Chaos Tests | Verify fault tolerance | Weekly | 10-30min | Staging |
| Security Scans | Detect vulnerabilities | Every build | 2-5min | CI/CD |
| Benchmarks | Performance regression testing | Per PR | 1-5min | Local/CI |

---

## Unit & Integration Tests

### Running Tests Locally

```bash
# Run all tests with coverage
make test

# Run specific test modules
pytest tests/test_lru_cache.py -v
pytest tests/test_kafka_consumer.py -v

# Run by marker
pytest -m unit              # Fast unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"        # Skip slow tests

# Run with coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html     # View coverage report
```

### Test Organization

```
tests/
├── test_api.py                     # API endpoint tests
├── test_lru_cache.py              # Cache implementation
├── test_refactored_predict.py     # Prediction orchestration
├── test_unified_api.py            # Strategy pattern
├── test_kafka_consumer.py         # Kafka integration
├── test_async_batch.py            # Batch processing
├── test_middleware.py             # HTTP middleware
├── test_health_check.py           # Health endpoints
└── chaos/                         # Chaos engineering
    ├── chaos_engineering_tests.py
    └── README.md
```

### Test Markers

Configure in `pytest.ini`:

```ini
[tool:pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    cache: tests related to caching
    strategy: tests for strategy pattern
```

### Writing New Tests

**Unit Test Template**:

```python
import pytest
from app.services.my_service import MyService


class TestMyService:
    """Test suite for MyService"""

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return MyService()

    def test_basic_functionality(self, service):
        """Test basic functionality"""
        result = service.do_something("test")
        assert result == "expected"

    @pytest.mark.parametrize("input,expected", [
        ("test1", "result1"),
        ("test2", "result2"),
    ])
    def test_multiple_inputs(self, service, input, expected):
        """Test with multiple input values"""
        result = service.do_something(input)
        assert result == expected
```

---

## Load Testing

### Overview

Located in `benchmarking/load_test.py`, this comprehensive load testing framework simulates realistic traffic patterns.

### Traffic Patterns

1. **Constant**: Steady RPS throughout test
2. **Ramp**: Gradually increase from low to high RPS
3. **Spike**: Periodic traffic bursts
4. **Wave**: Sinusoidal traffic pattern

### Running Load Tests

```bash
# Basic load test (100 RPS, 60 seconds)
python benchmarking/load_test.py \
  --url http://localhost:8000 \
  --rps 100 \
  --duration 60 \
  --pattern constant

# Ramp test (gradually increase load)
python benchmarking/load_test.py \
  --url http://mlops-sentiment.local \
  --rps 500 \
  --duration 300 \
  --pattern ramp \
  --output load_test_results.json

# Spike test (periodic bursts)
python benchmarking/load_test.py \
  --url http://localhost:8000 \
  --rps 200 \
  --duration 120 \
  --pattern spike

# Wave pattern (realistic daily traffic)
python benchmarking/load_test.py \
  --url http://localhost:8000 \
  --rps 300 \
  --duration 600 \
  --pattern wave
```

### Realistic Data Generation

The load tester generates realistic sentiment analysis requests:

- **Positive texts** (50%): Reviews, feedback, testimonials
- **Negative texts** (30%): Complaints, issues, problems
- **Neutral texts** (20%): Factual statements, descriptions

### Understanding Results

```json
{
  "summary": {
    "total_requests": 6000,
    "successful_requests": 5985,
    "failed_requests": 15,
    "success_rate": 99.75,
    "target_rps": 100,
    "actual_rps": 99.8
  },
  "latency": {
    "min_ms": 12.5,
    "max_ms": 245.3,
    "mean_ms": 45.2,
    "median_ms": 42.1,
    "p95_ms": 85.7,
    "p99_ms": 120.4
  }
}
```

### Performance Targets

| Metric | Target | Acceptable | Needs Investigation |
|--------|--------|------------|---------------------|
| Success Rate | >99.9% | >99% | <99% |
| P95 Latency | <100ms | <200ms | >200ms |
| P99 Latency | <250ms | <500ms | >500ms |
| Throughput | Meets RPS target | 90% of target | <90% of target |

### Load Testing Best Practices

1. **Start Small**: Begin with low RPS and gradually increase
2. **Monitor Resources**: Watch CPU, memory, and network during tests
3. **Use Realistic Data**: Generate varied text lengths and content
4. **Test Different Patterns**: Don't just test constant load
5. **Test from Multiple Sources**: Simulate distributed traffic

---

## Chaos Engineering

### Overview

Chaos engineering tests validate system resilience by deliberately injecting failures. Tests located in `tests/chaos/`.

### Available Tests

1. **Pod Termination**: Single pod failure and recovery
2. **Random Pod Killer**: Continuous random failures
3. **Multiple Pod Termination**: Simultaneous pod failures
4. **Service Degradation**: Reduced capacity testing
5. **Rapid Scaling**: Scaling stability validation

### Running Chaos Tests

```bash
# Run all chaos tests
python tests/chaos/chaos_engineering_tests.py \
  --namespace default \
  --app-label app.kubernetes.io/name=mlops-sentiment \
  --service-name mlops-sentiment

# Save results
python tests/chaos/chaos_engineering_tests.py \
  --namespace staging \
  --output chaos_results.json
```

### Prerequisites

- Kubernetes cluster with running KubeSentiment deployment
- At least 2 replicas
- RBAC permissions for pod management
- `kubectl` configured and accessible

### Interpreting Chaos Results

```json
{
  "summary": {
    "total_tests": 5,
    "passed": 4,
    "failed": 1,
    "success_rate": 80.0
  },
  "results": [
    {
      "test": "Pod Termination Test",
      "status": "passed"
    }
  ]
}
```

**Success Criteria**: ≥80% tests passing

### Safety Guidelines

- **NEVER** run in production without approval
- Start with development environment
- Monitor during testing
- Have rollback procedures ready
- Run during maintenance windows

See [Chaos Engineering README](../tests/chaos/README.md) for detailed documentation.

---

## Security Testing

### Security Audit

A comprehensive security audit was performed covering:

- Docker image security
- Kubernetes RBAC
- Network policies
- Secrets management
- Pod security standards
- Container security contexts

**Full Report**: [Security Audit Report](./SECURITY_AUDIT_REPORT.md)

### Automated Security Scanning

#### Trivy Vulnerability Scanning

```bash
# Scan Docker image for vulnerabilities
trivy image ghcr.io/arec1b0/mlops-sentiment:latest \
  --severity HIGH,CRITICAL

# Scan with SARIF output for GitHub
trivy image ghcr.io/arec1b0/mlops-sentiment:latest \
  --format sarif \
  --output trivy-results.sarif

# Scan filesystem
trivy fs . --severity HIGH,CRITICAL
```

#### Security Scan in CI/CD

Security scanning is automated in `.github/workflows/ci.yml`:

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ needs.build.outputs.image_full }}
    format: "sarif"
    severity: "CRITICAL,HIGH"

- name: Upload to GitHub Security
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: "trivy-results.sarif"
```

### Security Checklist

- [x] Non-root container user
- [x] Read-only root filesystem
- [x] Dropped Linux capabilities
- [x] Network policies enabled
- [x] RBAC configured
- [x] Secrets managed via Vault
- [x] TLS enabled for ingress
- [x] Resource limits defined
- [x] Pod disruption budget
- [x] Security scanning in CI/CD

### Key Security Findings

#### ✅ Implemented Correctly

- Multi-stage Docker builds
- Non-root user (UID 1000)
- Read-only root filesystem
- Network policies (ingress/egress)
- Vault integration for secrets
- Automated vulnerability scanning

#### ⚠️ Recommendations

1. **Create RBAC Role/RoleBinding** (High Priority)
   - Files created: `helm/mlops-sentiment/templates/role.yaml`, `rolebinding.yaml`
   - Implements least-privilege access

2. **Restrict Network Egress** (Medium Priority)
   - Limit HTTPS egress to specific destinations

3. **Change Default Grafana Password** (Medium Priority)
   - Use Kubernetes Secret or Vault

---

## Performance Benchmarking

### Existing Benchmarks

Located in `benchmarking/` directory:

1. **Kafka Performance Test**: `kafka_performance_test.py`
   - Tests Kafka consumer throughput
   - Target: 5,000+ TPS
   - Demonstrates 10x improvement

2. **Async Batch Performance**: `async_batch_performance_test.py`
   - Tests batch job processing
   - Validates async execution

### Running Benchmarks

```bash
# Kafka benchmark
python benchmarking/kafka_performance_test.py \
  --config configs/kafka.yaml \
  --duration 60

# Async batch benchmark
python benchmarking/async_batch_performance_test.py
```

### Benchmark Targets

| Component | Metric | Target | Current |
|-----------|--------|--------|---------|
| Kafka Consumer | Throughput | 5,000 TPS | 105,700 msg/s |
| Single Prediction | Latency | <100ms | ~50ms (optimized) |
| Batch Prediction | Throughput | 1000 req/min | Varies |
| Cold Start | Time | <1s | 50ms (160x improvement) |

---

## CI/CD Integration

### GitHub Actions Pipeline

Located in `.github/workflows/ci.yml`

#### Test Stage

```yaml
- name: Run unit tests
  run: pytest tests/ -v -m "unit or not integration"

- name: Run integration tests
  run: pytest tests/ -v -m "integration"

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

#### Security Stage

```yaml
- name: Run Trivy scanner
  uses: aquasecurity/trivy-action@master

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
```

### Local CI Simulation

```bash
# Run full CI pipeline locally
make lint          # Code quality checks
make test          # Run tests with coverage
make build         # Build Docker image

# Simulate security scan
trivy image mlops-sentiment:local --severity HIGH,CRITICAL
```

---

## Best Practices

### General Testing

1. **Test Isolation**: Each test should be independent
2. **Deterministic**: Tests should produce consistent results
3. **Fast Feedback**: Unit tests <30s, integration <2min
4. **Clear Naming**: Test names describe what they test
5. **Arrange-Act-Assert**: Structure tests clearly

### Load Testing

1. **Gradual Ramp**: Don't start with max load
2. **Monitor Resources**: Track CPU, memory, network
3. **Realistic Data**: Use production-like payloads
4. **Document Baselines**: Record performance benchmarks
5. **Automate Regularly**: Schedule recurring load tests

### Chaos Engineering

1. **Start Small**: Begin with single pod failures
2. **Monitor Continuously**: Watch metrics during tests
3. **Document Learnings**: Record failures and fixes
4. **Automate Recovery**: Build self-healing systems
5. **Regular Testing**: Run chaos tests weekly

### Security Testing

1. **Shift Left**: Test security early in development
2. **Automate Scanning**: Run on every build
3. **Track Vulnerabilities**: Monitor and remediate
4. **Least Privilege**: Minimal permissions always
5. **Regular Audits**: Quarterly security reviews

---

## Troubleshooting

### Common Test Failures

**Issue**: Tests fail locally but pass in CI
- **Solution**: Check environment variables, dependencies versions
- **Command**: `pip list` to verify package versions

**Issue**: Flaky tests (intermittent failures)
- **Solution**: Check for race conditions, timing dependencies
- **Fix**: Add proper waits, use fixtures correctly

**Issue**: Coverage below threshold
- **Solution**: Add tests for uncovered code paths
- **Command**: `pytest --cov=app --cov-report=term-missing`

### Load Test Issues

**Issue**: Low throughput
- **Solution**: Check resource limits, connection pooling
- **Monitor**: CPU, memory, network saturation

**Issue**: High latency
- **Solution**: Profile code, check database queries
- **Tool**: Use `cProfile` or application APM

**Issue**: Connection errors
- **Solution**: Increase connection limits, check timeouts
- **Check**: `ulimit -n`, connection pool settings

### Chaos Test Issues

**Issue**: Tests fail due to insufficient replicas
- **Solution**: Scale deployment to ≥3 replicas
- **Command**: `kubectl scale deployment mlops-sentiment --replicas=3`

**Issue**: RBAC permission errors
- **Solution**: Verify service account permissions
- **Command**: `kubectl auth can-i delete pods`

---

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Load Testing Best Practices](https://www.loadview-testing.com/blog/load-testing-best-practices/)
- [Chaos Engineering Principles](https://principlesofchaos.org/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Kubernetes Testing Strategies](https://kubernetes.io/docs/tasks/debug-application-cluster/)

---

## Contributing

To add new tests:

1. Create test file in appropriate directory
2. Follow naming conventions (`test_*.py`)
3. Add markers for categorization
4. Update this documentation
5. Ensure CI/CD integration

For questions or improvements, open an issue or PR.

---

**Last Updated**: 2025-10-29
**Maintained By**: KubeSentiment Team
