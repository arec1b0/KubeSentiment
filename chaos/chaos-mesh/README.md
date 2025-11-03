# Chaos Mesh Experiments

This directory contains Chaos Mesh experiment definitions for testing the resilience of the KubeSentiment application.

## Prerequisites

Install Chaos Mesh on your Kubernetes cluster:

```bash
# Install using Helm
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update
helm install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace=chaos-mesh \
  --create-namespace \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock
```

Or using kubectl:

```bash
curl -sSL https://mirrors.chaos-mesh.org/latest/install.sh | bash
```

## Experiment Categories

### 1. Pod Chaos (`01-pod-kill.yaml`)
Tests pod-level failures and recovery:
- **pod-kill**: Kills a random pod every 10 minutes
- **pod-failure**: Makes a pod unavailable for 2 minutes every 30 minutes
- **container-kill**: Kills the main container every 20 minutes

### 2. Network Chaos (`02-network-chaos.yaml`)
Tests network resilience:
- **network-delay**: Adds 100ms latency with 10ms jitter
- **network-loss**: Drops 25% of packets
- **network-partition**: Isolates pods from Redis
- **kafka-partition**: Isolates pods from Kafka
- **bandwidth-limit**: Limits bandwidth to 1 Mbps

### 3. Stress Chaos (`03-stress-chaos.yaml`)
Tests resource pressure scenarios:
- **cpu-stress**: 80% CPU load on 2 workers
- **memory-stress**: Allocates 512MB of memory
- **mixed-stress**: Combines CPU and memory stress

### 4. HTTP Chaos (`04-http-chaos.yaml`)
Tests HTTP-level failures:
- **http-delay**: Adds 2s delay to `/api/v1/predict` requests
- **http-abort**: Aborts requests to the prediction endpoint
- **http-patch-response**: Modifies response bodies

### 5. IO Chaos (`05-io-chaos.yaml`)
Tests filesystem operations:
- **io-delay**: Adds 100ms delay to model cache reads
- **io-errno**: Injects I/O errors
- **io-mixed**: Combines latency and space errors

### 6. Time Chaos (`06-time-chaos.yaml`)
Tests clock skew scenarios:
- **clock-skew**: Shifts clock back by 1 hour
- **clock-forward**: Shifts clock forward by 30 minutes

### 7. Workflows (`07-workflow.yaml`)
Orchestrated chaos scenarios:
- **comprehensive-chaos**: Sequential execution of multiple chaos types
- **disaster-scenario**: Parallel execution of pod, network, and CPU chaos
- **scheduled-chaos**: Automated chaos execution every 6 hours

## Running Experiments

### Apply a Single Experiment

```bash
# Apply pod kill experiment
kubectl apply -f 01-pod-kill.yaml

# Check status
kubectl get podchaos

# View details
kubectl describe podchaos sentiment-pod-kill
```

### Apply All Experiments

```bash
# Apply all chaos experiments
kubectl apply -f .

# List all chaos experiments
kubectl get podchaos,networkchaos,stresschaos,httpchaos,iochaos,timechaos
```

### Run a Workflow

```bash
# Run comprehensive chaos workflow
kubectl apply -f 07-workflow.yaml

# Watch workflow execution
kubectl get workflow sentiment-comprehensive-chaos -w

# View workflow details
kubectl describe workflow sentiment-comprehensive-chaos
```

### Pause/Resume Experiments

```bash
# Pause an experiment
kubectl annotate podchaos sentiment-pod-kill experiment.chaos-mesh.org/pause=true

# Resume an experiment
kubectl annotate podchaos sentiment-pod-kill experiment.chaos-mesh.org/pause-
```

### Delete Experiments

```bash
# Delete a specific experiment
kubectl delete podchaos sentiment-pod-kill

# Delete all experiments
kubectl delete podchaos,networkchaos,stresschaos,httpchaos,iochaos,timechaos --all
```

