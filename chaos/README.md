# Chaos Engineering for KubeSentiment

Comprehensive chaos engineering implementation for testing the resilience, reliability, and fault tolerance of the KubeSentiment MLOps sentiment analysis service.

## Overview

This chaos engineering setup provides three complementary approaches:

1. **Infrastructure-Level Chaos** (Chaos Mesh) - Kubernetes-native chaos experiments
2. **Platform-Level Chaos** (Litmus) - Workflow-based chaos orchestration
3. **Application-Level Chaos** (Custom Middleware) - FastAPI application chaos injection

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Chaos Engineering Stack                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Infrastructure Layer (Chaos Mesh)                          │
│  ├─ Pod Chaos: Kill, failure, restart                       │
│  ├─ Network Chaos: Latency, loss, partition                 │
│  ├─ Stress Chaos: CPU, memory pressure                      │
│  ├─ IO Chaos: Disk latency, errors                          │
│  ├─ HTTP Chaos: Request manipulation                        │
│  └─ Time Chaos: Clock skew                                  │
│                                                              │
│  Platform Layer (Litmus)                                    │
│  ├─ Chaos Workflows: Orchestrated experiments               │
│  ├─ Health Probes: HTTP, K8s, Command, Prometheus           │
│  ├─ Node-Level: Node drain, CPU/memory hog                  │
│  └─ Scheduled Chaos: Automated game days                    │
│                                                              │
│  Application Layer (Custom)                                 │
│  ├─ Middleware: FastAPI chaos injection                     │
│  ├─ Runtime Control: Enable/disable via API                 │
│  ├─ Targeted Chaos: Path/condition-based                    │
│  └─ Metrics: Chaos statistics and monitoring                │
│                                                              │
│  Orchestration & Monitoring                                 │
│  ├─ Scripts: Automated test execution                       │
│  ├─ Grafana: Chaos-specific dashboards                      │
│  ├─ Prometheus: Metrics collection                          │
│  └─ Reports: Automated report generation                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Chaos Tools

```bash
cd chaos/scripts
./install_chaos_tools.sh
```

This installs:
- Chaos Mesh (Kubernetes-native chaos)
- Litmus (workflow-based chaos)
- Argo Workflows (orchestration)

### 2. Run Your First Experiment

```bash
# Run a simple pod kill experiment
./run_chaos_experiment.sh pod-kill 300 true

# Run network latency experiment
./run_chaos_experiment.sh network 600 true

# Run full test suite
python3 chaos_test_suite.py --namespace default
```

### 3. Enable Application-Level Chaos

See [app-chaos/README.md](app-chaos/README.md) for integration steps.

```bash
# Enable via API
curl -X POST http://localhost:8000/api/v1/chaos/enable \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "probability": 0.1}'

# Check status
curl http://localhost:8000/api/v1/chaos/status
```

## Directory Structure

```
chaos/
├── chaos-mesh/              # Chaos Mesh experiment manifests
│   ├── 01-pod-kill.yaml
│   ├── 02-network-chaos.yaml
│   ├── 03-stress-chaos.yaml
│   ├── 04-http-chaos.yaml
│   ├── 05-io-chaos.yaml
│   ├── 06-time-chaos.yaml
│   ├── 07-workflow.yaml
│   └── README.md
├── litmus/                  # Litmus chaos experiments
│   ├── 01-pod-delete.yaml
│   ├── 02-container-kill.yaml
│   ├── 03-pod-network-latency.yaml
│   ├── 04-pod-network-loss.yaml
│   ├── 05-pod-cpu-hog.yaml
│   ├── 06-pod-memory-hog.yaml
│   ├── 07-disk-fill.yaml
│   ├── 08-node-drain.yaml
│   ├── 09-workflow.yaml
│   └── README.md
├── app-chaos/               # Application-level chaos
│   ├── chaos_middleware.py
│   ├── chaos_routes.py
│   ├── __init__.py
│   └── README.md
├── scripts/                 # Orchestration scripts
│   ├── run_chaos_experiment.sh
│   ├── install_chaos_tools.sh
│   └── chaos_test_suite.py
├── dashboards/              # Grafana dashboards
│   └── chaos-monitoring-dashboard.json
└── README.md               # This file
```

## Chaos Experiment Categories

### 1. Pod-Level Chaos

