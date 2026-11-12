#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="${HOME}/bin:$PATH"

echo "=== 1. Checking Terraform Formatting ==="
terraform -chdir="${REPO_ROOT}/terraform" fmt -check -recursive
echo "OK: Terraform fmt clean"

echo "=== 2. Validating Terraform Single-Node Example ==="
cd "${REPO_ROOT}/terraform/examples/single-node"
terraform init -backend=false
terraform validate
echo "OK: Terraform validate passed"

echo "=== 3. Running TFLint ==="
cd "${REPO_ROOT}/terraform"
tflint --init 2>/dev/null || true
tflint --recursive
echo "OK: TFLint passed"

echo "=== 4. Running Helm Lint ==="
helm lint "${REPO_ROOT}/k8s/helm/cpu-llm-ops"
echo "OK: Helm lint passed"

echo "=== 5. Running Helm Template ==="
helm template test-release "${REPO_ROOT}/k8s/helm/cpu-llm-ops" > /dev/null
echo "OK: Helm template passed"

echo "=== All IaC & Helm checks PASSED! ==="
