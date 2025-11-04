#!/bin/bash
#
# Chaos Experiment Orchestration Script
# Runs chaos experiments with monitoring and reporting
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${CHAOS_NAMESPACE:-default}"
EXPERIMENT_TYPE="${1:-pod-kill}"
DURATION="${2:-300}"  # Default 5 minutes
MONITORING="${3:-true}"

# Experiment mappings
declare -A CHAOS_MESH_EXPERIMENTS=(
    ["pod-kill"]="chaos/chaos-mesh/01-pod-kill.yaml"
    ["network"]="chaos/chaos-mesh/02-network-chaos.yaml"
    ["stress"]="chaos/chaos-mesh/03-stress-chaos.yaml"
    ["http"]="chaos/chaos-mesh/04-http-chaos.yaml"
    ["io"]="chaos/chaos-mesh/05-io-chaos.yaml"
    ["time"]="chaos/chaos-mesh/06-time-chaos.yaml"
    ["workflow"]="chaos/chaos-mesh/07-workflow.yaml"
)

declare -A LITMUS_EXPERIMENTS=(
    ["pod-delete"]="chaos/litmus/01-pod-delete.yaml"
    ["container-kill"]="chaos/litmus/02-container-kill.yaml"
    ["network-latency"]="chaos/litmus/03-pod-network-latency.yaml"
    ["network-loss"]="chaos/litmus/04-pod-network-loss.yaml"
    ["cpu-hog"]="chaos/litmus/05-pod-cpu-hog.yaml"
    ["memory-hog"]="chaos/litmus/06-pod-memory-hog.yaml"
    ["disk-fill"]="chaos/litmus/07-disk-fill.yaml"
    ["node-drain"]="chaos/litmus/08-node-drain.yaml"
)

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

    # Check if application is running (using label selector for flexibility)
    if ! kubectl get deployment -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment &> /dev/null; then
        log_error "mlops-sentiment deployment not found in namespace $NAMESPACE"
        log_error "Please ensure the service is deployed before running chaos experiments"
        exit 1
    fi

    # Check if at least one pod is healthy
    READY_PODS=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment \
        -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' 2>/dev/null | wc -w)
    if [ "$READY_PODS" -eq 0 ]; then
        log_error "No healthy pods found for mlops-sentiment in namespace $NAMESPACE"
        exit 1
    fi
    log_info "Found $READY_PODS healthy pod(s)"

    log_success "Prerequisites check passed"
}

check_chaos_mesh() {
    if kubectl get crd podchaos.chaos-mesh.org &> /dev/null; then
        return 0
    fi
    return 1
}

check_litmus() {
    if kubectl get crd chaosengines.litmuschaos.io &> /dev/null; then
        return 0
    fi
    return 1
}

get_baseline_metrics() {
    log_info "Capturing baseline metrics..."

    # Get current pod count
    POD_COUNT=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment --no-headers | wc -l)
    log_info "Current pod count: $POD_COUNT"

    # Get health status
    if kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment -o jsonpath='{.items[0].metadata.name}' &> /dev/null; then
        POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment -o jsonpath='{.items[0].metadata.name}')
        HEALTH_STATUS=$(kubectl exec -n "$NAMESPACE" "$POD_NAME" -- curl -s http://localhost:8000/health || echo "Failed")
        log_info "Health status: $HEALTH_STATUS"
    fi

    # Query Prometheus for current metrics (if available)
    if command -v curl &> /dev/null && kubectl get svc prometheus -n monitoring &> /dev/null 2>&1; then
        log_info "Prometheus available, querying metrics..."
        # Port forward is needed for this to work
        # This is just a placeholder
    fi
}

apply_chaos_experiment() {
    local experiment_file=$1
    local experiment_name=$2

    log_info "Applying chaos experiment: $experiment_name"
    log_info "Experiment file: $experiment_file"

    if [ ! -f "$experiment_file" ]; then
        log_error "Experiment file not found: $experiment_file"
        exit 1
    fi

    kubectl apply -f "$experiment_file" -n "$NAMESPACE"
    log_success "Chaos experiment applied"
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
        if check_chaos_mesh; then
            kubectl get podchaos,networkchaos,stresschaos,httpchaos,iochaos,timechaos -n "$NAMESPACE" 2>/dev/null || true
        fi
        if check_litmus; then
            kubectl get chaosengine,chaosresult -n "$NAMESPACE" 2>/dev/null || true
        fi

        # Check HPA
        echo ""
        log_info "HPA Status:"
        kubectl get hpa mlops-sentiment -n "$NAMESPACE" 2>/dev/null || log_warning "HPA not found"

        sleep $check_interval
    done

    log_success "Monitoring period completed"
}