Tests pod resilience and recovery:
- **Pod Kill**: Abrupt pod termination
- **Pod Failure**: Make pod unavailable
- **Container Kill**: Kill specific containers

**Expected Behavior:**
- ✅ Pods recreated by deployment controller
- ✅ HPA maintains desired replica count
- ✅ Service continues with remaining pods
- ✅ Recovery time < 30 seconds

### 2. Network Chaos

Tests network resilience:
- **Latency**: Add delays (100ms - 5s)
- **Packet Loss**: Drop packets (10% - 50%)
- **Partition**: Isolate pods from dependencies
- **Bandwidth Limit**: Throttle network throughput

**Expected Behavior:**
- ✅ Increased latency reflected in metrics
- ✅ Retry mechanisms activated
- ✅ Cache fallback utilized
- ✅ No complete service outage

### 3. Resource Stress

Tests resource management:
- **CPU Stress**: High CPU load
- **Memory Stress**: Memory pressure
- **Disk Fill**: Disk space exhaustion

**Expected Behavior:**
- ✅ HPA triggers scale-up
- ✅ Requests queued properly
- ✅ No OOMKilled events
- ✅ Resource limits respected

### 4. HPA Stress Testing

Tests Horizontal Pod Autoscaler (HPA) behavior under load:
- **CPU Stress**: Apply 80% CPU load to trigger HPA scale-up
- **Scale Monitoring**: Track HPA scaling behavior in real-time
- **Scale Validation**: Verify scale-up to maxReplicas and scale-down to minReplicas

**Expected Behavior:**
- ✅ HPA scales up to maxReplicas when CPU utilization exceeds threshold (70%)
- ✅ Service remains available and responsive during scaling process
- ✅ Latency stays within acceptable SLOs (< 5x normal P95)
- ✅ HPA scales down to minReplicas after stress ends
- ✅ Scale-up completes within 60-90 seconds (HPA stabilization window)
- ✅ Scale-down completes within 5 minutes (scaleDown stabilizationWindowSeconds: 300)

**Usage:**
```bash
# Run HPA-specific chaos test
make chaos-test-hpa

# Or run directly
python3 chaos/scripts/chaos_test_suite.py \
  --namespace default \
  --experiments hpa-stress-test \
  --output chaos_report_hpa.json
```

**What Gets Tested:**
- HPA configuration validation (min/max replicas)
- CPU stress application (80% load, above 70% threshold)
- Real-time HPA replica count monitoring
- Scale-up timing and validation
- Scale-down timing and validation
- Service availability during scaling

**Success Criteria:**
- HPA reaches maxReplicas during stress
- Scale-up time < 120 seconds
- Scale-down time < 600 seconds
- All pods remain healthy throughout
- Service endpoints remain responsive

**Troubleshooting:**
- If HPA doesn't scale up: Check metrics-server is running, verify HPA has CPU metrics configured, ensure resource requests/limits are set on pods
- If scale-up is slow: Check HPA behavior.scaleUp.stabilizationWindowSeconds, verify metrics-server response times
- If scale-down doesn't occur: Check HPA behavior.scaleDown.stabilizationWindowSeconds (default 300s), verify CPU utilization has dropped below threshold

### 5. Dependency Chaos

Tests external dependency handling:
- **Redis Partition**: Cache unavailability
- **Kafka Partition**: Stream processing disruption
- **Vault Unavailability**: Secrets access failure

**Expected Behavior:**
- ✅ Graceful degradation
- ✅ Fallback to non-cached operation
- ✅ Circuit breakers triggered
- ✅ Error handling activated

### 6. Application-Level Chaos

Tests application resilience:
- **HTTP Errors**: 500, 503, 504 responses
- **Latency Injection**: Random delays
- **Exceptions**: Raised errors
- **Partial Failures**: Degraded responses

**Expected Behavior:**
- ✅ Client retries triggered
- ✅ Error rates monitored
- ✅ SLOs maintained
- ✅ Observability accurate

## Chaos Workflows

### Basic Workflow

```bash
1. Establish baseline metrics
2. Apply chaos experiment
3. Monitor system behavior
4. Stop chaos injection
5. Verify recovery
6. Generate report
```

### Automated Test Suite

