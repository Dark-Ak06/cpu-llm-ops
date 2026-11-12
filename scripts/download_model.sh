#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR="${MODEL_DIR:-/models}"
MODEL_FILE="${MODEL_FILE:-qwen2.5-1.5b-instruct-q4_k_m.gguf}"
EXPECTED_SHA256="${MODEL_SHA256:-6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e}"
MODEL_URL="${MODEL_URL:-https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf}"

TARGET_PATH="${MODEL_DIR}/${MODEL_FILE}"
TMP_PATH="${TARGET_PATH}.tmp"

mkdir -p "${MODEL_DIR}"

calc_sha256() {
    local file_path="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "${file_path}" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "${file_path}" | awk '{print $1}'
    elif command -v openssl >/dev/null 2>&1; then
        openssl dgst -sha256 "${file_path}" | awk '{print $NF}'
    else
        echo "Error: no SHA256 utility found (sha256sum, shasum, openssl)." >&2
        exit 1
    fi
}

echo "=== LLM Model Init Verification ==="
echo "Target path:      ${TARGET_PATH}"
echo "Expected SHA256:  ${EXPECTED_SHA256}"
echo "Source URL:       ${MODEL_URL}"

if [[ -f "${TARGET_PATH}" ]]; then
    echo "Found existing file at ${TARGET_PATH}. Computing checksum..."
    CURRENT_SHA256=$(calc_sha256 "${TARGET_PATH}")
    if [[ "${CURRENT_SHA256}" == "${EXPECTED_SHA256}" ]]; then
        echo "[OK] Checksum matched (${CURRENT_SHA256}). Model ready for inference."
        exit 0
    else
        echo "[WARN] Checksum mismatch: found ${CURRENT_SHA256}, expected ${EXPECTED_SHA256}."
        echo "Re-downloading model..."
        rm -f "${TARGET_PATH}"
    fi
fi

echo "Downloading ${MODEL_FILE} from Hugging Face..."
curl -fL --retry 5 --retry-delay 2 --retry-max-time 300 -o "${TMP_PATH}" "${MODEL_URL}"

echo "Validating downloaded artifact..."
DOWNLOAD_SHA256=$(calc_sha256 "${TMP_PATH}")
if [[ "${DOWNLOAD_SHA256}" != "${EXPECTED_SHA256}" ]]; then
    echo "[ERROR] Verification failed! Expected: ${EXPECTED_SHA256}, Got: ${DOWNLOAD_SHA256}" >&2
    rm -f "${TMP_PATH}"
    exit 1
fi

mv "${TMP_PATH}" "${TARGET_PATH}"
chmod 644 "${TARGET_PATH}"
echo "[OK] Model download and verification successful: ${TARGET_PATH}"
exit 0
