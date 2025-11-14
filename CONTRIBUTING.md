# Contributing to KubeSentiment

First off, thank you for considering contributing! Your help is appreciated.

This document provides guidelines for contributing to the KubeSentiment project. Please read it to ensure a smooth contribution process.

## How Can I Contribute?

You can contribute in several ways:

- Reporting bugs
- Suggesting enhancements
- Writing documentation
- Submitting pull requests with code changes

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- `make` (optional, for using Makefile shortcuts)
- `pre-commit` (optional, but highly recommended)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/arec1b0/KubeSentiment.git
    cd KubeSentiment
    ```

2.  **Install dependencies:**
    It's recommended to use a virtual environment.
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

    Install all required dependencies for development:
    ```bash
    make install-dev
    ```
    Or manually:
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```

### Running the Application Locally

You can run the application using Docker Compose for an environment that closely mirrors production:
```bash
docker-compose up
```
Or run it directly for development with hot-reloading:
```bash
uvicorn app.main:app --reload
```

## Code Quality and Style

We use a set of tools to maintain high code quality and a consistent style.

### Tools Overview

| Tool         | Purpose                       | Configuration             |
|--------------|-------------------------------|---------------------------|
| **Black**    | Automatic code formatting     | `pyproject.toml`          |
| **isort**    | Import sorting                | `pyproject.toml`          |
| **Flake8**   | Style and syntax checking     | `.flake8`                 |
| **mypy**     | Static type checking          | `pyproject.toml`          |
| **Bandit**   | Security vulnerability scanning | `pyproject.toml`          |
| **pre-commit**| Automated pre-commit checks   | `.pre-commit-config.yaml` |

### Formatting and Linting

Before submitting code, please ensure it meets our quality standards.

- **Format your code:**
  ```bash
  make format
  ```
  This will run `black` and `isort` to format your code automatically.

- **Check for linting errors:**
  ```bash
  make lint
  ```
  This will run all checks (Black, isort, Flake8, mypy) without modifying files.

### Pre-commit Hooks (Recommended)

To automate this process, we highly recommend using pre-commit hooks. They will run the necessary checks automatically every time you make a commit.

1.  **Install pre-commit:**
    ```bash
    pip install pre-commit
    ```

2.  **Install the hooks:**
    ```bash
    pre-commit install
    ```

Now, the code quality checks will run on your changed files before you commit. You can also run them manually on all files:
```bash
pre-commit run --all-files
```

### VSCode Integration

If you use Visual Studio Code, we have a recommended setup for an optimal developer experience.

1.  **Install Recommended Extensions**: Open the Command Palette (`Ctrl+Shift+P`) and select `Extensions: Show Recommended Extensions`. This will suggest installing extensions like Python, Black, isort, and Flake8, as defined in `.vscode/extensions.json`.

2.  **Automatic Formatting**: The workspace settings in `.vscode/settings.json` are already configured to format your code with Black and sort imports with isort every time you save a file.

## Logging Guidelines

KubeSentiment uses structured logging throughout the codebase to enable better observability, debugging, and log aggregation. Please follow these guidelines when adding logging to your code.

### Using Structured Logging

#### For Application Code

Application code (files in `app/` directory) must use the structured logging system:

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Good - Structured logging with keyword arguments
logger.info("User authentication successful", user_id=user.id, method="oauth")
logger.warning("API rate limit approaching", current_requests=95, limit=100)
logger.error("Database connection failed", error=str(e), database="postgres", exc_info=True)

# Bad - F-strings and string formatting (DO NOT USE)
logger.info(f"User {user.id} authenticated")  # DON'T DO THIS
logger.error("Failed: {}".format(str(e)))  # DON'T DO THIS
```

#### For Standalone Scripts

Scripts in `scripts/`, `benchmarking/scripts/`, and `chaos/scripts/` should use standard logging with structured data:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s - %(name)s"
)
logger = logging.getLogger(__name__)

# Use the 'extra' parameter for structured data
logger.info("Migration started", extra={"environment": "prod", "secret_count": 10})
logger.error("Validation failed", extra={"key": key, "error": str(e)}, exc_info=True)
```

### Log Levels

Use appropriate log levels for different situations:

- **DEBUG**: Detailed information for debugging (e.g., variable values, function entry/exit)
- **INFO**: General information about application flow (e.g., startup, requests completed, operations succeeded)
- **WARNING**: Something unexpected but recoverable happened (e.g., deprecated API used, fallback behavior triggered)
- **ERROR**: An error occurred but the application continues (e.g., request failed, database timeout)
- **CRITICAL**: A critical error that may cause application failure (rarely used)

### Best Practices

1. **Always use keyword arguments** instead of f-strings or string formatting
2. **Include context**: Add relevant metadata like IDs, names, counts, durations
3. **Use `exc_info=True`** when logging exceptions in exception handlers
4. **Be consistent**: Use snake_case for all metadata keys
5. **Avoid sensitive data**: Never log passwords, API keys, or PII
6. **Use descriptive messages**: Message should explain "what", metadata should provide "details"

### Examples

#### Good Examples

```python
# API request logging
logger.info(
    "API request completed",
    http_method="POST",
    http_path="/predict",
    http_status=200,
    duration_ms=45.2,
    user_id=user_id
)

# Model operation
logger.info(
    "Model prediction completed",
    model_name="distilbert",
    confidence=0.95,
    prediction="POSITIVE",
    latency_ms=23.1
)

# Error with context
try:
    result = expensive_operation()
except Exception as e:
    logger.error(
        "Operation failed",
        operation="expensive_operation",
        error=str(e),
        retry_count=3,
        exc_info=True
    )
```

#### Bad Examples

```python
# DON'T: Using f-strings
logger.info(f"User {user_id} completed request in {duration}ms")

# DON'T: String concatenation
logger.error("Failed to connect to " + database + ": " + str(error))

# DON'T: Missing context
logger.info("Operation completed")  # What operation? How long? Any errors?

# DON'T: Logging sensitive data
logger.debug("User credentials", username=username, password=password)  # NEVER DO THIS
```

### Helper Functions

The logging system provides helper functions for common patterns:

```python
from app.core.logging import log_api_request, log_model_operation, log_security_event

# Log API requests
log_api_request(request, response, duration_ms)

# Log model operations
log_model_operation("prediction", model_name, duration_ms, success=True)

# Log security events
log_security_event("authentication_failed", severity="high", user_id=user_id)
```

### Configuration

The structured logging system is configured in `app/core/logging.py`. It provides:

- JSON-formatted output for production
- Automatic correlation ID injection
- Service metadata enrichment
- Integration with OpenTelemetry
- Contextual loggers with request-specific data

For more details on configuration, see `app/core/logging.py`.

## Submitting Contributions

### Git Commit Guidelines

- Write clear and meaningful commit messages.
- Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. For example:
    - `feat: Add new model backend for TensorFlow`
    - `fix: Correctly handle empty text input in prediction endpoint`
    - `docs: Update architecture diagram`
    - `style: Format code with Black`
    - `refactor: Simplify prediction service logic`
    - `test: Add unit tests for caching logic`

### Pull Request Process

1.  Ensure that all tests pass and your code is linted.
2.  Update the `README.md` or other documentation with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations and container parameters.
3.  Create a pull request to the `develop` branch.
4.  Provide a clear title and description for your pull request, explaining the "what" and "why" of your changes.
5.  If your PR addresses an open issue, link it (e.g., `Closes #123`).
6.  Your PR will be reviewed by maintainers, and you may be asked to make changes.

Thank you for your contribution!
