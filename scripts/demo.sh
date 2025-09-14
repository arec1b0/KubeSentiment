#!/bin/bash
set -e

echo "🚀 MLOps Sentiment Service - Complete Demonstration"
echo "==================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "\n${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
print_step "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.9+ first."
    exit 1
fi

print_success "Prerequisites check passed"

# 1. Code Quality Checks
print_step "Running code quality checks..."

if [ -f "scripts/quality_check.sh" ]; then
    chmod +x scripts/quality_check.sh
    if ./scripts/quality_check.sh; then
        print_success "Code quality checks passed"
    else
        print_warning "Some quality checks failed, continuing with demo..."
    fi
else
    print_warning "Quality check script not found, skipping..."
fi

# 2. Run Tests
print_step "Running test suite..."

if [ -f "scripts/run_tests.sh" ]; then
    chmod +x scripts/run_tests.sh
    if ./scripts/run_tests.sh; then
        print_success "Test suite passed"
    else
        print_warning "Some tests failed, continuing with demo..."
    fi
else
    print_warning "Test script not found, running basic tests..."
    python -m pytest tests/ -x --tb=short --disable-warnings || print_warning "Tests failed, continuing..."
fi

# 3. Build Docker Image
print_step "Building Docker image..."

if docker build -t mlops-sentiment:demo .; then
    print_success "Docker image built successfully"
else
    print_error "Docker build failed"
    exit 1
fi

# 4. Deploy Service
print_step "Deploying service..."

# Stop existing container if running
docker stop mlops-sentiment-demo 2>/dev/null || true
docker rm mlops-sentiment-demo 2>/dev/null || true

# Start new container
if docker run -d \
    --name mlops-sentiment-demo \
    -p 8000:8000 \
    -e MLOPS_DEBUG=false \
    -e MLOPS_LOG_LEVEL=INFO \
    --restart unless-stopped \
    mlops-sentiment:demo; then
    print_success "Service deployed successfully"
else
    print_error "Service deployment failed"
    exit 1
fi

# 5. Wait for service to start
print_step "Waiting for service to start..."

for i in {1..30}; do
    if curl -s -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        print_success "Service is ready!"
        break
    elif [ $i -eq 30 ]; then
        print_error "Service failed to start within 30 seconds"
        docker logs mlops-sentiment-demo
        exit 1
    else
        echo -n "."
        sleep 1
    fi
done

# 6. Demonstrate API Functionality
print_step "Demonstrating API functionality..."

echo -e "\n${YELLOW}🔍 Health Check:${NC}"
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool || echo "Health check failed"

echo -e "\n${YELLOW}📊 System Metrics:${NC}"
curl -s http://localhost:8000/api/v1/metrics | python3 -m json.tool || echo "Metrics check failed"

echo -e "\n${YELLOW}😊 Positive Sentiment Test:${NC}"
curl -s -X POST http://localhost:8000/api/v1/predict \
    -H "Content-Type: application/json" \
    -d '{"text": "I absolutely love this amazing MLOps service! It works perfectly."}' | \
    python3 -m json.tool || echo "Positive prediction failed"

echo -e "\n${YELLOW}😞 Negative Sentiment Test:${NC}"
curl -s -X POST http://localhost:8000/api/v1/predict \
    -H "Content-Type: application/json" \
    -d '{"text": "This service is terrible and completely broken."}' | \
    python3 -m json.tool || echo "Negative prediction failed"

# 7. Performance Testing
print_step "Running performance test..."

echo "Testing service performance with 10 concurrent requests..."
for i in {1..10}; do
    curl -s -X POST http://localhost:8000/api/v1/predict \
        -H "Content-Type: application/json" \
        -d '{"text": "Performance test message number '$i'"}' \
        > /dev/null &
done
wait
print_success "Performance test completed"

# 8. Security Testing
print_step "Testing security features..."

echo "Testing input validation..."
response=$(curl -s -X POST http://localhost:8000/api/v1/predict \
    -H "Content-Type: application/json" \
    -d '{"text": ""}' \
    -w "%{http_code}")

if [[ "$response" == *"422"* ]]; then
    print_success "Input validation working correctly (empty text rejected)"
else
    print_warning "Input validation may not be working as expected"
fi

# 9. Monitoring Demo
print_step "Monitoring and logging demonstration..."

echo "Service logs (last 20 lines):"
docker logs --tail 20 mlops-sentiment-demo

# 10. Infrastructure as Code Demo
print_step "Infrastructure as Code files..."

if [ -d "k8s" ]; then
    echo "Kubernetes manifests available:"
    ls -la k8s/
    print_success "Kubernetes deployment files ready"
else
    print_warning "Kubernetes manifests not found"
fi

if [ -f "docker-compose.yml" ]; then
    echo "Docker Compose configuration available"
    print_success "Docker Compose stack ready"
else
    print_warning "Docker Compose configuration not found"
fi

# 11. Documentation Check
print_step "Documentation completeness check..."

docs_score=0
total_docs=6

[ -f "README.md" ] && ((docs_score++)) && echo "✅ README.md"
[ -f "CONTRIBUTING.md" ] && ((docs_score++)) && echo "✅ CONTRIBUTING.md"
[ -f "MODEL_SPEC.md" ] && ((docs_score++)) && echo "✅ MODEL_SPEC.md"
[ -f ".env.template" ] && ((docs_score++)) && echo "✅ .env.template"
[ -d ".github/workflows" ] && ((docs_score++)) && echo "✅ CI/CD workflows"
[ -f "pyproject.toml" ] && ((docs_score++)) && echo "✅ Python project configuration"

echo "Documentation score: $docs_score/$total_docs"
if [ $docs_score -eq $total_docs ]; then
    print_success "All documentation is complete"
else
    print_warning "Some documentation is missing"
fi

# 12. Final Status
print_step "MLOps Service Status Summary"

echo -e "\n🌟 ${GREEN}MLOps Sentiment Analysis Service Demo Complete!${NC} 🌟"
echo "============================================================"
echo -e "📍 Service URL: ${YELLOW}http://localhost:8000${NC}"
echo -e "📚 API Documentation: ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "🏥 Health Check: ${YELLOW}http://localhost:8000/api/v1/health${NC}"
echo -e "📊 Metrics: ${YELLOW}http://localhost:8000/api/v1/metrics${NC}"

echo -e "\n📋 MLOps Features Demonstrated:"
echo "  ✅ Automated testing and quality checks"
echo "  ✅ Containerized deployment"
echo "  ✅ Health monitoring and metrics"
echo "  ✅ API functionality and validation"
echo "  ✅ Security features"
echo "  ✅ Performance testing"
echo "  ✅ Infrastructure as Code"
echo "  ✅ Comprehensive documentation"

echo -e "\n🛠️ Management Commands:"
echo "  View logs:      docker logs -f mlops-sentiment-demo"
echo "  Stop service:   docker stop mlops-sentiment-demo"
echo "  Remove service: docker rm mlops-sentiment-demo"
echo "  Shell access:   docker exec -it mlops-sentiment-demo /bin/bash"

echo -e "\n🔄 Next Steps:"
echo "  • Deploy to Kubernetes: kubectl apply -f k8s/"
echo "  • Set up monitoring: docker-compose up -d"
echo "  • Configure CI/CD: Push to repository to trigger pipeline"
echo "  • Scale horizontally: Add more replicas"

echo -e "\n${GREEN}🎉 MLOps demo completed successfully!${NC}"