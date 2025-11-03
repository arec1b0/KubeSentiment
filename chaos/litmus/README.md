# Litmus Chaos Experiments

This directory contains Litmus Chaos experiment definitions for testing the resilience of the KubeSentiment application.

## Prerequisites

### Install Litmus

```bash
# Install Litmus Operator
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v3.0.0.yaml

# Verify installation
kubectl get pods -n litmus

# Install Chaos Experiments
kubectl apply -f https://hub.litmuschaos.io/api/chaos/master?file=charts/generic/experiments.yaml
```

### Create Service Account

```bash
# Create Litmus admin service account
kubectl create sa litmus-admin -n default

# Create cluster role binding
kubectl create clusterrolebinding litmus-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=default:litmus-admin
```

### Install Argo Workflows (for workflow orchestration)

```bash
kubectl create namespace argo
kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/latest/download/install.yaml

# Create service account for Argo
kubectl create sa argo-chaos -n default
kubectl create clusterrolebinding argo-chaos \
  --clusterrole=cluster-admin \
  --serviceaccount=default:argo-chaos
```

## Experiment Categories

### 1. Pod Delete (`01-pod-delete.yaml`)
Deletes pods to test recovery mechanisms:
- Deletes 33% of pods
- 60s total chaos duration
- 10s interval between deletions
- HTTP probe for health monitoring

### 2. Container Kill (`02-container-kill.yaml`)
Kills containers to test restart policies:
- Targets `mlops-sentiment` container
- Affects 50% of pods
- 60s chaos duration
- Validates model info endpoint

### 3. Pod Network Latency (`03-pod-network-latency.yaml`)
Introduces network delays:
- 2000ms latency with 500ms jitter
- 120s chaos duration
- Affects 33% of pods
- Monitors response time degradation

### 4. Pod Network Loss (`04-pod-network-loss.yaml`)
Simulates packet loss:
- 30% packet loss
- 90s chaos duration
- Affects 25% of pods
- Tests service availability

### 5. Pod CPU Hog (`05-pod-cpu-hog.yaml`)
Stresses CPU resources:
- 2 CPU cores at 80% load
- 180s chaos duration
- Affects 50% of pods
- Monitors HPA scaling behavior

### 6. Pod Memory Hog (`06-pod-memory-hog.yaml`)
Stresses memory resources:
- 512MB memory consumption
- 180s chaos duration
- Affects 33% of pods
- Prometheus probe for memory monitoring

### 7. Disk Fill (`07-disk-fill.yaml`)
Fills disk space:
- 80% disk fill with 512MB
- 120s chaos duration
- Affects 25% of pods
- Command probe for disk usage

### 8. Node Drain (`08-node-drain.yaml`)
Drains nodes to test rescheduling:
- Drains 25% of nodes
- 180s chaos duration
- Tests pod rescheduling
- Monitors service health during drain

### 9. Workflow (`09-workflow.yaml`)
Orchestrated chaos scenarios:
- **chaos-pipeline**: Sequential execution of multiple experiments
- **scheduled-chaos**: Cron-based random chaos injection every 6 hours

## Running Experiments

### Apply Individual Experiment

```bash
# Apply pod delete experiment
kubectl apply -f 01-pod-delete.yaml

# Check status
kubectl get chaosengine
kubectl describe chaosengine sentiment-pod-delete

# View chaos result
kubectl get chaosresult
kubectl describe chaosresult sentiment-pod-delete-pod-delete
```

### Run Workflow

```bash
# Apply workflow
kubectl apply -f 09-workflow.yaml

# Submit workflow
argo submit 09-workflow.yaml -n default --watch

# List workflows
argo list -n default

# Get workflow details
argo get sentiment-litmus-workflow -n default

# View logs
argo logs sentiment-litmus-workflow -n default
```

### Enable Scheduled Chaos

```bash
# Apply cron workflow
kubectl apply -f 09-workflow.yaml

# List cron workflows
argo cron list -n default

# Suspend scheduling
argo cron suspend sentiment-scheduled-chaos -n default

# Resume scheduling
argo cron resume sentiment-scheduled-chaos -n default
```

### Stop Experiment

```bash
# Delete chaos engine (stops ongoing chaos)
kubectl delete chaosengine sentiment-pod-delete

# Patch to stop
kubectl patch chaosengine sentiment-pod-delete \
  -p '{"spec":{"engineState":"stop"}}' \
  --type=merge
```

## Probes

Litmus supports multiple probe types for validating hypothesis:

### HTTP Probe
Validates API endpoints:
```yaml
probe:
  - name: check-health
    type: httpProbe
    mode: Continuous
    httpProbe/inputs:
      url: 'http://service/health'
      method:
        get:
          criteria: '=='
          responseCode: '200'
```

