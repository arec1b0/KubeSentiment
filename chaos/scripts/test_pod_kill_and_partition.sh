#!/bin/bash
#
# Focused Chaos Test Script for Pod Kills and Network Partitions
# Tests the two critical scenarios: pod kills and network partitions
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
EXPERIMENT_TYPE="${1:-pod-kill}"  # pod-kill or network-partition
NAMESPACE="${2:-default}"
DURATION="${3:-300}"  # Default 5 minutes

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi

    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster."
        exit 1
    fi

    # Check if application is running
    if ! kubectl get deployment -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment &> /dev/null; then
        log_error "mlops-sentiment deployment not found in namespace $NAMESPACE"
        exit 1
    fi

    # Check Chaos Mesh installation
    if ! kubectl get crd podchaos.chaos-mesh.org &> /dev/null; then
        log_error "Chaos Mesh not installed. Please run: make chaos-install"
        exit 1
    fi

    # Check if at least one pod is healthy
    READY_PODS=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment \
        -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | wc -w)
    if [ "$READY_PODS" -eq 0 ]; then
        log_error "No healthy pods found for mlops-sentiment in namespace $NAMESPACE"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

get_baseline_metrics() {
    log_info "Capturing baseline metrics..."

    POD_COUNT=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment --no-headers | wc -l)
    log_info "Current pod count: $POD_COUNT"

    # Get pod names
    POD_NAMES=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment \
        -o jsonpath='{.items[*].metadata.name}')
    log_info "Pod names: $POD_NAMES"

    # Try health check if pod is available
    if [ -n "$POD_NAMES" ]; then
        FIRST_POD=$(echo $POD_NAMES | awk '{print $1}')
        if kubectl exec -n "$NAMESPACE" "$FIRST_POD" -- curl -s http://localhost:8000/health &> /dev/null; then
            log_success "Health check passed"
        else
            log_warning "Health check failed or curl not available"
        fi
    fi
}

apply_pod_kill_chaos() {
    log_info "Applying pod kill chaos experiment..."

    # Create a temporary manifest without scheduler for immediate execution
    TEMP_MANIFEST=$(mktemp)
    cat > "$TEMP_MANIFEST" <<EOF
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: sentiment-pod-kill-test
  namespace: $NAMESPACE
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - $NAMESPACE
    labelSelectors:
      app.kubernetes.io/name: mlops-sentiment
  duration: '${DURATION}s'
EOF

    kubectl apply -f "$TEMP_MANIFEST"
    rm -f "$TEMP_MANIFEST"
    log_success "Pod kill chaos experiment applied"
}

apply_network_partition_chaos() {
    log_info "Applying network partition chaos experiment..."

    # Create a temporary manifest for network partition to Redis
    TEMP_MANIFEST=$(mktemp)
    cat > "$TEMP_MANIFEST" <<EOF
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: sentiment-network-partition-test
  namespace: $NAMESPACE
spec:
  action: partition
  mode: one
  selector:
    namespaces:
      - $NAMESPACE
    labelSelectors:
      app.kubernetes.io/name: mlops-sentiment
  direction: to
  target:
    mode: all
    selector:
      namespaces:
        - $NAMESPACE
      labelSelectors:
        app: redis
  duration: '${DURATION}s'
EOF

    kubectl apply -f "$TEMP_MANIFEST"
    rm -f "$TEMP_MANIFEST"
    log_success "Network partition chaos experiment applied"
}

monitor_experiment() {
    local experiment_type=$1
    local duration=$2

    log_info "Monitoring chaos experiment for ${duration}s..."
    log_info "Press Ctrl+C to stop monitoring (experiment will continue)"

    local end_time=$(($(date +%s) + duration))
    local check_interval=10

    while [ $(date +%s) -lt $end_time ]; do
        echo ""
        log_info "=== Status at $(date '+%Y-%m-%d %H:%M:%S') ==="

        # Check pod status
        echo ""
        log_info "Pod Status:"
        kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment

        # Check chaos experiments
        echo ""
        log_info "Chaos Experiments:"
        kubectl get podchaos,networkchaos -n "$NAMESPACE" 2>/dev/null || true

        # Check HPA if exists
        echo ""
        log_info "HPA Status:"
        kubectl get hpa -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment 2>/dev/null || log_warning "HPA not found"

        sleep $check_interval
    done

    log_success "Monitoring period completed"
}

