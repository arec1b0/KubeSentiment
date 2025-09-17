#!/bin/bash

# MLOps Sentiment Analysis Service - Kubernetes Deployment Script
# This script deploys the sentiment analysis service to Kubernetes (Minikube/Kind)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="mlops-sentiment"
IMAGE_NAME="sentiment-service"
IMAGE_TAG="latest"
ENVIRONMENT=${1:-"dev"}

echo -e "${BLUE}🚀 MLOps Sentiment Service - Kubernetes Deployment${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "Namespace: ${YELLOW}${NAMESPACE}${NC}"
echo -e "Image: ${YELLOW}${IMAGE_NAME}:${IMAGE_TAG}${NC}"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed or not in PATH${NC}"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster${NC}"
    echo -e "${YELLOW}💡 Make sure Minikube or Kind is running${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Kubernetes cluster is accessible${NC}"

# Build Docker image
echo -e "${BLUE}🔨 Building Docker image...${NC}"
if docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${RED}❌ Failed to build Docker image${NC}"
    exit 1
fi

# Load image into cluster (for Minikube/Kind)
echo -e "${BLUE}📦 Loading image into cluster...${NC}"
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    echo -e "${YELLOW}🔄 Detected Minikube - loading image...${NC}"
    minikube image load ${IMAGE_NAME}:${IMAGE_TAG}
elif command -v kind &> /dev/null; then
    echo -e "${YELLOW}🔄 Detected Kind - loading image...${NC}"
    kind load docker-image ${IMAGE_NAME}:${IMAGE_TAG}
else
    echo -e "${YELLOW}⚠️  Unknown cluster type - assuming image is available${NC}"
fi

# Apply Kubernetes manifests
echo -e "${BLUE}🎯 Deploying to Kubernetes...${NC}"

# Create namespace
echo -e "${YELLOW}📁 Creating namespace...${NC}"
kubectl apply -f k8s/namespace.yaml

# Apply ConfigMap (choose based on environment)
if [ "${ENVIRONMENT}" = "dev" ]; then
    echo -e "${YELLOW}⚙️  Applying development configuration...${NC}"
    kubectl apply -f k8s/configmap.yaml
    kubectl patch configmap sentiment-config -n ${NAMESPACE} --patch "$(kubectl get configmap sentiment-config-dev -n ${NAMESPACE} -o yaml | grep -A 20 'data:' | tail -n +2)"
else
    echo -e "${YELLOW}⚙️  Applying production configuration...${NC}"
    kubectl apply -f k8s/configmap.yaml
fi

# Apply other manifests
echo -e "${YELLOW}🚀 Deploying service components...${NC}"
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Optional: Apply Ingress (if NGINX Ingress Controller is available)
if kubectl get ingressclass nginx &> /dev/null; then
    echo -e "${YELLOW}🌐 Applying Ingress...${NC}"
    kubectl apply -f k8s/ingress.yaml
else
    echo -e "${YELLOW}⚠️  NGINX Ingress Controller not found - skipping Ingress${NC}"
fi

# Optional: Apply HPA (if metrics server is available)
if kubectl top nodes &> /dev/null; then
    echo -e "${YELLOW}📊 Applying Horizontal Pod Autoscaler...${NC}"
    kubectl apply -f k8s/hpa.yaml
else
    echo -e "${YELLOW}⚠️  Metrics server not available - skipping HPA${NC}"
fi

# Optional: Deploy Prometheus for monitoring
read -p "Do you want to deploy Prometheus for monitoring? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}📊 Deploying Prometheus...${NC}"
    kubectl apply -f k8s/prometheus-config.yaml
    echo -e "${GREEN}✅ Prometheus deployed! Access it at:${NC}"
    if command -v minikube &> /dev/null && minikube status &> /dev/null; then
        echo -e "${GREEN}📍 Prometheus URL: http://$(minikube ip):30900${NC}"
    elif command -v kind &> /dev/null; then
        echo -e "${GREEN}📍 Prometheus URL: http://localhost:30900${NC}"
    fi
fi

# Wait for deployment to be ready
echo -e "${BLUE}⏳ Waiting for deployment to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/sentiment-service -n ${NAMESPACE}

# Show deployment status
echo -e "${BLUE}📊 Deployment Status:${NC}"
kubectl get pods -n ${NAMESPACE} -o wide
echo ""
kubectl get services -n ${NAMESPACE}

# Get service URL
echo -e "${BLUE}🔗 Service Access Information:${NC}"
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    MINIKUBE_IP=$(minikube ip)
    echo -e "${GREEN}📍 Minikube Service URL: http://${MINIKUBE_IP}:30800${NC}"
    echo -e "${GREEN}📍 Health Check: http://${MINIKUBE_IP}:30800/health${NC}"
    echo -e "${GREEN}📍 API Docs: http://${MINIKUBE_IP}:30800/docs${NC}"
elif command -v kind &> /dev/null; then
    echo -e "${GREEN}📍 Kind Service URL: http://localhost:30800${NC}"
    echo -e "${GREEN}📍 Health Check: http://localhost:30800/health${NC}"
    echo -e "${GREEN}📍 API Docs: http://localhost:30800/docs${NC}"
fi

# Test the service
echo -e "${BLUE}🧪 Testing the service...${NC}"
sleep 10

if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    TEST_URL="http://$(minikube ip):30800"
elif command -v kind &> /dev/null; then
    TEST_URL="http://localhost:30800"
else
    TEST_URL="http://localhost:30800"
fi

if curl -s "${TEST_URL}/health" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Service is healthy and responding!${NC}"
else
    echo -e "${YELLOW}⚠️  Service might still be starting up...${NC}"
fi

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${BLUE}📝 Next steps:${NC}"
echo -e "  • Check pods: ${YELLOW}kubectl get pods -n ${NAMESPACE}${NC}"
echo -e "  • View logs: ${YELLOW}kubectl logs -f deployment/sentiment-service -n ${NAMESPACE}${NC}"
echo -e "  • Port forward: ${YELLOW}kubectl port-forward svc/sentiment-service 8000:8000 -n ${NAMESPACE}${NC}"
echo -e "  • Delete deployment: ${YELLOW}./scripts/cleanup.sh${NC}"
