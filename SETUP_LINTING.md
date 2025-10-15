# 🚀 Quick Linting and Formatting Setup

## What Was Configured

Professional code quality tools are now configured in the KubeSentiment project:

### ✅ Tools

1. **Black** - automatic code formatting
2. **Flake8** - syntax and style checking (PEP 8)
3. **isort** - import sorting
4. **mypy** - type checking
5. **Bandit** - security scanning
6. **Pre-commit** - automatic pre-commit checks

### 📁 Created Files

- `pyproject.toml` - central configuration (black, isort, pytest, mypy, bandit)
- `.flake8` - flake8 configuration
- `requirements-dev.txt` - development dependencies
- `.pre-commit-config.yaml` - pre-commit hooks setup
- `.editorconfig` - universal editor settings
- `.vscode/settings.json` - VSCode settings
- `.vscode/extensions.json` - recommended VSCode extensions
- `LINTING_GUIDE.md` - detailed guide

## ⚡ Quick Start

### Step 1: Install Dependencies

```bash
# Install all development dependencies
make install-dev

# Or manually
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Step 2: Check Code

```bash
# Run all checks
make lint

# Output will contain results:
# - Black: formatting check
# - isort: import check
# - Flake8: style and syntax check
# - mypy: type check
```

### Step 3: Auto-fix

```bash
# Automatically format all code
make format

# Or
make lint-fix
```

### Step 4: Setup Pre-commit (recommended)

```bash
# Install pre-commit hooks
pre-commit install

# Now on every git commit it will automatically:
# ✓ Format code
# ✓ Check style
# ✓ Validate YAML/JSON
# ✓ Check security
```

### Step 5: Run Manually

```bash
# Check all files with pre-commit
pre-commit run --all-files

# Check only changed files
pre-commit run
```

## 🔧 Using Individual Tools

### Black (formatting)

```bash
# Check formatting
black --check app/ tests/

# Format code
black app/ tests/

# Format one file
black app/main.py
```

### Flake8 (linting)

```bash
# Check entire project
flake8 app/ tests/

# Check one file
flake8 app/main.py

# Show statistics
flake8 --statistics app/
```

### isort (imports)

```bash
# Check imports
isort --check-only app/ tests/

# Fix imports
isort app/ tests/

# Show diff without changes
isort --diff app/
```

### mypy (types)

```bash
# Check types
mypy app/

# Check with detailed output
mypy app/ --show-error-codes --pretty
```

## 📝 Configuration

### Main Parameters

- **Line length**: 100 characters (configured in black and flake8)
- **Indentation**: 4 spaces for Python
- **Encoding**: UTF-8
- **Line endings**: LF (Unix-style)

### Ignored Flake8 Rules

```ini
E203  # whitespace before ':' (conflicts with black)
W503  # line break before operator (conflicts with black)
E501  # line length (managed by black)
```

### Code Complexity

- **Maximum cyclomatic complexity**: 10
- Flake8 will warn about overly complex functions

## 💻 VSCode Integration

### Recommended Extensions

Open command palette (Ctrl+Shift+P) and select:
`Extensions: Show Recommended Extensions`

Install:

- Python (ms-python.python)
- Black Formatter (ms-python.black-formatter)
- isort (ms-python.isort)
- Flake8 (ms-python.flake8)
- Mypy Type Checker (ms-python.mypy-type-checker)

### Automatic Formatting

After installing extensions:

1. Code will automatically format on save (Ctrl+S)
2. Imports will automatically sort
3. Linting errors will highlight in real-time

## 🎯 Workflow

### Daily Work

```bash
# 1. Write code
# 2. Save file (VSCode auto-formats)
# 3. Check before commit
make lint

# 4. If there are errors - fix automatically
make format

# 5. Make commit (pre-commit runs automatically)
git add .
git commit -m "feat: add new feature"
```

### Before Pull Request

```bash
# Run all checks
make lint
make test

# Or full CI cycle locally
make all
```

## 🔍 Examples

### Black Formatting Example

**Before:**

```python
def my_function(x,y,z):
    result=x+y+z
    return result
```

**After:**

```python
def my_function(x, y, z):
    result = x + y + z
    return result
```

### isort Sorting Example

**Before:**

```python
import sys
from app.config import settings
import os
from typing import List
```

**After:**

```python
import os
import sys
from typing import List

from app.config import settings
```

### Flake8 Check Example

```python
# Error: unused variable
def calculate(x, y):
    z = 10  # F841: local variable 'z' is assigned to but never used
    return x + y

# Error: too complex function
def complex_function(a, b, c, d, e):  # C901: too complex (11)
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return True
    return False
```

## 🐛 Troubleshooting

### Conflicts Between Tools

Configuration is already set to eliminate conflicts between black and flake8.

### Pre-commit Not Working

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install

# Clean cache
pre-commit clean
```

### Too Many Errors

```bash
# Auto-fix everything possible
make format

# Then check remaining errors
make lint

# Remaining errors must be fixed manually
```

## 📚 Additional Resources

- [Detailed guide](./LINTING_GUIDE.md)
- [Black documentation](https://black.readthedocs.io/)
- [Flake8 documentation](https://flake8.pycqa.org/)
- [PEP 8 Style Guide](https://pep8.org/)

## ✨ Useful Commands

```bash
# Installation
make install-dev              # Install dev dependencies

# Checking
make lint                     # Check code (no changes)
make lint-fix                 # Auto-fix

# Formatting
make format                   # Format code

# Testing
make test                     # Run tests

# Pre-commit
pre-commit install            # Install hooks
pre-commit run --all-files    # Check all files

# Cleanup
make clean                    # Remove cache and artifacts

# Full cycle
make all                      # Clean + install + lint + test + build
```

## 🎉 Done

Now your code will:

- ✅ Automatically format
- ✅ Comply with PEP 8
- ✅ Have proper import sorting
- ✅ Be checked for security
- ✅ Validate before each commit

**Next step**: Run `make format` to format all existing code!
