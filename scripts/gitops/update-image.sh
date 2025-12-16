#!/bin/bash

# GitOps Helper Script - Update Image Tags
# This script updates image tags in GitOps environment values
# Can be used locally or in CI/CD pipelines

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Usage
usage() {
    cat <<EOF
Usage: $0 -e ENVIRONMENT -t TAG [-r REPOSITORY] [-c] [-p]

Update GitOps environment values with new image tag

Options:
    -e  Environment (development, staging, production)
    -t  Image tag to set
    -r  Image repository (optional, default: use existing)
    -c  Commit changes
    -p  Push changes
    -h  Show this help

Examples:
    # Update staging to use tag 'v1.2.3'
    $0 -e staging -t v1.2.3

    # Update and commit
    $0 -e production -t v1.2.3 -c

    # Update, commit, and push
    $0 -e production -t v1.2.3 -c -p

    # Update with custom repository
    $0 -e development -t latest -r ghcr.io/myorg/myapp -c -p
EOF
    exit 1
}

# Parse arguments
ENVIRONMENT=""
TAG=""
REPOSITORY=""
COMMIT=false
PUSH=false

while getopts "e:t:r:cph" opt; do
    case $opt in
        e) ENVIRONMENT="$OPTARG" ;;
        t) TAG="$OPTARG" ;;
        r) REPOSITORY="$OPTARG" ;;
        c) COMMIT=true ;;
        p) PUSH=true ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Validate required arguments
if [ -z "$ENVIRONMENT" ] || [ -z "$TAG" ]; then
    log_error "Environment and tag are required"
    usage
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    log_error "Must be one of: development, staging, production"
    exit 1
fi

# File paths
GITOPS_DIR="infrastructure/gitops"
VALUES_FILE="$GITOPS_DIR/environments/$ENVIRONMENT/values.yaml"
APP_FILE="$GITOPS_DIR/applications/$ENVIRONMENT/mlops-sentiment.yaml"

# Check if yq is installed
if ! command -v yq &> /dev/null; then
    log_error "yq is not installed. Please install it:"
    echo "  brew install yq (macOS)"
    echo "  snap install yq (Linux)"
    echo "  choco install yq (Windows)"
    exit 1
fi

# Check if files exist
if [ ! -f "$VALUES_FILE" ]; then
    log_error "Values file not found: $VALUES_FILE"
    exit 1
fi

if [ ! -f "$APP_FILE" ]; then
    log_error "Application file not found: $APP_FILE"
    exit 1
fi

log_info "Updating $ENVIRONMENT environment to tag: $TAG"

# Update values.yaml
log_info "Updating $VALUES_FILE"
yq eval ".image.tag = \"$TAG\"" -i "$VALUES_FILE"

if [ -n "$REPOSITORY" ]; then
    log_info "Updating repository to: $REPOSITORY"
    yq eval ".image.repository = \"$REPOSITORY\"" -i "$VALUES_FILE"
fi

# Update Application manifest
log_info "Updating $APP_FILE"
yq eval "(.spec.source.helm.parameters[] | select(.name == \"image.tag\")).value = \"$TAG\"" \
    -i "$APP_FILE"

if [ -n "$REPOSITORY" ]; then
    yq eval "(.spec.source.helm.parameters[] | select(.name == \"image.repository\")).value = \"$REPOSITORY\"" \
        -i "$APP_FILE"
fi

log_success "Files updated successfully"

# Show changes
echo ""
log_info "Changes:"
git diff --no-pager "$VALUES_FILE" "$APP_FILE" || true
echo ""

# Commit if requested
if [ "$COMMIT" = true ]; then
    log_info "Committing changes..."

    git add "$VALUES_FILE" "$APP_FILE"

    COMMIT_MSG="chore(gitops): update $ENVIRONMENT image to $TAG"
    if [ -n "$REPOSITORY" ]; then
        COMMIT_MSG="$COMMIT_MSG from $REPOSITORY"
    fi
    COMMIT_MSG="$COMMIT_MSG [skip ci]"

    git commit -m "$COMMIT_MSG"
    log_success "Changes committed"

    # Push if requested
    if [ "$PUSH" = true ]; then
        log_info "Pushing changes..."
        BRANCH=$(git rev-parse --abbrev-ref HEAD)
        git push origin "$BRANCH"
        log_success "Changes pushed to $BRANCH"
    fi
fi

echo ""
log_success "✅ Update complete!"
echo ""
log_info "Next steps:"
if [ "$COMMIT" = false ]; then
    echo "  1. Review changes: git diff"
    echo "  2. Commit: git add . && git commit -m 'chore(gitops): update $ENVIRONMENT'"
    echo "  3. Push: git push"
fi

if [ "$ENVIRONMENT" = "production" ]; then
    echo "  • Manually sync in ArgoCD:"
    echo "    argocd app sync mlops-sentiment-production"
else
    echo "  • ArgoCD will automatically sync the changes"
    echo "  • Monitor: argocd app get mlops-sentiment-$ENVIRONMENT"
fi
echo ""
