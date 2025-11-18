# Code Quality Standards and Automation

This document outlines the code quality standards, automated checks, and quality gates enforced in the KubeSentiment project.

## Table of Contents

- [Overview](#overview)
- [Code Quality Tools](#code-quality-tools)
- [Quality Gates](#quality-gates)
- [Standards and Guidelines](#standards-and-guidelines)
- [Pre-commit Hooks](#pre-commit-hooks)
- [CI/CD Integration](#cicd-integration)
- [Local Development](#local-development)

## Overview

The project enforces code quality through automated tools and quality gates that run both locally (via pre-commit hooks) and in CI/CD pipelines. All code must pass these checks before being merged.

## Code Quality Tools

### 1. Ruff (Linting)

**Purpose**: Fast Python linter that replaces flake8 and many other tools.

**Configuration**: `pyproject.toml` → `[tool.ruff]`

**Enabled Rules**:
- `E`, `W`: pycodestyle errors and warnings
- `F`: pyflakes (unused imports, undefined names)
- `B`: flake8-bugbear (common bugs and design problems)
- `C4`: flake8-comprehensions (better comprehensions)
- `UP`: pyupgrade (modernize Python syntax)
- `ARG`: flake8-unused-arguments
- `SIM`: flake8-simplify (code simplifications)
- `TCH`: flake8-type-checking (TYPE_CHECKING imports)
- `PTH`: flake8-use-pathlib (use pathlib instead of os.path)
- `ERA`: eradicate (commented-out code detection)
- `PD`: pandas-vet (pandas best practices)
- `PL`: Pylint rules
- `TRY`: tryceratops (exception handling best practices)
- `RUF`: Ruff-specific rules

**Complexity Limit**: Maximum cyclomatic complexity of 10 (MCCabe)

**Usage**:
```bash
# Check code
ruff check app/ tests/

# Auto-fix issues
ruff check --fix app/ tests/
```

### 2. Black (Code Formatting)

**Purpose**: Uncompromising code formatter.

**Configuration**: `pyproject.toml` → `[tool.black]`

**Settings**:
- Line length: 100 characters
- Target Python version: 3.11+
- Excludes: `.eggs`, `.git`, `.venv`, `__pycache__`, etc.

**Usage**:
```bash
# Check formatting
black --check app/ tests/

# Format code
black app/ tests/
```

### 3. isort (Import Sorting)

**Purpose**: Automatically sorts and organizes imports.

**Configuration**: `pyproject.toml` → `[tool.isort]`

**Settings**:
- Profile: "black" (compatible with Black)
- Line length: 100
- Multi-line output mode: 3

**Usage**:
```bash
# Check import order
isort --check-only app/ tests/

# Sort imports
isort app/ tests/
```

### 4. mypy (Type Checking)

**Purpose**: Static type checking for Python.

**Configuration**: `pyproject.toml` → `[tool.mypy]`

**Settings**:
- Python version: 3.11
- Warn on return `Any` types
- Check untyped function definitions
- Show error codes and column numbers
- Ignore missing imports for third-party libraries

**Type Checking Overrides**:
- ML libraries (mlflow, torch, transformers): ignore missing imports
- Monitoring libraries (prometheus_client): ignore missing imports
- Infrastructure libraries (redis, kafka, onnxruntime): ignore missing imports

**Usage**:
```bash
mypy app/ --config-file=pyproject.toml
```

### 5. Radon (Code Complexity)

**Purpose**: Measure code complexity metrics.

**Configuration**: `pyproject.toml` → `[tool.radon]`

**Settings**:
- Minimum complexity grade: B
- Show complexity details
- Include assertions in complexity calculation

**Complexity Grades**:
- A: 1-5 (low complexity)
- B: 6-10 (moderate complexity)
- C: 11-20 (high complexity)
- D: 21-30 (very high complexity)
- E: 31-40 (extremely high complexity)
- F: 41+ (unacceptable complexity)

**Usage**:
```bash
# Check complexity
radon cc app/ --min B --show-complexity

# Get summary
radon cc app/ --min B --total-average
```

### 6. Bandit (Security Scanning)

**Purpose**: Security linter for Python code.

**Configuration**: `pyproject.toml` → `[tool.bandit]`

**Settings**:
- Exclude directories: `/tests`, `/venv`, `/.venv`
- Skip tests: B101 (assert_used), B601 (shell injection in tests)

**Usage**:
```bash
bandit -r app/ -c pyproject.toml
```

## Quality Gates

### Minimum Requirements

All code must meet these thresholds:

| Metric | Threshold | Tool |
|--------|-----------|------|
| Code Coverage | ≥ 80% | pytest-cov |
| Cyclomatic Complexity | ≤ 10 | Ruff (MCCabe) / Radon |
| Type Coverage | ≥ 70% | mypy |
| Security Issues | 0 Critical/High | Bandit |
| Linting Errors | 0 | Ruff |
| Formatting | 100% compliant | Black |

### Quality Gate Enforcement

Quality gates are enforced at multiple levels:

1. **Pre-commit Hooks**: Run automatically before each commit
2. **CI/CD Pipeline**: Run on every push and pull request
3. **Pull Request Checks**: Must pass before merge

### Failing Quality Gates

If quality gates fail:

1. **Pre-commit**: Fix issues locally before committing
2. **CI/CD**: Fix issues and push again
3. **PR**: All checks must pass before merge approval

## Standards and Guidelines

### Code Style

- **Line Length**: 100 characters maximum
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings (Black default)
- **Trailing Commas**: Use in multi-line collections
- **Blank Lines**: 2 blank lines between top-level definitions

### Type Hints

- Use type hints for all function parameters and return types
- Use `Optional[T]` for nullable types
- Use `Union[T1, T2]` for multiple types
- Use `List[T]`, `Dict[K, V]`, `Tuple[T, ...]` for collections
- Use `Protocol` for structural subtyping

**Example**:
```python
from typing import Optional, List, Dict
from typing_extensions import Protocol

def process_data(
    items: List[str],
    config: Optional[Dict[str, str]] = None
) -> Dict[str, int]:
    """Process items and return statistics."""
    ...
```

### Complexity Guidelines

- **Functions**: Maximum cyclomatic complexity of 10
- **Classes**: Keep methods focused and single-purpose
- **Refactoring**: If complexity exceeds threshold, refactor into smaller functions

**Complexity Reduction Strategies**:
- Extract complex conditions into named functions
- Use early returns to reduce nesting
- Break large functions into smaller, focused functions
- Use data structures to simplify logic

### Import Organization

Imports should be organized in this order:

1. Standard library imports
2. Third-party imports
3. Local application imports

**Example**:
```python
# Standard library
import os
from typing import List, Optional

# Third-party
import numpy as np
from fastapi import FastAPI

# Local
from app.core.config import settings
from app.models.base import BaseModel
```

### Documentation

- **Docstrings**: Use Google-style docstrings for all public functions, classes, and modules
- **Type Hints**: Prefer type hints over docstring type annotations
- **Comments**: Explain "why", not "what"

**Example**:
```python
def calculate_metrics(
    predictions: List[float],
    actuals: List[float]
) -> Dict[str, float]:
    """Calculate performance metrics for predictions.

    Args:
        predictions: Model predictions as a list of floats.
        actuals: Ground truth values as a list of floats.

    Returns:
        Dictionary containing accuracy, precision, recall, and F1 score.

    Raises:
        ValueError: If predictions and actuals have different lengths.
    """
    ...
```

### Error Handling

- Use specific exception types
- Include context in error messages
- Use `try/except` blocks appropriately
- Log errors with appropriate severity levels

**Example**:
```python
from app.utils.exceptions import ModelLoadError

try:
    model = load_model(model_path)
except FileNotFoundError as e:
    logger.error(f"Model file not found: {model_path}")
    raise ModelLoadError(f"Failed to load model from {model_path}") from e
```

### Security Best Practices

- Never commit secrets or credentials
- Use environment variables for configuration
- Validate and sanitize all user inputs
- Use parameterized queries for database operations
- Avoid `eval()` and `exec()` unless absolutely necessary

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit to catch issues early.

### Setup

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files
```

### Configured Hooks

1. **trailing-whitespace**: Remove trailing whitespace
2. **end-of-file-fixer**: Ensure files end with newline
3. **check-yaml**: Validate YAML files
4. **check-json**: Validate JSON files
5. **check-toml**: Validate TOML files
6. **check-added-large-files**: Prevent large file commits (>1MB)
7. **check-merge-conflict**: Detect merge conflict markers
8. **debug-statements**: Detect debug statements (pdb, ipdb)
9. **mixed-line-ending**: Ensure consistent line endings
10. **black**: Format Python code
11. **isort**: Sort imports
12. **ruff**: Lint Python code (with auto-fix)
13. **ruff-format**: Format with Ruff formatter
14. **bandit**: Security scanning
15. **mypy**: Type checking

## CI/CD Integration

### GitHub Actions Workflow

The CI/CD pipeline runs quality checks in the `test` job:

1. **Code Quality Checks**:
   - Black formatting check
   - isort import sorting check
   - Ruff linting
   - mypy type checking
   - Radon complexity check
   - Bandit security scan

2. **Test Execution**:
   - Unit tests with coverage
   - Integration tests
   - Coverage reporting to Codecov

3. **Quality Gates**:
   - All checks must pass
   - Coverage must meet threshold (≥80%)
   - No security issues (Critical/High)

### Artifacts

- **Bandit Report**: Security scan results (JSON format)
- **Coverage Report**: Test coverage metrics (XML format)

## Local Development

### Quick Commands

```bash
# Install development dependencies
make install-dev

# Run all quality checks
make lint

# Auto-fix linting issues
make lint-fix

# Format code
make format

# Check complexity
make complexity

# Run tests with coverage
make test
```

### IDE Integration

#### VS Code

Recommended extensions:
- Python (Microsoft)
- Ruff (Astral Software)
- Black Formatter (Microsoft)
- mypy Type Checker (ms-python)
- isort (Microsoft)

Settings are configured in `.vscode/settings.json`:
- Format on save enabled
- Ruff as default linter
- Black as default formatter

#### PyCharm

1. Install Ruff plugin
2. Configure Ruff as external tool
3. Enable Black formatter
4. Configure mypy as external tool

### Troubleshooting

#### Pre-commit hooks not running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
```

#### Ruff errors

```bash
# Check specific file
ruff check path/to/file.py

# Auto-fix issues
ruff check --fix path/to/file.py
```

#### mypy errors

```bash
# Check specific module
mypy app/module.py --config-file=pyproject.toml

# Show error codes
mypy app/ --show-error-codes
```

#### Complexity issues

```bash
# Check specific file complexity
radon cc app/module.py --show-complexity

# Find most complex functions
radon cc app/ --min C --show-complexity
```

## Continuous Improvement

### Regular Reviews

- Review and update quality thresholds quarterly
- Update tool versions regularly
- Add new rules based on common issues
- Remove obsolete rules

### Metrics Tracking

Track these metrics over time:
- Code coverage percentage
- Average cyclomatic complexity
- Number of linting errors per PR
- Type coverage percentage
- Security issue count

### Team Feedback

- Gather feedback on tool effectiveness
- Adjust thresholds based on team velocity
- Document common issues and solutions
- Share best practices and examples

## References

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Black Documentation](https://black.readthedocs.io/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [Radon Documentation](https://radon.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)

