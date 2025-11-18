# MLOps Sentiment Analysis - Development Commands

.PHONY: help install install-dev install-test install-aws install-gcp install-azure test lint format clean build deploy dev docs chaos-install chaos-test-pod-kill chaos-test-network-partition chaos-test-suite chaos-test-hpa chaos-cleanup chaos-status

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install Python dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-test.txt
	pip install -r requirements-dev.txt

install-test: ## Install testing dependencies
	pip install -r requirements.txt
	pip install -r requirements-test.txt

install-aws: ## Install AWS-specific dependencies
	pip install -r requirements.txt
	pip install -r requirements-aws.txt

install-gcp: ## Install GCP-specific dependencies
	pip install -r requirements.txt
	pip install -r requirements-gcp.txt

install-azure: ## Install Azure-specific dependencies
	pip install -r requirements.txt
	pip install -r requirements-azure.txt

test: ## Run tests with coverage
	pytest tests/ -v --cov=app --cov-report=term-missing

lint: ## Run code quality checks
	@echo "🔍 Running code quality checks..."
	@echo "📝 Checking Black formatting..."
	@black --check app/ tests/ scripts/ run.py || (echo "❌ Black check failed. Run 'make format' to fix." && exit 1)
	@echo "📦 Checking isort..."
	@isort --check-only app/ tests/ scripts/ run.py || (echo "❌ isort check failed. Run 'make format' to fix." && exit 1)
	@echo "🔎 Running Ruff linter..."
	@ruff check app/ tests/ scripts/ run.py || (echo "❌ Ruff check failed. Run 'make lint-fix' to auto-fix issues." && exit 1)
	@echo "🔬 Running mypy type checker..."
	@mypy app/ --config-file=pyproject.toml || (echo "❌ mypy check failed." && exit 1)
	@echo "📊 Checking code complexity..."
	@radon cc app/ --min B --show-complexity || (echo "❌ Complexity check failed." && exit 1)
	@echo "🔒 Running Bandit security scan..."
	@bandit -r app/ -c pyproject.toml || (echo "⚠️  Bandit found security issues." && exit 1)
	@echo "✅ All code quality checks passed!"

lint-fix: ## Auto-fix linting issues
	@echo "🔧 Auto-fixing linting issues..."
	@black app/ tests/ scripts/ run.py
	@isort app/ tests/ scripts/ run.py
	@ruff check --fix app/ tests/ scripts/ run.py
	@echo "✅ Auto-fix complete!"

complexity: ## Check code complexity metrics
	@echo "📊 Code Complexity Report:"
	@radon cc app/ --min B --show-complexity
	@echo ""
	@echo "📈 Complexity Summary:"
	@radon cc app/ --min B --total-average

format: ## Format code
	@echo "Formatting with black..."
	black app/ tests/ scripts/ run.py
	@echo "Sorting imports with isort..."
	isort app/ tests/ scripts/ run.py

clean: ## Clean up cache files and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete

build: ## Build Docker image
	docker build -t sentiment-service:latest .

dev: ## Start development server with docker-compose
	docker-compose up --build

deploy-dev: ## Deploy to development environment
	helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
		--namespace mlops-sentiment-dev \
		--create-namespace \
		--values ./helm/mlops-sentiment/values-dev.yaml \
		--set image.tag=latest

deploy-staging: ## Deploy to staging environment
	helm upgrade --install mlops-sentiment ./helm/mlops-sentiment \
		--namespace mlops-sentiment-staging \
		--create-namespace \
		--values ./helm/mlops-sentiment/values-staging.yaml \
		--set image.tag=latest

docs: ## Generate documentation (if applicable)
	@echo "Documentation available in docs/ directory"

benchmark: ## Run benchmarking suite
	cd benchmarking && ./quick-benchmark.sh

# Chaos Engineering Targets
CHAOS_NAMESPACE ?= default
CHAOS_DURATION ?= 300

chaos-install: ## Install Chaos Mesh and Litmus tools
	@echo "Installing chaos engineering tools..."
	@bash chaos/scripts/install_chaos_tools.sh

chaos-test-pod-kill: ## Run pod kill chaos experiment
	@echo "Running pod kill chaos experiment..."
	@bash chaos/scripts/test_pod_kill_and_partition.sh pod-kill $(CHAOS_NAMESPACE) $(CHAOS_DURATION)

chaos-test-network-partition: ## Run network partition chaos experiment
	@echo "Running network partition chaos experiment..."
	@bash chaos/scripts/test_pod_kill_and_partition.sh network-partition $(CHAOS_NAMESPACE) $(CHAOS_DURATION)

chaos-test-suite: ## Run full chaos engineering test suite
	@echo "Running chaos engineering test suite..."
	@python3 chaos/scripts/chaos_test_suite.py --namespace $(CHAOS_NAMESPACE) --output chaos_report.json

chaos-test-hpa: ## Run HPA-specific chaos test
	@echo "Running HPA chaos test..."
	@python3 chaos/scripts/chaos_test_suite.py \
		--namespace $(CHAOS_NAMESPACE) \
		--experiments hpa-stress-test \
		--output chaos_report_hpa.json

chaos-cleanup: ## Clean up all chaos experiments
	@echo "Cleaning up chaos experiments..."
	@kubectl delete podchaos,networkchaos,stresschaos,httpchaos,iochaos,timechaos --all -n $(CHAOS_NAMESPACE) 2>/dev/null || true
	@kubectl delete chaosengine --all -n $(CHAOS_NAMESPACE) 2>/dev/null || true
	@echo "Cleanup completed"

chaos-status: ## Check chaos tools and experiment status
	@echo "=== Chaos Mesh Status ==="
	@kubectl get pods -n chaos-mesh 2>/dev/null || echo "Chaos Mesh not installed"
	@echo ""
	@echo "=== Litmus Status ==="
	@kubectl get pods -n litmus 2>/dev/null || echo "Litmus not installed"
	@echo ""
	@echo "=== Active Chaos Experiments ==="
	@kubectl get podchaos,networkchaos,stresschaos,httpchaos,iochaos,timechaos -n $(CHAOS_NAMESPACE) 2>/dev/null || echo "No active experiments"
	@kubectl get chaosengine,chaosresult -n $(CHAOS_NAMESPACE) 2>/dev/null || echo "No active Litmus experiments"

all: clean install lint test build ## Run full CI pipeline locally
