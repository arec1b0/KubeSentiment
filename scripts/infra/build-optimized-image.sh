#!/bin/bash
#
# Build Optimized Docker Image with Baked-in Models
#
# This script builds a Docker image with pre-downloaded and optimized models
# for sub-50ms cold-start performance.
#
# Usage:
#   ./scripts/build-optimized-image.sh [OPTIONS]
#
# Options:
#   -m, --model MODEL_NAME       HuggingFace model identifier
#   -t, --tag IMAGE_TAG          Docker image tag
#   -r, --registry REGISTRY      Docker registry
#   --no-onnx                    Skip ONNX optimization
#   --push                       Push to registry after build
#

set -e

# Default values
MODEL_NAME="distilbert-base-uncased-finetuned-sst-2-english"
IMAGE_TAG="optimized-$(date +%Y%m%d-%H%M%S)"
REGISTRY="ghcr.io/yourusername"
ENABLE_ONNX="true"
PUSH_IMAGE="false"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -m|--model)
      MODEL_NAME="$2"
      shift 2
      ;;
    -t|--tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    -r|--registry)
      REGISTRY="$2"
      shift 2
      ;;
    --no-onnx)
      ENABLE_ONNX="false"
      shift
      ;;
    --push)
      PUSH_IMAGE="true"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Build metadata
BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VERSION="1.0.0"
REVISION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Image name
IMAGE_NAME="${REGISTRY}/mlops-sentiment:${IMAGE_TAG}"

echo "========================================"
echo "Building Optimized Docker Image"
echo "========================================"
echo "Model: ${MODEL_NAME}"
echo "Image: ${IMAGE_NAME}"
echo "ONNX Optimization: ${ENABLE_ONNX}"
echo "Build Time: ${BUILD_TIME}"
echo "Git Revision: ${REVISION}"
echo "========================================"
echo

# Build the image
docker build \
  -f Dockerfile.optimized \
  --build-arg MODEL_NAME="${MODEL_NAME}" \
  --build-arg ONNX_OPTIMIZATION="${ENABLE_ONNX}" \
  --build-arg BUILDTIME="${BUILD_TIME}" \
  --build-arg VERSION="${VERSION}" \
  --build-arg REVISION="${REVISION}" \
  -t "${IMAGE_NAME}" \
  .

echo
echo "✅ Image built successfully: ${IMAGE_NAME}"

# Get image size
IMAGE_SIZE=$(docker images "${IMAGE_NAME}" --format "{{.Size}}")
echo "📊 Image size: ${IMAGE_SIZE}"

# Test the image
echo
echo "🧪 Testing image..."
docker run --rm "${IMAGE_NAME}" python -c "
import sys
sys.path.insert(0, '/app')
from app.models.persistence import ModelPersistenceManager
mgr = ModelPersistenceManager(cache_dir='/models')
info = mgr.get_cache_info()
print(f'✅ Models cached: {info[\"cached_models_count\"]}')
print(f'📦 Cache size: {info[\"total_cache_size_mb\"]} MB')
for model in info['cached_models']:
    print(f'  - {model}')
"

# Push if requested
if [ "${PUSH_IMAGE}" = "true" ]; then
  echo
  echo "🚀 Pushing image to registry..."
  docker push "${IMAGE_NAME}"
  echo "✅ Image pushed: ${IMAGE_NAME}"
fi

echo
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo
echo "To use this image:"
echo "  docker run -p 8000:8000 ${IMAGE_NAME}"
echo
echo "Or update your Helm values:"
echo "  image:"
echo "    repository: ${REGISTRY}/mlops-sentiment"
echo "    tag: ${IMAGE_TAG}"
echo
echo "Expected cold-start: <50ms 🚀"
echo "========================================"

