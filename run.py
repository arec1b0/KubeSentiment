#!/usr/bin/env python3
"""A development server launcher for the sentiment analysis service.

This script provides a convenient way to start the application in a local
development environment. It sets sensible default environment variables for
development, such as enabling debug mode and hot reloading, and prints helpful
information to the console upon startup.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_startup_info():
    """Prints a formatted banner with useful development information.

    This includes the project directory, Python executable path, and a list of
    available API endpoints with example `curl` commands.
    """
    print("🚀 MLOps Sentiment Analysis Service")
    print("=" * 50)
    print(f"📁 Project Directory: {project_root}")
    print(f"🐍 Python: {sys.executable}")
    print("🔧 Mode: Development (Hot reload enabled)")
    print("📊 Metrics: Enabled")
    print()
    print("📚 Available Endpoints:")
    print("  • API Docs (Swagger): http://localhost:8000/docs")
    print("  • API Docs (ReDoc):   http://localhost:8000/redoc")
    print("  • Health Check:       http://localhost:8000/health")
    print("  • Metrics:            http://localhost:8000/metrics")
    print("  • Predict:            http://localhost:8000/predict")
    print()
    print("🧪 Test Commands:")
    print('  curl -X GET "http://localhost:8000/health"')
    print('  curl -X POST "http://localhost:8000/predict" \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"text": "I love this service!"}\'')
    print("=" * 50)


if __name__ == "__main__":
    # Set development environment variables
    os.environ.setdefault("MLOPS_DEBUG", "true")
    os.environ.setdefault("MLOPS_LOG_LEVEL", "INFO")
    os.environ.setdefault("MLOPS_ENABLE_METRICS", "true")

    try:
        import uvicorn

        from app.config import get_settings

        settings = get_settings()

        print_startup_info()

        uvicorn.run(
            "app.main:app",  # Use string import for hot reload
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            reload=settings.debug,
            reload_dirs=["app"],  # Only watch app directory
        )

    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("💡 Make sure you've installed dependencies: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
        sys.exit(1)
