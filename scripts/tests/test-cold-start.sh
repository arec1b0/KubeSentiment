#!/bin/bash
#
# Test Cold-Start Performance
#
# This script measures actual cold-start times by repeatedly deleting
# and recreating pods, then measuring time to first successful request.
#
# Usage:
#   ./scripts/test-cold-start.sh [OPTIONS]
#
# Options:
#   -n, --namespace NAMESPACE    Kubernetes namespace (default: mlops)
#   -i, --iterations COUNT       Number of test iterations (default: 10)
#   -w, --wait-timeout SECONDS   Max wait time per pod (default: 120)
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
NAMESPACE="mlops"
ITERATIONS=10
WAIT_TIMEOUT=120

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -n|--namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    -i|--iterations)
      ITERATIONS="$2"
      shift 2
      ;;
    -w|--wait-timeout)
      WAIT_TIMEOUT="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Cold-Start Performance Test${NC}"
echo -e "${BLUE}======================================${NC}"
echo "Namespace: ${NAMESPACE}"
echo "Iterations: ${ITERATIONS}"
echo "Wait Timeout: ${WAIT_TIMEOUT}s"
echo -e "${BLUE}======================================${NC}"
echo

# Check if deployment exists
if ! kubectl get deployment mlops-sentiment -n ${NAMESPACE} &>/dev/null; then
  echo -e "${RED}Error: Deployment 'mlops-sentiment' not found in namespace '${NAMESPACE}'${NC}"
  exit 1
fi

# Get service endpoint
SERVICE_NAME="mlops-sentiment"
echo "Getting service endpoint..."

