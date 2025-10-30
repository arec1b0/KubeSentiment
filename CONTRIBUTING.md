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
