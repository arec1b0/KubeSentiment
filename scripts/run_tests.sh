#!/bin/bash
set -e

echo "🧪 Running test suite with better isolation..."

# Set test environment variables
export MLOPS_DEBUG=true
export MLOPS_MODEL_NAME=mock-model
export MLOPS_LOG_LEVEL=ERROR
export MLOPS_ENABLE_METRICS=false

# Clear any Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Run tests with proper settings
python -m pytest tests/ -v --tb=short -x --disable-warnings

echo "✅ Test suite completed!"