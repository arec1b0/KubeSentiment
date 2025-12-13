#!/bin/bash

# MLOps Sentiment Analysis Service - Minikube Setup Script
# This script sets up Minikube for local Kubernetes development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 MLOps Sentiment Service - Minikube Setup${NC}"
echo -e "${BLUE}===========================================${NC}"

# Check if Minikube is installed
if ! command -v minikube &> /dev/null; then
    echo -e "${RED}❌ Minikube is not installed${NC}"
    echo -e "${YELLOW}💡 Please install Minikube from: https://minikube.sigs.k8s.io/docs/start/${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Minikube is installed: $(minikube version --short)${NC}"

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed${NC}"
    echo -e "${YELLOW}💡 Please install kubectl from: https://kubernetes.io/docs/tasks/tools/${NC}"
    exit 1
fi

echo -e "${GREEN}✅ kubectl is installed: $(kubectl version --client --short)${NC}"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo -e "${YELLOW}💡 Please start Docker Desktop or Docker daemon${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"

# Check if Minikube is already running
if minikube status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Minikube is already running${NC}"
    minikube status
    
    read -p "Do you want to restart Minikube? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🔄 Stopping Minikube...${NC}"
        minikube stop
        
        echo -e "${YELLOW}🗑️  Deleting existing Minikube cluster...${NC}"
        minikube delete
    else
        echo -e "${BLUE}ℹ️  Using existing Minikube cluster${NC}"
        kubectl config use-context minikube
        echo -e "${GREEN}✅ Minikube setup completed!${NC}"
        exit 0
    fi
fi

# Start Minikube with optimized settings for ML workloads
echo -e "${BLUE}🚀 Starting Minikube...${NC}"
minikube start \
    --driver=docker \
    --cpus=4 \
    --memory=8192 \
    --disk-size=20g \
    --kubernetes-version=v1.28.3 \
    --container-runtime=docker \
    --extra-config=kubelet.housekeeping-interval=10s

echo -e "${GREEN}✅ Minikube started successfully!${NC}"

# Enable necessary addons
echo -e "${BLUE}🔧 Enabling Minikube addons...${NC}"

# Enable metrics server for HPA
echo -e "${YELLOW}📊 Enabling metrics-server...${NC}"
minikube addons enable metrics-server

# Enable NGINX Ingress Controller
echo -e "${YELLOW}🌐 Enabling ingress...${NC}"
minikube addons enable ingress

# Enable dashboard (optional)
echo -e "${YELLOW}📈 Enabling dashboard...${NC}"
minikube addons enable dashboard

# Wait for addons to be ready
echo -e "${YELLOW}⏳ Waiting for addons to be ready...${NC}"
kubectl wait --for=condition=ready pod -l k8s-app=metrics-server -n kube-system --timeout=60s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=ingress-nginx -n ingress-nginx --timeout=60s

# Configure kubectl context
echo -e "${BLUE}⚙️  Configuring kubectl...${NC}"
kubectl config use-context minikube

# Verify cluster
echo -e "${BLUE}🔍 Verifying cluster...${NC}"
kubectl cluster-info
kubectl get nodes -o wide

# Show cluster information
echo -e "${BLUE}📊 Cluster Information:${NC}"
echo -e "${GREEN}✅ Minikube IP: $(minikube ip)${NC}"
echo -e "${GREEN}✅ Dashboard URL: $(minikube dashboard --url)${NC}"

# Test cluster functionality
echo -e "${BLUE}🧪 Testing cluster functionality...${NC}"
kubectl create namespace test-namespace --dry-run=client -o yaml | kubectl apply -f -
kubectl delete namespace test-namespace

echo -e "${GREEN}🎉 Minikube setup completed successfully!${NC}"
echo -e "${BLUE}📝 Next steps:${NC}"
echo -e "  • Deploy the service: ${YELLOW}./scripts/infra/deploy-helm.sh${NC}"
echo -e "  • Access dashboard: ${YELLOW}minikube dashboard${NC}"
echo -e "  • View cluster status: ${YELLOW}minikube status${NC}"
echo -e "  • Stop Minikube: ${YELLOW}minikube stop${NC}"
echo -e "  • Delete cluster: ${YELLOW}minikube delete${NC}"

echo ""
echo -e "${BLUE}🔗 Useful Minikube commands:${NC}"
echo -e "  • Get Minikube IP: ${YELLOW}minikube ip${NC}"
echo -e "  • SSH into node: ${YELLOW}minikube ssh${NC}"
echo -e "  • Load Docker image: ${YELLOW}minikube image load <image-name>${NC}"
echo -e "  • Service URL: ${YELLOW}minikube service <service-name> --url${NC}"
