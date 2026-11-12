# Production Operations Runbook

This runbook guides on-call engineers in triaging, diagnosing, and resolving production alerts for the **cpu-llm-ops** service.

---

## 1. Alert: `ServiceDown`

### Severity: Critical
### Trigger: `up{job="cpu-llm-ops"} == 0` for > 30 seconds

### Diagnosis Steps
1. Verify pod status across the Kubernetes namespace:
   ```bash
   kubectl get pods -l app.kubernetes.io/name=cpu-llm-ops
   ```
2. Check for container crashes or restart loops:
   ```bash
   kubectl describe pod -l app.kubernetes.io/name=cpu-llm-ops
   ```
3. Inspect recent stderr and application logs:
   ```bash
   kubectl logs -l app.kubernetes.io/name=cpu-llm-ops --tail=100
   ```
4. Check if the node is experiencing OOM (Out Of Memory):
   ```bash
   kubectl get events --sort-by='.metadata.creationTimestamp' | tail -n 20
   ```

### Remediation
- **If OOMKilled**: Increase pod memory limits in `values.yaml` (`resources.limits.memory`) or scale out node capacity.
- **If stuck in CrashLoopBackOff**: Verify that the `/models` volume is properly mounted and has correct file permissions (`chown 10001:10001`).
- **Restart deployment**:
  ```bash
  kubectl rollout restart deployment/cpu-llm-ops
  ```

---

## 2. Alert: `ModelNotLoaded`

### Severity: Critical
### Trigger: `llm_model_loaded == 0` for > 1 minute

### Diagnosis Steps
1. Verify the `/ready` endpoint status:
   ```bash
   curl -i http://localhost:8000/ready
   ```
2. Check init container execution status:
   ```bash
   kubectl logs <pod-name> -c model-downloader
   ```
3. Inspect whether model weights file exists and matches the required SHA256 checksum:
   ```bash
   kubectl exec <pod-name> -c cpu-llm-ops -- ls -la /models
   ```

### Remediation
- If the init container failed to download weights due to network timeouts, restart the pod to retry:
  ```bash
  kubectl delete pod <pod-name>
  ```
- If running in local or staging environments without internet access, set `MOCK_INFERENCE=true` in the ConfigMap.

---

## 3. Alert: `HighErrorRate`

### Severity: Warning
### Trigger: 5xx or 429 error rate > 5% over 2 minutes

### Diagnosis Steps
1. Identify whether errors are `5xx` (internal errors) or `429` (backpressure rejections):
   ```promql
   sum(rate(llm_requests_total{status=~"5.."}[2m]))
   sum(rate(llm_requests_total{status="429"}[2m]))
   ```
2. Inspect application error logs filtered by log level `ERROR`:
   ```bash
   kubectl logs -l app.kubernetes.io/name=cpu-llm-ops | grep '"level": "ERROR"'
   ```

### Remediation
- **If 429 (Saturation)**: The incoming request rate exceeds CPU capacity.
  - Scale up replicas horizontally:
    ```bash
    kubectl scale deployment/cpu-llm-ops --replicas=3
    ```
  - Verify that the Horizontal Pod Autoscaler (HPA) is functioning:
    ```bash
    kubectl get hpa cpu-llm-ops
    ```
- **If 504 (Timeouts)**: Requests are taking longer than `REQUEST_TIMEOUT_SECONDS`.
  - Check whether clients are passing excessively large `max_tokens` values.
  - Tune `n_threads` to match the allocated CPU limits.

---

## 4. Alert: `HighP95Latency`

### Severity: Warning
### Trigger: `p95` latency exceeds 10 seconds for > 1 minute

### Diagnosis Steps
1. Check current concurrency and queue depth:
   ```promql
   llm_in_flight_requests
   llm_queue_depth
   ```
2. Check node CPU utilization:
   ```bash
   kubectl top pods -l app.kubernetes.io/name=cpu-llm-ops
   ```

### Remediation
- If CPU is throttled (`container_cpu_cfs_throttled_periods_total`), increase CPU limits or set dedicated CPU cores (`cpu: 4000m`).
- Adjust `N_THREADS` in configuration (optimal setting: 1 thread per physical core assigned to the container).

---

## 5. Routine Maintenance Procedures

### Graceful Deployment Upgrade
```bash
helm upgrade --install cpu-llm-ops ./k8s/helm/cpu-llm-ops -f ./k8s/helm/cpu-llm-ops/values.yaml
kubectl rollout status deployment/cpu-llm-ops --timeout=180s
```

### Manual Backup of Cached Model Weights
```bash
docker run --rm -v cpu-llm-ops-models:/models -v $(pwd):/backup alpine tar czf /backup/model-weights-backup.tar.gz /models
```
