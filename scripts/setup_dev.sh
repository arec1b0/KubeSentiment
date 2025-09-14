#!/bin/bash
set -e

echo "🚀 Setting up MLOps development environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "📍 Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies
echo "🛠️ Installing development dependencies..."
pip install pytest pytest-cov pytest-asyncio httpx black flake8 mypy isort bandit safety pre-commit

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs models data

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📄 Creating .env file..."
    cat > .env << EOF
# MLOps Sentiment Analysis Service Configuration
MLOPS_DEBUG=true
MLOPS_LOG_LEVEL=INFO
MLOPS_HOST=0.0.0.0
MLOPS_PORT=8000
MLOPS_WORKERS=1
MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
MLOPS_MODEL_CACHE_DIR=./models
MLOPS_ENABLE_METRICS=true
MLOPS_ALLOWED_ORIGINS=*
EOF
fi

# Run initial tests
echo "🧪 Running initial tests..."
python -m pytest tests/ -v

echo "✅ Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Activate virtual environment: source venv/bin/activate"
echo "   2. Start development server: python -m uvicorn app.main:app --reload"
echo "   3. Open API docs: http://localhost:8000/docs"
echo "   4. Run tests: pytest"
echo "   5. Format code: black app tests"
echo "   6. Lint code: flake8 app"