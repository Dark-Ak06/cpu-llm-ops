#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "=== Running Smoke Test against ${BASE_URL} ==="

echo -n "1. Testing /health (liveness)... "
HEALTH_RESP=$(curl -fsS "${BASE_URL}/health")
echo "OK -> ${HEALTH_RESP}"

echo -n "2. Testing /ready (readiness)... "
READY_RESP=$(curl -fsS "${BASE_URL}/ready")
echo "OK -> ${READY_RESP}"

echo "3. Testing /generate (inference)... "
GEN_PAYLOAD='{"prompt": "Explain Kubernetes in one sentence.", "max_tokens": 64, "temperature": 0.2}'
GEN_RESP=$(curl -fsS -X POST "${BASE_URL}/generate" \
    -H "Content-Type: application/json" \
    -d "${GEN_PAYLOAD}")
echo "Response: ${GEN_RESP}"

echo -n "4. Validating generation response structure... "
echo "${GEN_RESP}" | grep -q '"text"' || { echo "Failed: 'text' field missing"; exit 1; }
echo "${GEN_RESP}" | grep -q '"tokens_generated"' || { echo "Failed: 'tokens_generated' field missing"; exit 1; }
echo "${GEN_RESP}" | grep -q '"latency_ms"' || { echo "Failed: 'latency_ms' field missing"; exit 1; }
echo "OK"

echo "5. Testing /generate/stream (SSE streaming)... "
STREAM_RESP=$(curl -fsS -N -X POST "${BASE_URL}/generate/stream" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Say hello", "max_tokens": 16}' | head -n 10)
echo "Stream sample: ${STREAM_RESP}"

echo -n "6. Testing /metrics (Prometheus scrape)... "
METRICS_RESP=$(curl -fsS "${BASE_URL}/metrics")
echo "${METRICS_RESP}" | grep -q "llm_requests_total" || { echo "Failed: 'llm_requests_total' metric missing"; exit 1; }
echo "${METRICS_RESP}" | grep -q "llm_model_loaded" || { echo "Failed: 'llm_model_loaded' metric missing"; exit 1; }
echo "OK"

echo "=== All smoke tests passed successfully! ==="
