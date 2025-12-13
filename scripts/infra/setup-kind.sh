#!/bin/bash

# MLOps Sentiment Analysis Service - Kind Setup Script
# This script sets up Kind (Kubernetes in Docker) for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="mlops-sentiment"
KIND_CONFIG_FILE="kind-config.yaml"

echo -e "${BLUE}🚀 MLOps Sentiment Service - Kind Setup${NC}"
echo -e "${BLUE}======================================${NC}"

# Check if Kind is installed
if ! command -v kind &> /dev/null; then
    echo -e "${RED}❌ Kind is not installed${NC}"
    echo -e "${YELLOW}💡 Installing Kind...${NC}"
    
    # Detect OS and install Kind
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
        chmod +x ./kind
        sudo mv ./kind /usr/local/bin/kind
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install kind
        else
            curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-darwin-amd64
            chmod +x ./kind
            sudo mv ./kind /usr/local/bin/kind
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo -e "${YELLOW}💡 Please install Kind manually from: https://kind.sigs.k8s.io/docs/user/quick-start/#installation${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Kind is installed: $(kind version)${NC}"

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

# Check if cluster already exists
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${YELLOW}⚠️  Kind cluster '${CLUSTER_NAME}' already exists${NC}"
    
    read -p "Do you want to delete and recreate the cluster? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🗑️  Deleting existing cluster...${NC}"
        kind delete cluster --name ${CLUSTER_NAME}
    else
        echo -e "${BLUE}ℹ️  Using existing cluster${NC}"
        kubectl config use-context kind-${CLUSTER_NAME}
        echo -e "${GREEN}✅ Kind setup completed!${NC}"
        exit 0
    fi
fi

# Create Kind configuration file
echo -e "${BLUE}📝 Creating Kind configuration...${NC}"
cat > ${KIND_CONFIG_FILE} << EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ${CLUSTER_NAME}
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
  - containerPort: 30800
    hostPort: 30800
    protocol: TCP
- role: worker
- role: worker
EOF

# Create Kind cluster
echo -e "${BLUE}🚀 Creating Kind cluster...${NC}"
kind create cluster --config ${KIND_CONFIG_FILE} --wait 5m

# Configure kubectl context
echo -e "${BLUE}⚙️  Configuring kubectl...${NC}"
kubectl config use-context kind-${CLUSTER_NAME}

# Install NGINX Ingress Controller
echo -e "${BLUE}🌐 Installing NGINX Ingress Controller...${NC}"
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait for NGINX Ingress to be ready
echo -e "${YELLOW}⏳ Waiting for NGINX Ingress Controller...${NC}"
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

# Install metrics server for HPA
echo -e "${BLUE}📊 Installing metrics server...${NC}"
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Patch metrics server for Kind (disable TLS verification)
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

# Wait for metrics server to be ready
echo -e "${YELLOW}⏳ Waiting for metrics server...${NC}"
kubectl wait --for=condition=ready pod -l k8s-app=metrics-server -n kube-system --timeout=60s

# Verify cluster
echo -e "${BLUE}🔍 Verifying cluster...${NC}"
kubectl cluster-info
kubectl get nodes -o wide

# Show cluster information
echo -e "${BLUE}📊 Cluster Information:${NC}"
kubectl get nodes
kubectl get pods -A

# Test cluster functionality
echo -e "${BLUE}🧪 Testing cluster functionality...${NC}"
kubectl create namespace test-namespace --dry-run=client -o yaml | kubectl apply -f -
kubectl delete namespace test-namespace

# Clean up configuration file
rm -f ${KIND_CONFIG_FILE}

echo -e "${GREEN}🎉 Kind setup completed successfully!${NC}"
echo -e "${BLUE}📝 Next steps:${NC}"
echo -e "  • Deploy the service: ${YELLOW}./scripts/infra/deploy-helm.sh${NC}"
echo -e "  • View cluster status: ${YELLOW}kubectl get nodes${NC}"
echo -e "  • Delete cluster: ${YELLOW}kind delete cluster --name ${CLUSTER_NAME}${NC}"

echo ""
echo -e "${BLUE}🔗 Useful Kind commands:${NC}"
echo -e "  • List clusters: ${YELLOW}kind get clusters${NC}"
echo -e "  • Load Docker image: ${YELLOW}kind load docker-image <image-name> --name ${CLUSTER_NAME}${NC}"
echo -e "  • Get kubeconfig: ${YELLOW}kind get kubeconfig --name ${CLUSTER_NAME}${NC}"
echo -e "  • Export logs: ${YELLOW}kind export logs --name ${CLUSTER_NAME}${NC}"

echo ""
echo -e "${BLUE}🌐 Service Access:${NC}"
echo -e "  • NodePort services will be available on: ${YELLOW}http://localhost:30800${NC}"
echo -e "  • Ingress services will be available on: ${YELLOW}http://localhost${NC}"
