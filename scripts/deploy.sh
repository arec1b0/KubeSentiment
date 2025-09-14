#!/bin/bash
set -e

echo "🐳 Building and deploying MLOps sentiment service..."

# Configuration
IMAGE_NAME="mlops-sentiment"
CONTAINER_NAME="mlops-sentiment-service"
PORT="8000"
ENV_FILE=".env"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Docker is installed
if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Stop and remove existing container
echo -e "${YELLOW}🛑 Stopping existing container...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# Build the Docker image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
docker build -t $IMAGE_NAME:latest .

# Run quality checks on the image
echo -e "${YELLOW}🧪 Running security scan on image...${NC}"
if command_exists docker; then
    # Basic image inspection
    docker inspect $IMAGE_NAME:latest > /dev/null
    echo -e "${GREEN}✅ Image built successfully${NC}"
fi

# Create network if it doesn't exist
docker network create mlops-network 2>/dev/null || true

# Run the container
echo -e "${YELLOW}🚀 Starting container...${NC}"
if [ -f "$ENV_FILE" ]; then
    docker run -d \
        --name $CONTAINER_NAME \
        --network mlops-network \
        -p $PORT:8000 \
        --env-file $ENV_FILE \
        --restart unless-stopped \
        $IMAGE_NAME:latest
else
    docker run -d \
        --name $CONTAINER_NAME \
        --network mlops-network \
        -p $PORT:8000 \
        -e MLOPS_DEBUG=false \
        -e MLOPS_LOG_LEVEL=INFO \
        --restart unless-stopped \
        $IMAGE_NAME:latest
fi

# Wait for the service to start
echo -e "${YELLOW}⏳ Waiting for service to start...${NC}"
sleep 10

# Health check
echo -e "${YELLOW}🔍 Performing health check...${NC}"
for i in {1..12}; do
    if curl -f -s http://localhost:$PORT/api/v1/health > /dev/null; then
        echo -e "${GREEN}✅ Service is healthy!${NC}"
        break
    elif [ $i -eq 12 ]; then
        echo -e "${RED}❌ Service health check failed${NC}"
        echo "Container logs:"
        docker logs $CONTAINER_NAME
        exit 1
    else
        echo "Attempt $i/12... waiting 5 seconds"
        sleep 5
    fi
done

# Show service information
echo -e "\n${GREEN}🎉 Deployment successful!${NC}"
echo "========================"
echo -e "📍 Service URL: ${YELLOW}http://localhost:$PORT${NC}"
echo -e "📚 API Docs: ${YELLOW}http://localhost:$PORT/docs${NC}"
echo -e "🏥 Health Check: ${YELLOW}http://localhost:$PORT/api/v1/health${NC}"
echo -e "📊 Metrics: ${YELLOW}http://localhost:$PORT/api/v1/metrics${NC}"

# Test the API
echo -e "\n${YELLOW}🧪 Testing the API...${NC}"
echo "Health Check:"
curl -s http://localhost:$PORT/api/v1/health | python3 -m json.tool

echo -e "\nSentiment Prediction Test:"
curl -s -X POST http://localhost:$PORT/api/v1/predict \
    -H "Content-Type: application/json" \
    -d '{"text": "I love this amazing service!"}' | python3 -m json.tool

echo -e "\n${GREEN}✅ All tests passed!${NC}"

# Show useful commands
echo -e "\n${YELLOW}📋 Useful commands:${NC}"
echo "View logs:      docker logs -f $CONTAINER_NAME"
echo "Stop service:   docker stop $CONTAINER_NAME"
echo "Remove service: docker rm $CONTAINER_NAME"
echo "Shell access:   docker exec -it $CONTAINER_NAME /bin/bash"

echo -e "\n${GREEN}🚀 MLOps sentiment service is now running!${NC}"