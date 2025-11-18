# Code Quality Quick Reference

Quick reference guide for code quality tools and commands.

## Installation

```bash
# Install all development dependencies
make install-dev
# or
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install
```

## Common Commands

### Format Code

```bash
# Format all code
make format

# Format specific directories
black app/ tests/
isort app/ tests/
```

### Check Code Quality

```bash
# Run all checks
make lint

# Run specific checks
black --check app/
isort --check-only app/
ruff check app/
mypy app/ --config-file=pyproject.toml
radon cc app/ --min B
bandit -r app/ -c pyproject.toml
```

### Auto-fix Issues

```bash
# Auto-fix all fixable issues
make lint-fix

# Auto-fix specific tools
ruff check --fix app/
black app/
isort app/
```

### Complexity Analysis

```bash
# Check complexity
make complexity

# Detailed complexity report
radon cc app/ --min B --show-complexity

# Complexity summary
radon cc app/ --min B --total-average
```

## Quality Thresholds

| Metric | Threshold | Command |
|--------|-----------|---------|
| Code Coverage | ≥ 80% | `pytest --cov=app` |
| Max Complexity | ≤ 10 | `radon cc app/ --min B` |
| Avg Complexity | ≤ 5.0 | `radon cc app/ --total-average` |
| Security Issues | 0 Critical/High | `bandit -r app/` |
| Linting Errors | 0 | `ruff check app/` |

## Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
```

## CI/CD Quality Gates

Quality gates are automatically enforced in CI/CD:

1. **Linting**: Ruff, Black, isort
2. **Type Checking**: mypy
3. **Complexity**: Radon (max complexity ≤ 10)
4. **Security**: Bandit (0 critical/high issues)
5. **Coverage**: pytest-cov (≥ 80%)

All checks must pass before merge.

## Troubleshooting

### Ruff Errors

```bash
# Check specific file
ruff check path/to/file.py

# Show detailed errors
ruff check app/ --verbose

# Auto-fix
ruff check --fix app/
```

### mypy Errors

```bash
# Check specific module
mypy app/module.py

# Show error codes
mypy app/ --show-error-codes

# Ignore specific errors (use sparingly)
# type: ignore[error-code]
```

### Complexity Issues

```bash
# Find most complex functions
radon cc app/ --min C --show-complexity

# Check specific file
radon cc app/module.py --show-complexity
```

### Pre-commit Not Running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install

# Test hooks manually
pre-commit run --all-files
```

## IDE Integration

### VS Code

1. Install recommended extensions (see `.vscode/extensions.json`)
2. Format on save is enabled automatically
3. Ruff linting runs in real-time

### PyCharm

1. Install Ruff plugin
2. Configure Ruff as external tool
3. Enable Black formatter
4. Configure mypy as external tool

## File Structure

```
.
├── .pre-commit-config.yaml  # Pre-commit hooks config
├── pyproject.toml            # Tool configurations
├── requirements-dev.txt      # Dev dependencies
├── scripts/
│   ├── check_code_quality.py  # Quality check script
│   └── quality_gate.py       # CI/CD quality gate
└── docs/
    ├── CODE_STANDARDS.md     # Full standards doc
    └── CODE_QUALITY_QUICK_REFERENCE.md  # This file
```

## Quick Fix Workflow

1. **Make changes** to code
2. **Run checks**: `make lint`
3. **Auto-fix**: `make lint-fix`
4. **Review remaining issues** manually
5. **Commit**: Pre-commit hooks run automatically

## Additional Resources

- Full documentation: `docs/CODE_STANDARDS.md`
- Tool configurations: `pyproject.toml`
- Pre-commit config: `.pre-commit-config.yaml`

