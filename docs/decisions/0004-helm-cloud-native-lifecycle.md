# ADR 0004: Cloud-Native Lifecycle Management via Helm

## Status
Accepted

## Context
Deploying LLM inference services on Kubernetes presents unique operational challenges: large model weights (~1-10 GB) cannot be baked into images without slowing down rollout times, model initialization takes several seconds to load into memory, and CPU spikes during inference require responsive horizontal autoscaling.

## Decision
We package the Kubernetes deployment as a comprehensive Helm v3 chart adhering to cloud-native best practices:
1. **Decoupled Model Storage via Init Container**: An unprivileged init container verifies existing weights on a PersistentVolumeClaim (PVC) or downloads them on first launch, ensuring the primary container starts with pre-warmed weights.
2. **Three-Tier Probes**:
   - `startupProbe`: Allows up to 150s for initial model loading before Kubernetes initiates restart loops.
   - `livenessProbe`: Verifies ASGI process health on `/health`.
   - `readinessProbe`: Verifies `/ready` status, routing traffic only when the model engine is confirmed loaded in RAM.
3. **Resilience & Autoscale**:
   - Horizontal Pod Autoscaler (HPA) targeting 80% CPU utilization.
   - PodDisruptionBudget (PDB) guaranteeing minimum availability during node draining or rolling upgrades.
   - NetworkPolicy restricting ingress/egress to necessary communication ports.

## Consequences
### Positive
- Production-ready rolling updates without dropped requests.
- Automatic traffic redirection during model reloads.
- Standardized deployment configuration via `values.yaml` across dev, kind, and production environments.

### Negative
- Requires PVC provisioning with ReadWriteOnce or ReadWriteMany access modes on cloud clusters.