cleanup_experiments() {
    log_info "Cleaning up chaos experiments..."

    kubectl delete podchaos sentiment-pod-kill-test -n "$NAMESPACE" 2>/dev/null || true
    kubectl delete networkchaos sentiment-network-partition-test -n "$NAMESPACE" 2>/dev/null || true

    log_success "Cleanup completed"
}

verify_recovery() {
    log_info "Verifying system recovery..."

    local max_wait=300  # 5 minutes
    local waited=0
    local check_interval=10

    while [ $waited -lt $max_wait ]; do
        # Check if all pods are ready
        READY_PODS=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment \
            -o jsonpath='{.items[?(@.status.phase=="Running" && @.status.conditions[?(@.type=="Ready")].status=="True")].metadata.name}' | wc -w)
        TOTAL_PODS=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment --no-headers | wc -l)

        log_info "Ready pods: $READY_PODS/$TOTAL_PODS"

        if [ "$READY_PODS" -ge 1 ] && [ "$READY_PODS" -eq "$TOTAL_PODS" ]; then
            log_success "System recovered: $READY_PODS pods ready"

            # Try health check
            POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment \
                -o jsonpath='{.items[0].metadata.name}')
            if kubectl exec -n "$NAMESPACE" "$POD_NAME" -- curl -s http://localhost:8000/health &> /dev/null; then
                log_success "Health check passed"
                return 0
            fi
        fi

        sleep $check_interval
        waited=$((waited + check_interval))
    done

    log_warning "Recovery verification timed out after ${max_wait}s"
    return 1
}

generate_report() {
    local experiment_type=$1
    local start_time=$2
    local end_time=$3

    log_info "Generating experiment report..."

    local report_file="chaos_report_${experiment_type}_$(date +%Y%m%d_%H%M%S).txt"

    cat > "$report_file" <<EOF
========================================
Chaos Engineering Experiment Report
========================================

Experiment Type: $experiment_type
Start Time: $(date -d "@$start_time" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r "$start_time" '+%Y-%m-%d %H:%M:%S')
End Time: $(date -d "@$end_time" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r "$end_time" '+%Y-%m-%d %H:%M:%S')
Duration: $((end_time - start_time))s
Namespace: $NAMESPACE

----------------------------------------
Pod Status After Experiment:
----------------------------------------
$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment)

----------------------------------------
Events During Experiment:
----------------------------------------
$(kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -20)

----------------------------------------
HPA Status:
----------------------------------------
$(kubectl get hpa -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment 2>/dev/null || echo "HPA not found")

========================================
End of Report
========================================
EOF

    log_success "Report generated: $report_file"
}

show_usage() {
    cat <<EOF
Usage: $0 [EXPERIMENT_TYPE] [NAMESPACE] [DURATION]

EXPERIMENT_TYPE: Type of chaos experiment to run
    - pod-kill: Kill a random pod to test recovery
    - network-partition: Partition network connection to Redis

NAMESPACE: Kubernetes namespace (default: default)
DURATION: Experiment duration in seconds (default: 300)

Examples:
    $0 pod-kill default 300
    $0 network-partition mlops-sentiment-dev 600
EOF
}

# Main execution
main() {
    echo ""
    log_info "=========================================="
    log_info "Focused Chaos Test: Pod Kill & Network Partition"
    log_info "=========================================="
    echo ""

    if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
        show_usage
        exit 0
    fi

    if [ "$EXPERIMENT_TYPE" != "pod-kill" ] && [ "$EXPERIMENT_TYPE" != "network-partition" ]; then
        log_error "Invalid experiment type: $EXPERIMENT_TYPE"
        log_error "Valid types: pod-kill, network-partition"
        show_usage
        exit 1
    fi

    check_prerequisites

    START_TIME=$(date +%s)

    # Capture baseline
    get_baseline_metrics

    # Apply experiment
    if [ "$EXPERIMENT_TYPE" == "pod-kill" ]; then
        apply_pod_kill_chaos
    else
        apply_network_partition_chaos
    fi

    # Monitor experiment
    monitor_experiment "$EXPERIMENT_TYPE" "$DURATION"

    # Cleanup
    cleanup_experiments

    # Verify recovery
    verify_recovery

    END_TIME=$(date +%s)

    # Generate report
    generate_report "$EXPERIMENT_TYPE" "$START_TIME" "$END_TIME"

    echo ""
    log_success "=========================================="
    log_success "Chaos experiment completed successfully!"
    log_success "=========================================="
    echo ""
}

# Trap Ctrl+C
trap cleanup_experiments INT TERM

# Run main
main "$@"

