#!/bin/bash
# Deploy to Google Cloud Run

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}
SERVICE_NAME="sentiment-analysis-onnx"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying to Google Cloud Run"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"

# Build the container
echo "📦 Building container image..."
docker build -t ${IMAGE_NAME}:latest .

# Push to Container Registry
echo "⬆️  Pushing to Container Registry..."
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 60 \
    --min-instances 0 \
    --max-instances 10 \
    --concurrency 80 \
    --port 8080

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --format 'value(status.url)')

echo "✅ Deployment successful!"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Test the service:"
echo "curl -X POST ${SERVICE_URL}/predict \\"
echo '  -H "Content-Type: application/json" \\'
echo '  -d '"'"'{"text": "This is amazing!"}'"'"

