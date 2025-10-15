#!/bin/bash
# Script for formatting all project code

set -e

echo "=========================================="
echo "🎨 Auto-formatting code with Black & isort"
echo "=========================================="
echo ""

# Check for tools
command -v black >/dev/null 2>&1 || { echo "❌ Black not installed. Run: pip install -r requirements-dev.txt"; exit 1; }
command -v isort >/dev/null 2>&1 || { echo "❌ isort not installed. Run: pip install -r requirements-dev.txt"; exit 1; }

# Define directories to format
DIRS="app tests scripts run.py"

echo "📝 Formatting with Black..."
black $DIRS
echo "✅ Black formatting complete"
echo ""

echo "📦 Sorting imports with isort..."
isort $DIRS
echo "✅ Import sorting complete"
echo ""

echo "=========================================="
echo "🎉 Code formatting complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Run linting: make lint"
echo "  3. Run tests: make test"
echo "  4. Commit: git commit -am 'style: format code'"
