$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\bin;C:\Program Files\Docker\Docker\resources\bin;$env:PATH"

$clusterName = "cpu-llm-ops-cluster"

Write-Output "=== 1. Checking Kind Cluster Status ==="
$clusters = & kind get clusters 2>&1
if ($clusters -notcontains $clusterName) {
    Write-Output "Creating Kind cluster '$clusterName'..."
    & kind create cluster --name $clusterName
} else {
    Write-Output "Kind cluster '$clusterName' already exists."
}

Write-Output "`n=== 2. Loading Docker Image into Kind ==="
& kind load docker-image cpu-llm-ops:latest --name $clusterName

Write-Output "`n=== 3. Installing/Upgrading Helm Chart ==="
& helm upgrade --install cpu-llm-ops ./k8s/helm/cpu-llm-ops -f ./k8s/helm/cpu-llm-ops/values-kind.yaml

Write-Output "`n=== 4. Waiting for Pod Readiness ==="
& kubectl rollout status deployment/cpu-llm-ops --timeout=120s

Write-Output "`n=== 5. Kubernetes Resources Status ==="
& kubectl get pods -l app.kubernetes.io/name=cpu-llm-ops -o wide
& kubectl get svc cpu-llm-ops

Write-Output "`n=== Kubernetes Deployment Verified Successfully! ==="