```bash
# Run comprehensive test suite
python3 chaos/scripts/chaos_test_suite.py \
  --namespace default \
  --output chaos_report.json

# Run specific experiments
python3 chaos/scripts/chaos_test_suite.py \
  --experiments pod-kill-basic network-delay \
  --namespace default

# Run HPA stress test
make chaos-test-hpa

# Or run HPA test directly
python3 chaos/scripts/chaos_test_suite.py \
  --experiments hpa-stress-test \
  --namespace default \
  --output chaos_report_hpa.json
```

### Scheduled Chaos (Game Days)

```bash
# Apply scheduled chaos (every 6 hours)
kubectl apply -f chaos/chaos-mesh/07-workflow.yaml

# View schedule
kubectl get schedule -n default

# Disable scheduled chaos
kubectl delete schedule sentiment-scheduled-chaos
```

## Monitoring During Chaos

### Grafana Dashboards

```bash
# Port forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:80

# Access dashboards at http://localhost:3000
```

Import the chaos monitoring dashboard:
1. Go to Dashboards → Import
2. Upload `chaos/dashboards/chaos-monitoring-dashboard.json`
3. Select Prometheus data source

**Key Metrics to Monitor:**
- Request success rate
- Response latency (p95, p99)
- Pod status and restarts
- HPA scaling behavior (replica counts, scale-up/down timing)
- HPA CPU utilization vs target threshold
- Error rates by type
- Resource utilization

### Prometheus Queries

```promql
# Success rate
sum(rate(sentiment_requests_total{status="success"}[1m])) / sum(rate(sentiment_requests_total[1m])) * 100

# Request latency p95
histogram_quantile(0.95, sum(rate(sentiment_request_duration_seconds_bucket[1m])) by (le))

# Pod restarts
rate(kube_pod_container_status_restarts_total{namespace="default",pod=~"mlops-sentiment.*"}[5m])

# HPA current replicas
kube_horizontalpodautoscaler_status_current_replicas{horizontalpodautoscaler="mlops-sentiment"}

# HPA desired replicas
kube_horizontalpodautoscaler_status_desired_replicas{horizontalpodautoscaler="mlops-sentiment"}

# HPA scaling events (changes in replica count)
changes(kube_horizontalpodautoscaler_status_current_replicas{horizontalpodautoscaler="mlops-sentiment"}[1m]) > 0

# HPA CPU utilization target vs current
kube_horizontalpodautoscaler_spec_target_metric{horizontalpodautoscaler="mlops-sentiment",resource="cpu"}
kube_horizontalpodautoscaler_status_current_metrics{horizontalpodautoscaler="mlops-sentiment"}

# HPA min/max replicas
kube_horizontalpodautoscaler_spec_min_replicas{horizontalpodautoscaler="mlops-sentiment"}
kube_horizontalpodautoscaler_spec_max_replicas{horizontalpodautoscaler="mlops-sentiment"}
```

### Logs

```bash
# Stream logs during chaos
kubectl logs -f -l app.kubernetes.io/name=mlops-sentiment -n default

# Filter for chaos events
kubectl logs -l app.kubernetes.io/name=mlops-sentiment -n default | grep -i chaos

# View all events
kubectl get events -n default --sort-by='.lastTimestamp'
```

## Success Criteria

Define clear success criteria for each experiment:

### Service Availability
- ✅ Uptime ≥ 99% during chaos
- ✅ At least 1 pod always healthy
- ✅ Health checks pass throughout

### Performance
- ✅ P95 latency < 5x normal
- ✅ P99 latency < 10x normal
- ✅ Throughput ≥ 70% of baseline

### Recovery
- ✅ Full recovery < 2 minutes
- ✅ No manual intervention required
- ✅ All pods return to healthy state

### Data Integrity
- ✅ No data loss
- ✅ No duplicate processing
- ✅ Consistent state

## Best Practices

### 1. Start Small
- Begin with low severity experiments
- Test in non-production first
- Gradually increase chaos intensity

### 2. Hypothesis-Driven
```
Hypothesis: When a pod is killed, the service remains available
Expected: No downtime, automatic pod recreation
Validation: Monitor success rate, check pod count
```

### 3. Monitor Actively
- Watch dashboards during experiments
- Stream logs in real-time
- Keep team on standby

### 4. Document Everything
- Record observations
- Note unexpected behavior
- Track improvements

### 5. Automate
- Schedule regular chaos game days
- Integrate with CI/CD
- Automated reporting

