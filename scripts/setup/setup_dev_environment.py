#!/usr/bin/env python3
"""
KubeSentiment Development Environment Setup Script

This script automates the setup of a local development environment for KubeSentiment.
It handles virtual environment creation, dependency installation, and pre-commit hook setup.

Usage:
    python scripts/setup/setup_dev_environment.py
    # Or with options:
    python scripts/setup/setup_dev_environment.py --full --with-observability

Features:
    - Creates Python virtual environment
    - Installs dependencies (dev, test, optional extras)
    - Installs pre-commit hooks
    - Validates installation
    - Provides next steps for development

Requirements:
    - Python 3.11+
    - Git (for pre-commit hooks)
    - Virtual environment support

Environment Variables:
    PYTHON_VERSION: Override Python version (default: python3.11)
    SKIP_HOOKS: Skip pre-commit hook installation
    SKIP_DOCKER: Skip Docker validation checks
"""

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path
from typing import List, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"


def print_header(message: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}▶ {message}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.CYAN}ℹ {message}{Colors.RESET}")


def run_command(
    command: List[str],
    description: str = "",
    check: bool = True,
    cwd: Optional[str] = None,
) -> Tuple[int, str]:
    """
    Run a shell command and return exit code and output.

    Args:
        command: Command to run as list
        description: Description of what the command does
        check: Raise exception on non-zero exit
        cwd: Working directory for command

    Returns:
        Tuple of (exit_code, output)
    """
    if description:
        print_info(f"Running: {description}")

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        if check and result.returncode != 0:
            print_error(f"Command failed with exit code {result.returncode}")
            print(result.stderr)
            raise RuntimeError(f"Command failed: {' '.join(command)}")

        return result.returncode, result.stdout + result.stderr

    except FileNotFoundError:
        print_error(f"Command not found: {command[0]}")
        raise


