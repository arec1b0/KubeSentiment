# Code Linting and Formatting Guide

## Tools Overview

The following tools are used in the project for code quality control:

### 1. **Black** - Automatic Code Formatter

- **Purpose**: Automatic Python code formatting in a consistent style
- **Configuration**: `pyproject.toml`
- **Line length**: 100 characters

### 2. **Flake8** - Linter for Style and Syntax Checking

- **Purpose**: Check code compliance with PEP 8 and find potential errors
- **Configuration**: `.flake8`
- **Plugins**:
  - `flake8-bugbear` - finds common bugs
  - `flake8-comprehensions` - improves list/dict comprehensions
  - `flake8-simplify` - suggests code simplifications

### 3. **isort** - Import Sorting

- **Purpose**: Automatic sorting and grouping of imports
- **Configuration**: `pyproject.toml`
- **Profile**: black (compatibility with black)

### 4. **mypy** - Static Type Checking

- **Purpose**: Python type checking
- **Settings**: Ignore missing imports

### 5. **Bandit** - Security Scanning

- **Purpose**: Find security issues in code
- **Exclusions**: Not applied to tests

## Installation

### Main Dependencies

```bash
pip install -r requirements.txt
```

### Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Or All Together

```bash
make install-dev
```

## Usage

### Code Checking (no changes)

```bash
# All checks at once
make lint

# Or separately
black --check app/ tests/        # Check formatting
flake8 app/ tests/               # Check style and syntax
isort --check-only app/ tests/   # Check imports
mypy app/                        # Check types
```

### Automatic Fixing

```bash
# Format all code
make format

# Or automatic lint fixing
make lint-fix

# Or separately
black app/ tests/                # Format code
isort app/ tests/                # Sort imports
```

### Pre-commit Hooks (recommended)

Pre-commit automatically checks code before each commit:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Pre-commit will automatically run on git commit
```

## Configuration

### pyproject.toml

```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100
```

### .flake8

```ini
[flake8]
max-line-length = 100
max-complexity = 10
extend-ignore = E203, W503, E501
```

## IDE Integration

### VSCode

Add to `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.flake8Args": ["--config=.flake8"],
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--config", "pyproject.toml"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

### PyCharm

1. Settings → Tools → Black
   - Enable "On code reformat"
   - Enable "On save"
2. Settings → Tools → External Tools
   - Add flake8 and isort

## Ignoring Warnings

### In Code (use sparingly!)

```python
# Ignore specific rule for one line
result = some_complex_function()  # noqa: E501

# Ignore for entire file
# flake8: noqa

# Ignore specific rule for entire file
# flake8: noqa: E501
```

### In Configuration

Edit `.flake8` for global exclusions:

```ini
per-file-ignores =
    __init__.py:F401
    tests/*:F401,F811
```

## CI/CD Integration

Linting runs automatically in CI pipeline:

```yaml
# Example for GitHub Actions
- name: Lint code
  run: make lint
```

## Troubleshooting

### Conflict Between Black and Flake8

Configuration is already set to ignore conflicting rules:

- E203 (whitespace before ':')
- W503 (line break before binary operator)
- E501 (line length, managed by Black)

### Fixing All Issues at Once

```bash
# 1. Format code
make format

# 2. Check remaining issues
make lint

# 3. Manually fix what cannot be fixed automatically
```

## Recommendations

1. **Run linting frequently**: Better to fix issues immediately
2. **Use pre-commit**: Automates checks
3. **Configure IDE**: Auto-formatting on save saves time
4. **Don't ignore warnings without reason**: They exist to improve code quality
5. **Regularly update tools**: `pip install -U -r requirements-dev.txt`

## Useful Commands

```bash
# Installation
make install-dev              # Install dev dependencies

# Checking
make lint                     # Check code
make test                     # Run tests

# Formatting
make format                   # Format code
make lint-fix                 # Auto-fix

# Pre-commit
pre-commit install           # Install hooks
pre-commit run --all-files   # Run on all files

# Full CI cycle locally
make all                     # Clean, install, lint, test, build
```

## Additional Information

- [Black documentation](https://black.readthedocs.io/)
- [Flake8 documentation](https://flake8.pycqa.org/)
- [isort documentation](https://pycqa.github.io/isort/)
- [mypy documentation](https://mypy.readthedocs.io/)
- [PEP 8 Style Guide](https://pep8.org/)
