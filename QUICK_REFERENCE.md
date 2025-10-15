# ⚡ Quick Reference - Linting and Formatting

## 🚀 Most Important Commands

```powershell
# === INSTALLATION ===
make install-dev              # Install all tools

# === FORMATTING (modifies files) ===
make format                   # Format all code
black app/ tests/             # Black only
isort app/ tests/             # isort only

# === CHECKING (no changes) ===
make lint                     # All checks at once
black --check app/            # Check formatting
flake8 app/                   # Check PEP 8 style
mypy app/                     # Check types

# === PRE-COMMIT ===
pre-commit install            # Install (once)
pre-commit run --all-files    # Check all files

# === COMBO ===
make all                      # Clean + install + lint + test + build
```

## 📁 Main Files

| File | Configures |
|------|-----------|
| `pyproject.toml` | Black, isort, pytest, mypy, bandit |
| `.flake8` | Flake8 (code style) |
| `.pre-commit-config.yaml` | Automatic checks |
| `requirements-dev.txt` | Development tools |

## 🎯 Workflow

```
1. Write code →
2. Save (Ctrl+S) → VSCode auto-formats →
3. Before commit: make lint →
4. git commit → pre-commit runs automatically →
5. ✅ Done!
```

## ⚙️ Settings

- **Line length**: 100 characters
- **Python**: 3.11+
- **Style**: PEP 8 + Black

## 📚 Documentation

- [CODE_QUALITY_SETUP.md](./CODE_QUALITY_SETUP.md) - Full instructions
- [LINTING_GUIDE.md](./LINTING_GUIDE.md) - Detailed guide
- [SETUP_LINTING.md](./SETUP_LINTING.md) - Quick start

## ✨ First Run

```powershell
# 1. Installation
make install-dev

# 2. Setup pre-commit
pre-commit install

# 3. Format existing code
make format

# 4. Check
make lint

# 5. Done! 🎉
```