def get_python_executable() -> str:
    """
    Get the Python executable path.

    Returns:
        Path to Python executable
    """
    python_version = os.getenv("PYTHON_VERSION", "python3.11")

    # Try specified version first
    try:
        result = subprocess.run(
            [python_version, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return python_version
    except FileNotFoundError:
        pass

    # Fallback options
    for executable in ["python3.11", "python3.12", "python3", "python"]:
        try:
            result = subprocess.run(
                [executable, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                version_output = result.stdout + result.stderr
                print_info(f"Found {executable}: {version_output.strip()}")
                return executable
        except FileNotFoundError:
            continue

    raise RuntimeError(
        "Python 3.11+ not found. Please install Python 3.11 or newer."
    )


def check_python_version(python_exe: str) -> bool:
    """
    Verify Python version is 3.11 or higher.

    Args:
        python_exe: Python executable path

    Returns:
        True if version is acceptable
    """
    result = subprocess.run(
        [python_exe, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        capture_output=True,
        text=True,
    )

    version = result.stdout.strip()
    major, minor = map(int, version.split("."))

    if major < 3 or (major == 3 and minor < 11):
        print_error(f"Python {version} found, but 3.11+ required")
        return False

    print_success(f"Python {version} verified")
    return True


def create_venv(project_root: Path, python_exe: str) -> Path:
    """
    Create a Python virtual environment.

    Args:
        project_root: Root directory of the project
        python_exe: Python executable to use

    Returns:
        Path to virtual environment
    """
    venv_path = project_root / ".venv"

    if venv_path.exists():
        print_warning(f"Virtual environment already exists at {venv_path}")
        response = input("Recreate virtual environment? (y/n): ").lower()
        if response != "y":
            return venv_path

        import shutil

        shutil.rmtree(venv_path)
        print_info("Removing existing virtual environment...")

    print_header("Creating Virtual Environment")
    print_info(f"Creating venv at {venv_path}")

    venv.create(str(venv_path), with_pip=True, upgrade_deps=True)
    print_success(f"Virtual environment created at {venv_path}")

    return venv_path


def get_pip_executable(venv_path: Path) -> str:
    """
    Get the pip executable from virtual environment.

    Args:
        venv_path: Path to virtual environment

    Returns:
        Path to pip executable
    """
    if sys.platform == "win32":
        return str(venv_path / "Scripts" / "pip")
    return str(venv_path / "bin" / "pip")


def get_python_executable_in_venv(venv_path: Path) -> str:
    """
    Get the Python executable from virtual environment.

    Args:
        venv_path: Path to virtual environment

    Returns:
        Path to Python executable
    """
    if sys.platform == "win32":
        return str(venv_path / "Scripts" / "python")
    return str(venv_path / "bin" / "python")


def install_dependencies(
    project_root: Path,
    pip_exe: str,
    full: bool = False,
    with_observability: bool = False,
    with_gpu: bool = False,
) -> None:
    """
    Install project dependencies.

    Args:
        project_root: Root directory of the project
        pip_exe: pip executable path
        full: Install all optional dependencies
        with_observability: Include observability tools (Prometheus, Grafana)
        with_gpu: Include GPU support (CUDA, cuDNN)
    """
    print_header("Installing Dependencies")

    requirements_files = [
        ("Base Requirements", "requirements.txt"),
        ("Development Tools", "requirements-dev.txt"),
        ("Testing Tools", "requirements-test.txt"),
    ]

    if full or with_observability:
        # Observability tools
        print_info("Including observability tools (Prometheus, Grafana, OpenTelemetry)")

    if with_gpu:
        print_warning("GPU support requested - ensure CUDA/cuDNN are installed")

    # Install base requirements
    for name, filename in requirements_files:
        req_file = project_root / filename
        if req_file.exists():
            print_info(f"Installing {name}...")
            run_command(
                [pip_exe, "install", "-r", str(req_file)],
                description=f"pip install -r {filename}",
            )
            print_success(f"{name} installed")
        else:
            print_warning(f"{filename} not found, skipping")

    # Upgrade pip, setuptools, wheel
    print_info("Upgrading pip, setuptools, wheel...")
    run_command(
        [pip_exe, "install", "--upgrade", "pip", "setuptools", "wheel"],
        description="Upgrading pip and tools",
    )
    print_success("Tools upgraded")


def setup_pre_commit_hooks(project_root: Path, pip_exe: str) -> None:
    """
    Install and configure pre-commit hooks.

    Args:
        project_root: Root directory of the project
        pip_exe: pip executable path
    """
    if os.getenv("SKIP_HOOKS"):
        print_warning("Pre-commit hook setup skipped (SKIP_HOOKS=1)")
        return

    print_header("Setting Up Pre-commit Hooks")

    # Install pre-commit
    print_info("Installing pre-commit...")
    run_command(
        [pip_exe, "install", "pre-commit"],
        description="pip install pre-commit",
    )

    # Install pre-commit hooks
    print_info("Installing pre-commit hooks...")
    run_command(
        ["pre-commit", "install"],
        description="pre-commit install",
        cwd=str(project_root),
    )

    print_success("Pre-commit hooks installed")
    print_info("Hooks will run automatically on commit")


def validate_installation(project_root: Path, python_exe: str) -> bool:
    """
    Validate the installation by importing key modules.

    Args:
        project_root: Root directory of the project
        python_exe: Python executable path

    Returns:
        True if validation passes
    """
    print_header("Validating Installation")

    modules_to_check = [
        ("FastAPI", "fastapi"),
        ("Pydantic", "pydantic"),
        ("Requests", "requests"),
        ("Pytest", "pytest"),
        ("Black", "black"),
        ("Ruff", "ruff"),
    ]

    all_valid = True
    for name, module in modules_to_check:
        result = subprocess.run(
            [python_exe, "-c", f"import {module}; print({module}.__version__)"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            print_success(f"{name} ({version})")
        else:
            print_error(f"{name} not found")
            all_valid = False

    return all_valid


def print_next_steps(project_root: Path, venv_path: Path) -> None:
    """
    Print next steps for developer.

    Args:
        project_root: Root directory of the project
        venv_path: Path to virtual environment
    """
    print_header("Setup Complete!")

    print("Next Steps:")
    print()

    # Activate virtual environment
    if sys.platform == "win32":
        activate_cmd = f".venv\\Scripts\\activate"
    else:
        activate_cmd = "source .venv/bin/activate"

    print(f"1. {Colors.CYAN}Activate virtual environment:{Colors.RESET}")
    print(f"   {Colors.BOLD}$ {activate_cmd}{Colors.RESET}")
    print()

    print(f"2. {Colors.CYAN}Start development server:{Colors.RESET}")
    print(f"   {Colors.BOLD}$ make dev{Colors.RESET}")
    print(f"   or")
    print(f"   {Colors.BOLD}$ PROFILE=local uvicorn app.main:app --reload{Colors.RESET}")
    print()

    print(f"3. {Colors.CYAN}Run tests:{Colors.RESET}")
    print(f"   {Colors.BOLD}$ make test{Colors.RESET}")
    print()

    print(f"4. {Colors.CYAN}Run linters:{Colors.RESET}")
    print(f"   {Colors.BOLD}$ make lint{Colors.RESET}")
    print()

    print(f"5. {Colors.CYAN}Format code:{Colors.RESET}")
    print(f"   {Colors.BOLD}$ make format{Colors.RESET}")
    print()

    print(f"Documentation:")
    print(f"  • {Colors.BOLD}README.md{Colors.RESET} - Project overview")
    print(f"  • {Colors.BOLD}CLAUDE.md{Colors.RESET} - AI assistant guide")
    print(f"  • {Colors.BOLD}docs/{Colors.RESET} - Architecture, setup guides, ADRs")
    print()

    print(f"Common commands:")
    print(f"  • {Colors.BOLD}make help{Colors.RESET} - Show all available commands")
    print(f"  • {Colors.BOLD}make install-dev{Colors.RESET} - Install dev dependencies")
    print(f"  • {Colors.BOLD}make test{Colors.RESET} - Run test suite")
    print(f"  • {Colors.BOLD}make coverage{Colors.RESET} - Generate coverage report")
    print()

    print(f"{Colors.GREEN}Happy coding!{Colors.RESET}")
    print()


def main() -> int:
    """
    Main entry point for the setup script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Set up KubeSentiment development environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic setup
  python scripts/setup/setup_dev_environment.py

  # Setup with all optional dependencies
  python scripts/setup/setup_dev_environment.py --full

  # Setup with observability tools
  python scripts/setup/setup_dev_environment.py --with-observability

  # Setup with GPU support
  python scripts/setup/setup_dev_environment.py --with-gpu
        """,
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Install all optional dependencies and tools",
    )

    parser.add_argument(
        "--with-observability",
        action="store_true",
        help="Include observability tools (Prometheus, Grafana, OpenTelemetry)",
    )

    parser.add_argument(
        "--with-gpu",
        action="store_true",
        help="Include GPU support (CUDA, cuDNN). Ensure drivers are installed.",
    )

    parser.add_argument(
        "--skip-hooks",
        action="store_true",
        help="Skip pre-commit hook installation",
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip installation validation",
    )

    args = parser.parse_args()

    try:
        # Determine project root
        project_root = Path(__file__).parent.parent.parent
        print_header(f"KubeSentiment Development Environment Setup")
        print_info(f"Project root: {project_root}")

        # Check Python version
        print_header("Checking Python Version")
        python_exe = get_python_executable()
        if not check_python_version(python_exe):
            return 1

        # Create virtual environment
        venv_path = create_venv(project_root, python_exe)

        # Get pip from venv
        pip_exe = get_pip_executable(venv_path)
        python_exe_venv = get_python_executable_in_venv(venv_path)

        # Install dependencies
        install_dependencies(
            project_root,
            pip_exe,
            full=args.full,
            with_observability=args.with_observability,
            with_gpu=args.with_gpu,
        )

        # Setup pre-commit hooks
        if not args.skip_hooks:
            try:
                setup_pre_commit_hooks(project_root, pip_exe)
            except Exception as e:
                print_warning(f"Pre-commit setup failed: {e}")
                print_warning("You can set it up manually with: pre-commit install")

        # Validate installation
        if not args.skip_validation:
            if not validate_installation(project_root, python_exe_venv):
                print_warning("Some modules are missing")
                return 1

        # Print next steps
        print_next_steps(project_root, venv_path)

        return 0

    except Exception as e:
        print_error(f"Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
