# MLOps Sentiment Analysis - Development Commands

.PHONY: help install test lint format clean build deploy dev docs

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install Python dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test: ## Run tests with coverage
	pytest tests/ -v --cov=app --cov-report=term-missing

lint: ## Run code quality checks
	@echo "Running black check..."
	black --check app/ tests/ scripts/ run.py
	@echo "Running isort check..."
	isort --check-only app/ tests/ scripts/ run.py
	@echo "Running flake8..."
	flake8 app/ tests/ scripts/ run.py
	@echo "Running mypy..."
	mypy app/ --ignore-missing-imports

lint-fix: ## Auto-fix linting issues
	black app/ tests/ scripts/ run.py
	isort app/ tests/ scripts/ run.py

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

all: clean install lint test build ## Run full CI pipeline locally
