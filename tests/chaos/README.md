# Chaos Engineering Tests for KubeSentiment

This directory contains chaos engineering tests to validate the resilience and fault tolerance of the KubeSentiment application.

## Overview

Chaos engineering is the discipline of experimenting on a system to build confidence in its capability to withstand turbulent conditions in production. These tests deliberately inject failures to verify that the system can gracefully handle them.

## Test Suite

### 1. Pod Termination Test
**Purpose**: Verify that the system can recover from a single pod failure

**What it does**:
- Terminates one pod
- Checks that service remains available (via other replicas)
- Verifies that Kubernetes restarts the pod
- Confirms full recovery

**Expected Behavior**:
- Service should remain available during pod termination
- New pod should start automatically
- Health checks should pass throughout

### 2. Random Pod Killer Test
**Purpose**: Test resilience under continuous random pod failures

**What it does**:
- Randomly kills pods every 10 seconds for 30 seconds
- Continuously monitors service health
- Verifies recovery after chaos stops

**Expected Behavior**:
- Service should maintain ≥70% uptime during chaos
- System should fully recover after chaos ends

### 3. Multiple Pod Termination Test
**Purpose**: Validate behavior when multiple pods fail simultaneously

**What it does**:
- Terminates half of the running pods at once
- Monitors service availability
- Verifies full pod count is restored

**Expected Behavior**:
- Service may degrade but should not completely fail
- All pods should be restored
- Final health checks should pass

### 4. Service Degradation Test
**Purpose**: Test performance under reduced capacity

**What it does**:
- Scales deployment down to 1 replica
- Tests health and prediction endpoints
- Restores original replica count

**Expected Behavior**:
- Service should work with single replica
- Prediction endpoint should remain functional
- Scaling should work smoothly

### 5. Rapid Scaling Test
**Purpose**: Verify stability during rapid scaling operations

**What it does**:
- Rapidly scales deployment up and down
- Monitors health during transitions
- Restores original state

**Expected Behavior**:
- Service should maintain ≥75% health checks
- Final replica count should match original
- No persistent errors

## Prerequisites

### Required Tools
- `kubectl` configured with access to your cluster
- Python 3.8+ with asyncio support

### Kubernetes Requirements
- Running KubeSentiment deployment
- Sufficient RBAC permissions to:
  - List/delete pods
  - Scale deployments
  - Create temporary pods for health checks

### Application Requirements
- At least 2 replicas for meaningful chaos tests
- Health endpoint accessible at `/health`
- Prediction endpoint at `/api/v1/predict`

## Usage

### Basic Usage

```bash
# Run all chaos tests against default namespace
python chaos_engineering_tests.py

# Specify namespace and label selector
python chaos_engineering_tests.py \
  --namespace mlops-sentiment \
  --app-label app.kubernetes.io/name=mlops-sentiment \
  --service-name mlops-sentiment

# Save results to file
python chaos_engineering_tests.py --output chaos_results.json
```

### Running Individual Tests

To run individual tests, you can modify the test suite or comment out tests you don't want to run in the `run_all_tests()` method.

### Interpreting Results

The test suite generates a JSON report with:

```json
{
  "summary": {
    "total_tests": 5,
    "passed": 4,
    "failed": 1,
    "errors": 0,
    "success_rate": 80.0
  },
  "results": [
    {
      "test": "Pod Termination Test",
      "status": "passed",
      "details": {}
    }
  ]
}
```

**Success Criteria**: ≥80% of tests passing

## Safety Guidelines

### Development Environment
- Run these tests in development/staging environments first
- Verify that PodDisruptionBudgets are configured
- Ensure adequate monitoring is in place

### Production Environment
- **ONLY** run during maintenance windows or off-peak hours
- Have incident response team on standby
- Start with less aggressive tests
- Monitor business metrics during testing

### What NOT to Do
- Don't run chaos tests without approval from operations team
- Don't run tests during business-critical periods
- Don't run tests without monitoring in place
- Don't run tests if you don't have rollback procedures

## Advanced Scenarios

### Network Partition Testing

```bash
# Requires NET_ADMIN capability in pods
# Add to deployment securityContext:
#   capabilities:
#     add: ["NET_ADMIN"]

# The test suite includes network partition methods but requires
# additional pod permissions to execute
```

### Custom Chaos Experiments

Extend the `ChaosEngineeringTests` class:

```python
async def test_custom_scenario(self) -> bool:
    """Your custom chaos test"""
    # Implement your chaos scenario
    pass

# Add to run_all_tests():
tests.append(("Custom Test", self.test_custom_scenario))
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Chaos Engineering Tests

on:
  schedule:
    - cron: '0 2 * * 6'  # Weekly on Saturday at 2 AM

jobs:
  chaos-tests:
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Setup kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubeconfig
        run: |
          echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig

      - name: Run Chaos Tests
        run: |
          python tests/chaos/chaos_engineering_tests.py \
            --namespace staging \
            --output chaos_results.json

      - name: Upload Results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: chaos-test-results
          path: chaos_results.json
```

## Monitoring During Chaos Tests

### Key Metrics to Monitor

1. **Application Metrics**:
   - Request success rate
   - Latency (p50, p95, p99)
   - Error rates

2. **Kubernetes Metrics**:
   - Pod restart counts
   - Pod ready status
   - Node resource utilization

3. **Business Metrics**:
   - Transaction success rate
   - User-facing errors

### Prometheus Queries

```promql
# Request success rate
rate(http_requests_total{status="200"}[5m]) / rate(http_requests_total[5m])

# Pod restart count
kube_pod_container_status_restarts_total{namespace="mlops-sentiment"}

# Service availability
up{job="mlops-sentiment"}
```

## Troubleshooting

### Test Failures

**Symptom**: All health checks failing
- **Solution**: Check if service is actually running
- **Command**: `kubectl get pods -n <namespace>`

**Symptom**: Pods not recovering
- **Solution**: Check pod logs and events
- **Command**: `kubectl describe pod <pod-name> -n <namespace>`

**Symptom**: Permission denied errors
- **Solution**: Verify RBAC permissions
- **Command**: `kubectl auth can-i delete pods -n <namespace>`

### Common Issues

1. **Insufficient Replicas**
   - Need at least 2 replicas for meaningful chaos tests
   - Update deployment: `kubectl scale deployment mlops-sentiment --replicas=3`

2. **No PodDisruptionBudget**
   - Create PDB to ensure minimum availability
   - Already configured in Helm chart: `helm/mlops-sentiment/templates/pdb.yaml`

3. **Slow Pod Startup**
   - Increase test timeouts if pods take long to start
   - Check init containers and health check delays

## Best Practices

1. **Start Small**: Begin with single pod termination before aggressive tests
2. **Monitor Continuously**: Watch metrics during entire test duration
3. **Document Learnings**: Record what breaks and how to fix it
4. **Automate Recovery**: Build automated remediation for common failures
5. **Regular Testing**: Run chaos tests regularly to catch regressions

## Resources

- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [Kubernetes Chaos Engineering Tools](https://kubernetes.io/docs/tasks/debug-application-cluster/)
- [Site Reliability Engineering Book](https://sre.google/books/)
- [Chaos Monkey](https://netflix.github.io/chaosmonkey/)

## Contributing

To add new chaos tests:

1. Create a new test method in `ChaosEngineeringTests`
2. Follow the naming convention: `test_<scenario_name>`
3. Return `bool` indicating pass/fail
4. Add to `run_all_tests()` method
5. Update this README with test documentation

## Support

For issues or questions about chaos engineering tests:
- Open an issue in the repository
- Tag with `chaos-engineering` label
- Include test output and logs
