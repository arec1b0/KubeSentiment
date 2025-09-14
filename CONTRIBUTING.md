# Contributing to MLOps Sentiment Analysis Service

Thank you for your interest in contributing to our MLOps sentiment analysis service! This document provides guidelines and information for contributors.

## 🚀 Quick Start for Contributors

### Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MLOps
   ```

2. **Set up development environment**
   ```bash
   ./scripts/setup_dev.sh
   ```

3. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

4. **Start development server**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

## 📋 Development Workflow

### 1. Code Quality Standards

We maintain high code quality standards using automated tools:

- **Code Formatting**: Black (line length: 88)
- **Import Sorting**: isort with Black profile
- **Linting**: flake8 with MLOps-specific rules
- **Type Checking**: mypy with strict configuration
- **Security**: bandit for security vulnerability scanning
- **Dependency Security**: safety for known vulnerabilities

### 2. Pre-commit Hooks

Pre-commit hooks are automatically installed during setup and will run:
- Code formatting checks
- Import sorting
- Linting
- Type checking
- Security scanning
- YAML/JSON validation

### 3. Running Quality Checks

Before submitting a PR, run all quality checks:

```bash
./scripts/quality_check.sh
```

This script runs:
- ✅ Code formatting verification
- ✅ Import sorting check
- ✅ Linting with flake8
- ✅ Type checking with mypy
- ✅ Security scanning with bandit
- ✅ Dependency vulnerability check
- ✅ Full test suite with coverage
- ✅ Docker build verification

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── conftest.py          # Test configuration and fixtures
├── test_main.py         # Main application tests
├── test_api.py          # API endpoint tests
├── test_sentiment.py    # ML model tests
└── test_config.py       # Configuration tests
```

### Writing Tests

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test API endpoints and component interactions
- **Mock External Dependencies**: Use mocks for ML models and external services
- **Test Coverage**: Maintain >90% test coverage

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run tests matching pattern
pytest -k "test_predict"
```

## 🏗️ Architecture Guidelines

### Project Structure

```
app/
├── __init__.py          # Package initialization
├── main.py             # FastAPI app factory and lifecycle
├── api.py              # API endpoints and schemas
├── config.py           # Configuration management
└── ml/
    ├── __init__.py
    └── sentiment.py    # ML model logic
```

### Key Principles

1. **Separation of Concerns**: Keep API logic separate from ML logic
2. **Dependency Injection**: Use FastAPI's dependency injection
3. **Configuration Management**: All settings via environment variables
4. **Error Handling**: Graceful degradation and proper error responses
5. **Logging**: Structured logging for observability
6. **Security**: Non-root containers, input validation, security headers

## 📦 Adding New Features

### 1. API Endpoints

When adding new endpoints:

1. Add endpoint function to `app/api.py`
2. Define Pydantic schemas for request/response
3. Add comprehensive tests in `tests/test_api.py`
4. Update API documentation

### 2. ML Models

When adding new models:

1. Create new module in `app/ml/`
2. Follow the same interface pattern as `sentiment.py`
3. Add configuration options in `app/config.py`
4. Add comprehensive tests
5. Update Docker image if needed

### 3. Configuration

When adding new configuration:

1. Add field to `Settings` class in `app/config.py`
2. Use `MLOPS_` prefix for environment variables
3. Add validation and documentation
4. Update example `.env` file

## 🔍 Code Review Process

### Pull Request Requirements

- [ ] All quality checks pass (`./scripts/quality_check.sh`)
- [ ] Test coverage maintained (>90%)
- [ ] Documentation updated
- [ ] API changes documented
- [ ] Breaking changes noted
- [ ] Security considerations addressed

### Review Checklist

**Code Quality**
- [ ] Code follows project style guidelines
- [ ] Functions and classes have proper docstrings
- [ ] Complex logic is commented
- [ ] No hardcoded values or magic numbers

**Testing**
- [ ] New features have comprehensive tests
- [ ] Edge cases are covered
- [ ] Mocks are used appropriately
- [ ] Tests are readable and maintainable

**Security**
- [ ] Input validation is proper
- [ ] No sensitive data in logs
- [ ] Dependencies are secure
- [ ] Security best practices followed

**Performance**
- [ ] No obvious performance issues
- [ ] Resource usage is reasonable
- [ ] Async/await used properly
- [ ] Database queries optimized (if applicable)

## 🚀 Deployment Guidelines

### Local Development

```bash
# Start with Docker Compose (includes monitoring)
docker-compose up -d

# Or standalone container
./scripts/deploy.sh
```

### Production Deployment

1. **Environment Configuration**
   - Set `MLOPS_DEBUG=false`
   - Configure proper `MLOPS_ALLOWED_ORIGINS`
   - Set up monitoring and logging
   - Use secrets management

2. **Kubernetes Deployment**
   ```bash
   kubectl apply -f k8s/
   ```

3. **Health Checks**
   - Configure liveness/readiness probes
   - Set up monitoring alerts
   - Test disaster recovery

## 📊 Monitoring and Observability

### Metrics

The service exposes metrics at `/api/v1/metrics`:
- System metrics (CPU, memory, GPU)
- Model status and performance
- Request/response metrics

### Logging

- Structured JSON logging
- Correlation IDs for tracing
- Different log levels for environments
- Security event logging

### Alerts

Key alerts to monitor:
- Service availability
- High error rates
- High latency
- Resource utilization
- Model degradation

## 🔒 Security Guidelines

### Development Security

- Never commit secrets or API keys
- Use environment variables for configuration
- Validate all inputs
- Follow OWASP guidelines
- Regular dependency updates

### Production Security

- Use HTTPS/TLS
- Implement rate limiting
- Set up API authentication
- Monitor for security events
- Regular security scans

## 📚 Documentation Standards

### Code Documentation

- Clear docstrings for all public functions
- Type hints for function parameters and returns
- Examples in docstrings where helpful
- Comments for complex business logic

### API Documentation

- OpenAPI/Swagger specifications
- Request/response examples
- Error code documentation
- Rate limiting information

## 🤝 Getting Help

### Resources

- **API Documentation**: `/docs` endpoint
- **Project Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

### Communication

- Be respectful and inclusive
- Provide clear problem descriptions
- Include relevant code samples
- Follow up on discussions

## 📋 Release Process

### Version Management

- Semantic versioning (MAJOR.MINOR.PATCH)
- Tag releases in Git
- Maintain CHANGELOG.md
- Document breaking changes

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version numbers updated
- [ ] Security scan clean
- [ ] Performance benchmarks meet SLA
- [ ] Deployment tested

Thank you for contributing to making this MLOps service better! 🚀