## Monitoring During Chaos

### Grafana Dashboards
Access Grafana to monitor metrics during chaos experiments:
```bash
# Port forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:80
```

View dashboards at http://localhost:3000:
- MLOps Sentiment Analysis Dashboard
- Advanced Metrics Dashboard
- Chaos Engineering Dashboard (custom)

### Prometheus Metrics
Key metrics to monitor:
- `sentiment_requests_total`: Request count
- `sentiment_request_duration_seconds`: Latency
- `sentiment_model_loaded`: Model availability
- `sentiment_active_requests`: Concurrent requests

### Logs
Stream logs during experiments:
```bash
# All pods
kubectl logs -l app.kubernetes.io/name=mlops-sentiment -f --tail=100

# Specific pod
kubectl logs <pod-name> -f
```

### Health Checks
Monitor endpoint health:
```bash
# Health endpoint
kubectl exec -it <pod-name> -- curl http://localhost:8000/health

# Readiness check
kubectl get pods -l app.kubernetes.io/name=mlops-sentiment -o wide
```

## Expected Behaviors

### Pod Kill/Failure
- ✅ HPA should create replacement pods
- ✅ Service continues with remaining replicas
- ✅ Request success rate >95%
- ✅ Recovery time <30s

### Network Chaos
- ✅ Increased latency reflected in metrics
- ✅ Graceful degradation with cache fallback
- ✅ Kafka consumer group rebalancing
- ✅ No complete service outage

### Stress Chaos
- ✅ HPA triggers scale-up
- ✅ Request latency increases but remains functional
- ✅ Memory/CPU metrics show pressure
- ✅ No OOMKilled events

### HTTP Chaos
- ✅ Client retries triggered
- ✅ Circuit breaker activation
- ✅ Error rates increase temporarily
- ✅ Recovery after chaos ends

## Safety Considerations

1. **Production Usage**: Do NOT run these experiments in production without:
   - Proper change management
   - Stakeholder notification
   - Runbook preparation
   - Rollback plans

2. **Blast Radius**: Experiments target only `mlops-sentiment` pods by default

3. **Duration**: Experiments are time-limited (1-5 minutes typical)

4. **Scheduling**: Scheduled experiments run every 1-12 hours depending on severity

5. **Monitoring**: Always monitor during chaos experiments

## Customization

### Change Target Namespace
Edit the `selector.namespaces` field:
```yaml
selector:
  namespaces:
    - your-namespace
```

### Adjust Chaos Parameters
Modify intensity, duration, or frequency:
```yaml
duration: '5m'          # How long chaos lasts
scheduler:
  cron: '@every 30m'    # How often to run
value: '2'              # Number of affected pods
```

### Add Custom Labels
Target specific pod groups:
```yaml
selector:
  labelSelectors:
    app.kubernetes.io/name: mlops-sentiment
    environment: staging
```

## Troubleshooting

### Chaos Not Applying
```bash
# Check Chaos Mesh status
kubectl get pods -n chaos-mesh

# Check experiment status
kubectl describe podchaos <experiment-name>

# View Chaos Mesh logs
kubectl logs -n chaos-mesh -l app.kubernetes.io/component=controller-manager
```

### Permission Issues
Ensure Chaos Mesh has proper RBAC permissions:
```bash
kubectl get clusterrole chaos-mesh-chaos-controller-manager-cluster-level
```

### Experiments Not Cleaning Up
```bash
# Force delete
kubectl delete podchaos <experiment-name> --force --grace-period=0

# Check finalizers
kubectl patch podchaos <experiment-name> -p '{"metadata":{"finalizers":[]}}' --type=merge
```

## References

- [Chaos Mesh Documentation](https://chaos-mesh.org/docs/)
- [Chaos Engineering Principles](https://principlesofchaos.org/)
- [Kubernetes Chaos Engineering](https://kubernetes.io/blog/2021/05/20/chaos-engineering/)