### K8s Probe
Validates Kubernetes resources:
```yaml
probe:
  - name: check-pods
    type: k8sProbe
    mode: Edge
    k8sProbe/inputs:
      resource: pods
      labelSelector: 'app=myapp'
      operation: present
```

### Command Probe
Executes custom commands:
```yaml
probe:
  - name: check-disk
    type: cmdProbe
    mode: Continuous
    cmdProbe/inputs:
      command: 'df -h | tail -1'
      comparator:
        type: int
        criteria: '<='
        value: '90'
```

### Prometheus Probe
Queries Prometheus metrics:
```yaml
probe:
  - name: check-memory
    type: promProbe
    mode: Continuous
    promProbe/inputs:
      endpoint: 'http://prometheus:9090'
      query: 'container_memory_usage_bytes'
      comparator:
        criteria: '<='
        value: '1073741824'
```

## Probe Modes

- **SoT (Start of Test)**: Runs once before chaos
- **EoT (End of Test)**: Runs once after chaos
- **Edge**: Runs before and after chaos
- **Continuous**: Runs throughout chaos duration
- **OnChaos**: Runs only while chaos is active

## Monitoring

### View Experiment Status

```bash
# List all chaos engines
kubectl get chaosengine -o wide

# List chaos results
kubectl get chaosresult

# Get detailed result
kubectl get chaosresult sentiment-pod-delete-pod-delete -o yaml
```

### Portal Access (if installed)

```bash
# Port forward Litmus Portal
kubectl port-forward -n litmus svc/litmusportal-frontend-service 3000:9091

# Access at http://localhost:3000
# Default credentials: admin / litmus
```

### Metrics

Litmus exports metrics to Prometheus:
```bash
# Check chaos exporter
kubectl get svc -n litmus chaos-exporter

# Example metrics
litmuschaos_experiment_verdict
litmuschaos_experiment_passed_experiments
litmuschaos_experiment_failed_experiments
```

## Expected Behaviors

### Pod/Container Deletion
- ✅ Pods recreated automatically
- ✅ Service remains available
- ✅ HPA maintains desired replicas
- ✅ Zero downtime with PDB

### Network Chaos
- ✅ Increased latency in metrics
- ✅ Retry mechanisms triggered
- ✅ Circuit breakers activated
- ✅ Graceful degradation

### Resource Stress
- ✅ HPA scales up pods
- ✅ CPU/Memory metrics spike
- ✅ Requests queued properly
- ✅ No OOM kills

### Node Drain
- ✅ Pods rescheduled to other nodes
- ✅ PDB prevents complete unavailability
- ✅ Rolling updates continue
- ✅ Service discovery updated

## Troubleshooting

### Experiment Not Starting

```bash
# Check chaos operator logs
kubectl logs -n litmus -l app.kubernetes.io/component=operator

# Check experiment pod
kubectl get pods -l chaosUID=<chaos-uid>
kubectl logs <experiment-pod>
```

### Probe Failures

```bash
# Check probe configuration
kubectl describe chaosengine <name>

# View probe results
kubectl get chaosresult <name> -o jsonpath='{.status.probeStatus}'
```

### Permission Issues

```bash
# Verify service account
kubectl get sa litmus-admin

# Check role bindings
kubectl get clusterrolebinding litmus-admin

# Grant additional permissions if needed
kubectl create clusterrolebinding litmus-admin-extra \
  --clusterrole=cluster-admin \
  --serviceaccount=default:litmus-admin
```

### Cleanup Stuck Resources

```bash
# Force delete chaos engine
kubectl delete chaosengine <name> --force --grace-period=0

# Remove finalizers
kubectl patch chaosengine <name> \
  -p '{"metadata":{"finalizers":null}}' \
  --type=merge

# Clean up experiment pods
kubectl delete pods -l chaosUID=<chaos-uid>
```

## Best Practices

1. **Start Small**: Begin with single experiments before workflows
2. **Monitor Actively**: Watch metrics and logs during experiments
3. **Use Probes**: Define success criteria with probes
4. **Set Timeouts**: Always limit chaos duration
5. **Document Results**: Record observations and improvements
6. **Progressive Rollout**: Test in dev → staging → production

## Integration with CI/CD

```yaml
# GitLab CI example
chaos-test:
  stage: test
  script:
    - kubectl apply -f chaos/litmus/01-pod-delete.yaml
    - kubectl wait --for=condition=ChaosEngineCompleted chaosengine/sentiment-pod-delete --timeout=600s
    - kubectl get chaosresult -o json | jq '.items[0].spec.experimentStatus.verdict'
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

## References

- [Litmus Documentation](https://docs.litmuschaos.io/)
- [Chaos Hub](https://hub.litmuschaos.io/)
- [Litmus GitHub](https://github.com/litmuschaos/litmus)
- [ChaosNative Blog](https://www.chaosnative.com/blog)