cleanup_experiments() {
    log_info "Cleaning up chaos experiments..."

    if check_chaos_mesh; then
        kubectl delete podchaos,networkchaos,stresschaos,httpchaos,iochaos,timechaos --all -n "$NAMESPACE" 2>/dev/null || true
    fi

    if check_litmus; then
        kubectl delete chaosengine --all -n "$NAMESPACE" 2>/dev/null || true
    fi

    log_success "Cleanup completed"
}

verify_recovery() {
    log_info "Verifying system recovery..."

    local max_wait=300  # 5 minutes
    local waited=0
    local check_interval=10

    while [ $waited -lt $max_wait ]; do
        # Check if all pods are ready
        READY_PODS=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | wc -w)
        TOTAL_PODS=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment --no-headers | wc -l)

        log_info "Ready pods: $READY_PODS/$TOTAL_PODS"

        if [ "$READY_PODS" -ge 1 ]; then
            log_success "System recovered: $READY_PODS pods ready"

            # Try health check
            POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=mlops-sentiment -o jsonpath='{.items[0].metadata.name}')
            if kubectl exec -n "$NAMESPACE" "$POD_NAME" -- curl -s http://localhost:8000/health > /dev/null 2>&1; then
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

    local report_file="chaos_report_$(date +%Y%m%d_%H%M%S).txt"

    cat > "$report_file" <<EOF
========================================
Chaos Engineering Experiment Report
========================================

Experiment Type: $experiment_type
Start Time: $(date -d "@$start_time" '+%Y-%m-%d %H:%M:%S')
End Time: $(date -d "@$end_time" '+%Y-%m-%d %H:%M:%S')
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
$(kubectl get hpa mlops-sentiment -n "$NAMESPACE" 2>/dev/null || echo "HPA not found")

========================================
End of Report
========================================
EOF

    log_success "Report generated: $report_file"
}

show_usage() {
    cat <<EOF
Usage: $0 [EXPERIMENT_TYPE] [DURATION] [MONITORING]

EXPERIMENT_TYPE: Type of chaos experiment to run
    Chaos Mesh experiments:
        - pod-kill: Kill random pods
        - network: Network chaos (latency, loss, partition)
        - stress: CPU/Memory stress
        - http: HTTP-level chaos
        - io: I/O chaos
        - time: Time chaos (clock skew)
        - workflow: Run complete workflow

    Litmus experiments:
        - pod-delete: Delete pods
        - container-kill: Kill containers
        - network-latency: Network latency
        - network-loss: Packet loss
        - cpu-hog: CPU stress
        - memory-hog: Memory stress
        - disk-fill: Disk space stress
        - node-drain: Node drain

DURATION: Monitoring duration in seconds (default: 300)
MONITORING: Enable monitoring (true/false, default: true)

Examples:
    $0 pod-kill 300 true
    $0 network 600 true
    $0 pod-delete 180 false

Environment Variables:
    CHAOS_NAMESPACE: Kubernetes namespace (default: default)
EOF
}

# Main execution
main() {
    echo ""
    log_info "=========================================="
    log_info "Chaos Engineering Experiment Runner"
    log_info "=========================================="
    echo ""

    if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
        show_usage
        exit 0
    fi

    check_prerequisites

    # Determine experiment file and check tool installation
    local experiment_file=""
    if [ -n "${CHAOS_MESH_EXPERIMENTS[$EXPERIMENT_TYPE]}" ]; then
        experiment_file="${CHAOS_MESH_EXPERIMENTS[$EXPERIMENT_TYPE]}"
        if ! check_chaos_mesh; then
            log_error "Chaos Mesh not installed. Please install Chaos Mesh first."
            log_error "Run: make chaos-install"
            exit 1
        fi
        log_info "Chaos Mesh is installed and ready"
    elif [ -n "${LITMUS_EXPERIMENTS[$EXPERIMENT_TYPE]}" ]; then
        experiment_file="${LITMUS_EXPERIMENTS[$EXPERIMENT_TYPE]}"
        if ! check_litmus; then
            log_error "Litmus not installed. Please install Litmus first."
            log_error "Run: make chaos-install"
            exit 1
        fi
        log_info "Litmus is installed and ready"
    else
        log_error "Unknown experiment type: $EXPERIMENT_TYPE"
        show_usage
        exit 1
    fi

    START_TIME=$(date +%s)

    # Capture baseline
    get_baseline_metrics

    # Apply experiment
    apply_chaos_experiment "$experiment_file" "$EXPERIMENT_TYPE"

    # Monitor if enabled
    if [ "$MONITORING" == "true" ]; then
        monitor_experiment "$EXPERIMENT_TYPE" "$DURATION"
    else
        log_info "Monitoring disabled, sleeping for ${DURATION}s..."
        sleep "$DURATION"
    fi

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