### 6. Communicate
- Notify team before experiments
- Share results and learnings
- Update runbooks

### 7. Progressive Rollout
```
Development → Staging → Limited Production → Full Production
```

## Safety Considerations

### Blast Radius Control

All experiments are scoped to limit impact:
```yaml
selector:
  namespaces:
    - default
  labelSelectors:
    app.kubernetes.io/name: mlops-sentiment
```

### Time Limits

All chaos has maximum duration:
```yaml
duration: '5m'        # Chaos active time
scheduler:
  cron: '@every 1h'   # Frequency
```

### Emergency Stop

```bash
# Stop all chaos immediately
kubectl delete podchaos,networkchaos,stresschaos,httpchaos,iochaos,timechaos --all -n default
kubectl delete chaosengine --all -n default

# Disable application chaos
curl -X POST http://localhost:8000/api/v1/chaos/disable
```

### Production Guidelines

**DO NOT** run chaos in production without:
1. ✅ Change management approval
2. ✅ Team notification
3. ✅ Monitoring setup
4. ✅ Rollback plan
5. ✅ Off-hours timing
6. ✅ On-call engineer available

## Troubleshooting

### Chaos Not Working

```bash
# Check Chaos Mesh status
kubectl get pods -n chaos-mesh
kubectl logs -n chaos-mesh -l app.kubernetes.io/component=controller-manager

# Check Litmus status
kubectl get pods -n litmus
kubectl get chaosengine -o wide

# Verify CRDs installed
kubectl get crd | grep chaos
```

### System Not Recovering

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=mlops-sentiment

# Check pod events
kubectl describe pods -l app.kubernetes.io/name=mlops-sentiment

# Check HPA
kubectl get hpa mlops-sentiment

# Force cleanup
kubectl delete podchaos --all --force
```

### Permission Errors

```bash
# Verify service accounts
kubectl get sa litmus-admin
kubectl get clusterrolebinding litmus-admin

# Grant permissions
kubectl create clusterrolebinding litmus-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=default:litmus-admin
```

## CI/CD Integration

### GitLab CI Example

```yaml
chaos-test:
  stage: test
  script:
    - kubectl apply -f chaos/chaos-mesh/01-pod-kill.yaml
    - sleep 300
    - kubectl delete podchaos --all
    - ./chaos/scripts/verify_recovery.sh
  only:
    - main
  when: manual
```

### GitHub Actions Example

```yaml
name: Chaos Testing
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * 1'  # Every Monday 2am

jobs:
  chaos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Chaos Tests
        run: |
          python3 chaos/scripts/chaos_test_suite.py
      - name: Upload Report
        uses: actions/upload-artifact@v2
        with:
          name: chaos-report
          path: chaos_report.*
```

## Results & Learnings

Document your chaos engineering results:

```bash
# Generate report
python3 chaos/scripts/chaos_test_suite.py --output results/$(date +%Y%m%d)_chaos_report.json

# Review findings
cat results/*_chaos_report.txt
```

### Example Learnings Template

```markdown
## Experiment: Pod Kill Test
**Date:** 2025-11-03
**Duration:** 5 minutes
**Severity:** Low

### Observations
- Pod recovered in 12 seconds
- No service downtime observed
- HPA maintained 3 replicas

### Issues Found
- Readiness probe delay caused 5s unavailability
- Metrics gap during pod restart

### Improvements Made
- Reduced readiness probe initial delay from 10s to 5s
- Added PodDisruptionBudget with minAvailable: 2

### Next Steps
- Test with 2 pods killed simultaneously
- Validate behavior under load
```

## Resources

### Documentation
- [Chaos Mesh Docs](https://chaos-mesh.org/docs/)
- [Litmus Docs](https://docs.litmuschaos.io/)
- [Principles of Chaos Engineering](https://principlesofchaos.org/)

### Tools
- Chaos Mesh Dashboard: http://localhost:2333 (after port-forward)
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

### Community
- [Chaos Engineering Slack](https://chaos-community.slack.com/)
- [CNCF Chaos Engineering WG](https://github.com/cncf/tag-app-delivery)

## Support

For issues or questions:
1. Check troubleshooting section
2. Review logs and events
3. Consult tool-specific documentation
4. Create an issue in the repository

## License

This chaos engineering implementation is part of the KubeSentiment project.
