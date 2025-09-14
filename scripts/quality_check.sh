#!/bin/bash
set -e

echo "🧪 Running MLOps quality checks..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
OVERALL_STATUS=0

echo "📋 Running code quality checks..."

# 1. Black formatting check
echo -e "\n${YELLOW}1. Checking code formatting with Black...${NC}"
if command_exists black; then
    if black --check --diff app tests; then
        echo -e "${GREEN}✅ Code formatting: PASSED${NC}"
    else
        echo -e "${RED}❌ Code formatting: FAILED${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠️ Black not installed, skipping formatting check${NC}"
fi

# 2. Import sorting check
echo -e "\n${YELLOW}2. Checking import sorting with isort...${NC}"
if command_exists isort; then
    if isort --check-only --diff app tests; then
        echo -e "${GREEN}✅ Import sorting: PASSED${NC}"
    else
        echo -e "${RED}❌ Import sorting: FAILED${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠️ isort not installed, skipping import sorting check${NC}"
fi

# 3. Linting with flake8
echo -e "\n${YELLOW}3. Linting code with flake8...${NC}"
if command_exists flake8; then
    if flake8 app tests; then
        echo -e "${GREEN}✅ Linting: PASSED${NC}"
    else
        echo -e "${RED}❌ Linting: FAILED${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠️ flake8 not installed, skipping linting check${NC}"
fi

# 4. Type checking with mypy
echo -e "\n${YELLOW}4. Type checking with mypy...${NC}"
if command_exists mypy; then
    if mypy app --ignore-missing-imports; then
        echo -e "${GREEN}✅ Type checking: PASSED${NC}"
    else
        echo -e "${RED}❌ Type checking: FAILED${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠️ mypy not installed, skipping type checking${NC}"
fi

# 5. Security check with bandit
echo -e "\n${YELLOW}5. Security scanning with bandit...${NC}"
if command_exists bandit; then
    if bandit -r app -f json > bandit-report.json 2>/dev/null; then
        echo -e "${GREEN}✅ Security scan: PASSED${NC}"
    else
        echo -e "${YELLOW}⚠️ Security scan: WARNINGS FOUND (check bandit-report.json)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ bandit not installed, skipping security scan${NC}"
fi

# 6. Dependency vulnerability check
echo -e "\n${YELLOW}6. Checking dependencies with safety...${NC}"
if command_exists safety; then
    if safety check; then
        echo -e "${GREEN}✅ Dependency check: PASSED${NC}"
    else
        echo -e "${RED}❌ Dependency check: VULNERABILITIES FOUND${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠️ safety not installed, skipping dependency check${NC}"
fi

# 7. Run tests
echo -e "\n${YELLOW}7. Running tests with pytest...${NC}"
if command_exists pytest; then
    if pytest tests/ --cov=app --cov-report=term-missing --cov-report=html; then
        echo -e "${GREEN}✅ Tests: PASSED${NC}"
    else
        echo -e "${RED}❌ Tests: FAILED${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠️ pytest not installed, skipping tests${NC}"
fi

# 8. Docker build test
echo -e "\n${YELLOW}8. Testing Docker build...${NC}"
if command_exists docker; then
    if docker build -t mlops-sentiment:test .; then
        echo -e "${GREEN}✅ Docker build: PASSED${NC}"
        docker rmi mlops-sentiment:test 2>/dev/null || true
    else
        echo -e "${RED}❌ Docker build: FAILED${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠️ Docker not installed, skipping Docker build test${NC}"
fi

# Summary
echo -e "\n${YELLOW}📊 Quality Check Summary${NC}"
echo "========================"

if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}🎉 All quality checks passed!${NC}"
else
    echo -e "${RED}❌ Some quality checks failed. Please fix the issues above.${NC}"
fi

echo -e "\n📁 Generated reports:"
echo "   - Coverage report: htmlcov/index.html"
echo "   - Security report: bandit-report.json"

exit $OVERALL_STATUS