#!/usr/bin/env python3
"""
Development environment setup script for MLOps project.

This script helps set up the development environment, install dependencies,
and verify the installation.
"""

import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, description, check=True):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command, shell=True, check=check, capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return result
        else:
            print(f"❌ {description} failed")
            print(f"Error: {result.stderr}")
            return result
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with error: {e}")
        return None


def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(
            f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible"
        )
        return True
    else:
        print(
            f"❌ Python {version.major}.{version.minor}.{version.micro} is not compatible. Python 3.8+ required."
        )
        return False


def check_virtual_environment():
    """Check if we're in a virtual environment."""
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print("✅ Virtual environment detected")
        return True
    else:
        print("⚠️  Not in a virtual environment")
        return False


def install_dependencies():
    """Install Python dependencies."""
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        command = f"{sys.executable} -m pip install -r requirements.txt"
        return run_command(command, "Installing Python dependencies")
    else:
        print("❌ requirements.txt not found")
        return False


def verify_installation():
    """Verify that key packages are installed."""
    packages = ["fastapi", "uvicorn", "transformers", "torch", "pydantic"]

    print("🔍 Verifying package installation...")
    all_good = True

    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} not found")
            all_good = False

    return all_good


def create_env_file():
    """Create .env file if it doesn't exist."""
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Creating .env file...")
        env_content = """# MLOps Sentiment Analysis Service Configuration
MLOPS_DEBUG=true
MLOPS_LOG_LEVEL=INFO
MLOPS_HOST=0.0.0.0
MLOPS_PORT=8000
MLOPS_ENABLE_METRICS=true
"""
        env_file.write_text(env_content)
        print("✅ .env file created")
    else:
        print("✅ .env file already exists")


def main():
    """Main setup function."""
    print("🚀 MLOps Development Environment Setup")
    print("=" * 50)

    # Check system info
    print(f"🖥️  Platform: {platform.system()} {platform.release()}")
    print(f"🐍 Python: {sys.executable}")

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Check virtual environment
    check_virtual_environment()

    # Create .env file
    create_env_file()

    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)

    # Verify installation
    if not verify_installation():
        print("❌ Some packages are missing. Please check the installation.")
        sys.exit(1)

    print("\n🎉 Development environment setup complete!")
    print("\n📋 Next steps:")
    print("1. Start the development server: python run.py")
    print("2. Open your browser to: http://localhost:8000/docs")
    print("3. Test the API endpoints")
    print("\n🔧 Development commands:")
    print("  • Start server:     python run.py")
    print("  • Run tests:        python -m pytest (when tests are added)")
    print("  • Check code:       python -m flake8 app/")
    print("  • Format code:      python -m black app/")


if __name__ == "__main__":
    main()
