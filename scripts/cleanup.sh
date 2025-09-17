#!/bin/bash

# MLOps Sentiment Analysis Service - Kubernetes Cleanup Script
# This script removes all resources related to the sentiment analysis service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="mlops-sentiment"

echo -e "${BLUE}🧹 MLOps Sentiment Service - Cleanup${NC}"
echo -e "${BLUE}===================================${NC}"
echo -e "Namespace: ${YELLOW}${NAMESPACE}${NC}"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed or not in PATH${NC}"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Kubernetes cluster is accessible${NC}"

# Check if namespace exists
if kubectl get namespace ${NAMESPACE} &> /dev/null; then
    echo -e "${YELLOW}🔍 Found namespace ${NAMESPACE}${NC}"
    
    # Show current resources
    echo -e "${BLUE}📊 Current resources in namespace:${NC}"
    kubectl get all -n ${NAMESPACE}
    echo ""
    
    # Confirm deletion
    echo -e "${YELLOW}⚠️  This will delete all resources in namespace ${NAMESPACE}${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🗑️  Deleting resources...${NC}"
        
        # Delete specific resources first (for clean shutdown)
        echo -e "${YELLOW}🔄 Deleting HPA...${NC}"
        kubectl delete -f k8s/hpa.yaml --ignore-not-found=true
        
        echo -e "${YELLOW}🔄 Deleting Ingress...${NC}"
        kubectl delete -f k8s/ingress.yaml --ignore-not-found=true
        
        echo -e "${YELLOW}🔄 Deleting Services...${NC}"
        kubectl delete -f k8s/service.yaml --ignore-not-found=true
        
        echo -e "${YELLOW}🔄 Deleting Deployment...${NC}"
        kubectl delete -f k8s/deployment.yaml --ignore-not-found=true
        
        echo -e "${YELLOW}🔄 Deleting ConfigMaps...${NC}"
        kubectl delete -f k8s/configmap.yaml --ignore-not-found=true
        
        # Wait for pods to terminate
        echo -e "${YELLOW}⏳ Waiting for pods to terminate...${NC}"
        kubectl wait --for=delete pods --all -n ${NAMESPACE} --timeout=60s || true
        
        # Delete namespace
        echo -e "${YELLOW}🔄 Deleting namespace...${NC}"
        kubectl delete -f k8s/namespace.yaml --ignore-not-found=true
        
        echo -e "${GREEN}✅ Cleanup completed successfully!${NC}"
    else
        echo -e "${BLUE}ℹ️  Cleanup cancelled${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Namespace ${NAMESPACE} not found${NC}"
fi

# Optional: Remove Docker image
echo ""
read -p "Do you want to remove the Docker image 'sentiment-service:latest'? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🗑️  Removing Docker image...${NC}"
    docker rmi sentiment-service:latest || echo -e "${YELLOW}⚠️  Image not found locally${NC}"
fi

echo -e "${GREEN}🎉 All cleanup operations completed!${NC}"
