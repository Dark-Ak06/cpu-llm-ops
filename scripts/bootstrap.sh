#!/usr/bin/env bash
set -euo pipefail

echo "=== Bootstrapping cpu-llm-ops Environment ==="

check_tool() {
    local tool="$1"
    if command -v "${tool}" >/dev/null 2>&1; then
        echo "[OK] ${tool} found: $(command -v "${tool}")"
    else
        echo "[WARN] ${tool} not found. Some targets may be unavailable."
    fi
}

echo "--- Checking Prerequisites ---"
check_tool git
check_tool docker
check_tool docker-compose
check_tool curl
check_tool python3
check_tool kubectl
check_tool helm
check_tool kind
check_tool terraform
check_tool tflint
check_tool k6

echo ""
echo "--- Ensuring Environment File ---"
if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "Created .env from .env.example"
else
    echo ".env already exists"
fi

echo ""
echo "--- Ensuring Local Model Cache Directory ---"
mkdir -p models

echo ""
echo "Bootstrap complete! You can now run:"
echo "  make up          -> Launch full stack in Docker Compose"
echo "  make test        -> Run unit tests"
echo "  make k8s-up      -> Launch in local Kubernetes (kind)"
