#
# Build Optimized Docker Image with Baked-in Models
#
# This script builds a Docker image with pre-downloaded and optimized models
# for sub-50ms cold-start performance.
#
# Usage:
#   .\scripts\infra\build-optimized-image.ps1 [OPTIONS]
#
# Options:
#   -ModelName MODEL_NAME       HuggingFace model identifier
#   -ImageTag IMAGE_TAG         Docker image tag
#   -Registry REGISTRY          Docker registry
#   -NoOnnx                     Skip ONNX optimization
#   -Push                       Push to registry after build
#

[CmdletBinding()]
param(
    [string]$ModelName = "distilbert-base-uncased-finetuned-sst-2-english",
    [string]$ImageTag = "optimized-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    [string]$Registry = "ghcr.io/yourusername",
    [switch]$NoOnnx,
    [switch]$Push
)

$ErrorActionPreference = "Stop"

# Build metadata
$BuildTime = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$Version = "1.0.0"
try {
    $Revision = git rev-parse --short HEAD 2>$null
} catch {
    $Revision = "unknown"
}

# Image name
$ImageName = "${Registry}/mlops-sentiment:${ImageTag}"

# ONNX optimization flag
$EnableOnnx = if ($NoOnnx) { "false" } else { "true" }

Write-Host "========================================"
Write-Host "Building Optimized Docker Image"
Write-Host "========================================"
Write-Host "Model: $ModelName"
Write-Host "Image: $ImageName"
Write-Host "ONNX Optimization: $EnableOnnx"
Write-Host "Build Time: $BuildTime"
Write-Host "Git Revision: $Revision"
Write-Host "========================================"
Write-Host ""

# Build the image
docker build `
    -f Dockerfile.optimized `
    --build-arg MODEL_NAME="$ModelName" `
    --build-arg ONNX_OPTIMIZATION="$EnableOnnx" `
    --build-arg BUILDTIME="$BuildTime" `
    --build-arg VERSION="$Version" `
    --build-arg REVISION="$Revision" `
    -t "$ImageName" `
    .

Write-Host ""
Write-Host "Image built successfully: $ImageName" -ForegroundColor Green

# Get image size
$ImageSize = docker images "$ImageName" --format "{{.Size}}"
Write-Host "Image size: $ImageSize" -ForegroundColor Cyan

# Test the image
Write-Host ""
Write-Host "Testing image..." -ForegroundColor Yellow
docker run --rm "$ImageName" python -c @'
import sys
sys.path.insert(0, '/app')
from app.models.persistence import ModelPersistenceManager
mgr = ModelPersistenceManager(cache_dir='/models')
info = mgr.get_cache_info()
print(f"Models cached: {info['cached_models_count']}")
print(f"Cache size: {info['total_cache_size_mb']} MB")
for model in info['cached_models']:
    print(f"  - {model}")
'@

# Push if requested
if ($Push) {
    Write-Host ""
    Write-Host "Pushing image to registry..." -ForegroundColor Cyan
    docker push "$ImageName"
    Write-Host "Image pushed: $ImageName" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================"
Write-Host "Build Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "To use this image:"
Write-Host "  docker run -p 8000:8000 $ImageName"
Write-Host ""
Write-Host "Or update your Helm values:"
Write-Host "  image:"
Write-Host "    repository: ${Registry}/mlops-sentiment"
Write-Host "    tag: $ImageTag"
Write-Host ""
Write-Host "Expected cold-start: <50ms" -ForegroundColor Green
Write-Host "========================================"