# Try to get LoadBalancer IP
SERVICE_IP=$(kubectl get svc ${SERVICE_NAME} -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

# If LoadBalancer not available, use port-forward
if [ -z "${SERVICE_IP}" ]; then
  echo -e "${YELLOW}LoadBalancer IP not available, using port-forward${NC}"
  kubectl port-forward svc/${SERVICE_NAME} -n ${NAMESPACE} 8000:80 &>/dev/null &
  PORT_FORWARD_PID=$!
  SERVICE_URL="http://localhost:8000"
  sleep 3
else
  SERVICE_URL="http://${SERVICE_IP}"
fi

echo "Service URL: ${SERVICE_URL}"
echo

# Arrays to store results
declare -a cold_start_times
declare -a first_request_times
declare -a model_load_times

# Run iterations
for i in $(seq 1 ${ITERATIONS}); do
  echo -e "${BLUE}=== Iteration $i/${ITERATIONS} ===${NC}"

  # Delete pod to force cold-start
  echo "Deleting pod..."
  kubectl delete pod -l app=mlops-sentiment -n ${NAMESPACE} --force --grace-period=0 &>/dev/null

  # Wait for pod to be gone
  sleep 2

  # Start timer
  START_TIME=$(date +%s.%N)

  # Wait for new pod to be ready
  echo "Waiting for pod to become ready..."
  if ! kubectl wait --for=condition=ready pod -l app=mlops-sentiment -n ${NAMESPACE} --timeout=${WAIT_TIMEOUT}s &>/dev/null; then
    echo -e "${RED}Pod did not become ready within ${WAIT_TIMEOUT}s${NC}"
    continue
  fi

  POD_READY_TIME=$(date +%s.%N)
  COLD_START_TIME=$(echo "${POD_READY_TIME} - ${START_TIME}" | bc)

  # Wait a moment for warm-up to complete
  sleep 1

  # Make first request
  echo "Making first request..."
  REQUEST_START=$(date +%s.%N)

  RESPONSE=$(curl -s -X POST "${SERVICE_URL}/predict" \
    -H "Content-Type: application/json" \
    -d '{"text": "This is a test"}' \
    --max-time 10 || echo "")

  REQUEST_END=$(date +%s.%N)
  FIRST_REQUEST_TIME=$(echo "${REQUEST_END} - ${REQUEST_START}" | bc)

  if [ -z "${RESPONSE}" ]; then
    echo -e "${RED}Request failed${NC}"
    continue
  fi

  # Get model load time from logs
  POD_NAME=$(kubectl get pods -l app=mlops-sentiment -n ${NAMESPACE} -o jsonpath='{.items[0].metadata.name}')
  MODEL_LOAD_LOG=$(kubectl logs ${POD_NAME} -n ${NAMESPACE} 2>/dev/null | grep "Model loaded successfully" | tail -1 || echo "")

  if [[ ${MODEL_LOAD_LOG} =~ duration_ms=([0-9.]+) ]]; then
    MODEL_LOAD_TIME="${BASH_REMATCH[1]}"
  else
    MODEL_LOAD_TIME="N/A"
  fi

  # Store results
  cold_start_times+=("${COLD_START_TIME}")
  first_request_times+=("${FIRST_REQUEST_TIME}")
  model_load_times+=("${MODEL_LOAD_TIME}")

  # Print results
  COLD_START_MS=$(echo "${COLD_START_TIME} * 1000" | bc | cut -d. -f1)
  FIRST_REQUEST_MS=$(echo "${FIRST_REQUEST_TIME} * 1000" | bc | cut -d. -f1)

  echo -e "${GREEN}✅ Cold-start: ${COLD_START_MS}ms${NC}"
  echo -e "${GREEN}✅ Model load: ${MODEL_LOAD_TIME}ms${NC}"
  echo -e "${GREEN}✅ First request: ${FIRST_REQUEST_MS}ms${NC}"
  echo

  # Brief pause between iterations
  sleep 2
done

# Clean up port-forward if used
if [ ! -z "${PORT_FORWARD_PID}" ]; then
  kill ${PORT_FORWARD_PID} 2>/dev/null || true
fi

# Calculate statistics
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Results Summary${NC}"
echo -e "${BLUE}======================================${NC}"

# Cold-start times
if [ ${#cold_start_times[@]} -gt 0 ]; then
  COLD_START_AVG=$(printf '%s\n' "${cold_start_times[@]}" | awk '{s+=$1; n++} END {if (n>0) printf "%.0f", s/n*1000}')
  COLD_START_MIN=$(printf '%s\n' "${cold_start_times[@]}" | sort -n | head -1 | awk '{printf "%.0f", $1*1000}')
  COLD_START_MAX=$(printf '%s\n' "${cold_start_times[@]}" | sort -n | tail -1 | awk '{printf "%.0f", $1*1000}')

  echo "Cold-Start Times:"
  echo "  Average: ${COLD_START_AVG}ms"
  echo "  Min: ${COLD_START_MIN}ms"
  echo "  Max: ${COLD_START_MAX}ms"
fi

# First request times
if [ ${#first_request_times[@]} -gt 0 ]; then
  FIRST_REQ_AVG=$(printf '%s\n' "${first_request_times[@]}" | awk '{s+=$1; n++} END {if (n>0) printf "%.0f", s/n*1000}')
  FIRST_REQ_MIN=$(printf '%s\n' "${first_request_times[@]}" | sort -n | head -1 | awk '{printf "%.0f", $1*1000}')
  FIRST_REQ_MAX=$(printf '%s\n' "${first_request_times[@]}" | sort -n | tail -1 | awk '{printf "%.0f", $1*1000}')

  echo "First Request Times:"
  echo "  Average: ${FIRST_REQ_AVG}ms"
  echo "  Min: ${FIRST_REQ_MIN}ms"
  echo "  Max: ${FIRST_REQ_MAX}ms"
fi

# Model load times (filter out N/A)
VALID_MODEL_TIMES=($(printf '%s\n' "${model_load_times[@]}" | grep -v "N/A"))
if [ ${#VALID_MODEL_TIMES[@]} -gt 0 ]; then
  MODEL_LOAD_AVG=$(printf '%s\n' "${VALID_MODEL_TIMES[@]}" | awk '{s+=$1; n++} END {if (n>0) printf "%.0f", s/n}')
  MODEL_LOAD_MIN=$(printf '%s\n' "${VALID_MODEL_TIMES[@]}" | sort -n | head -1 | cut -d. -f1)
  MODEL_LOAD_MAX=$(printf '%s\n' "${VALID_MODEL_TIMES[@]}" | sort -n | tail -1 | cut -d. -f1)

  echo "Model Load Times:"
  echo "  Average: ${MODEL_LOAD_AVG}ms"
  echo "  Min: ${MODEL_LOAD_MIN}ms"
  echo "  Max: ${MODEL_LOAD_MAX}ms"
fi

# Performance evaluation
echo
echo -e "${BLUE}Performance Evaluation:${NC}"

if [ ! -z "${MODEL_LOAD_AVG}" ]; then
  if [ ${MODEL_LOAD_AVG} -le 50 ]; then
    echo -e "${GREEN}✅ EXCELLENT: Model load time ≤ 50ms (160x improvement achieved!)${NC}"
  elif [ ${MODEL_LOAD_AVG} -le 100 ]; then
    echo -e "${GREEN}✅ GOOD: Model load time ≤ 100ms (80x improvement)${NC}"
  elif [ ${MODEL_LOAD_AVG} -le 200 ]; then
    echo -e "${YELLOW}⚠️  FAIR: Model load time ≤ 200ms (40x improvement)${NC}"
  else
    echo -e "${RED}❌ NEEDS IMPROVEMENT: Model load time > 200ms${NC}"
    echo "Consider:"
    echo "  - Enabling model persistence (PersistentVolume)"
    echo "  - Using optimized Dockerfile with baked-in models"
    echo "  - Checking storage class (use SSD)"
  fi
fi

echo -e "${BLUE}======================================${NC}"

