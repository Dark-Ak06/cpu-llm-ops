#!/usr/bin/env bash
set -e

BIN_DIR="${HOME}/bin"
mkdir -p "${BIN_DIR}"
export PATH="${BIN_DIR}:$PATH"

if [ ! -f "${BIN_DIR}/terraform" ]; then
    echo "Downloading Terraform..."
    curl -fsSL https://releases.hashicorp.com/terraform/1.7.5/terraform_1.7.5_linux_amd64.zip -o /tmp/tf.zip
    python3 -c "import zipfile; zipfile.ZipFile('/tmp/tf.zip').extractall('${BIN_DIR}')"
    chmod +x "${BIN_DIR}/terraform"
    rm -f /tmp/tf.zip
fi

if [ ! -f "${BIN_DIR}/tflint" ]; then
    echo "Downloading TFLint..."
    curl -fsSL https://github.com/terraform-linters/tflint/releases/download/v0.50.3/tflint_linux_amd64.zip -o /tmp/tflint.zip
    python3 -c "import zipfile; zipfile.ZipFile('/tmp/tflint.zip').extractall('${BIN_DIR}')"
    chmod +x "${BIN_DIR}/tflint"
    rm -f /tmp/tflint.zip
fi

echo "=== Toolchain Status ==="
echo "Helm:      $(helm version --short 2>/dev/null || echo 'not found')"
echo "Terraform: $(${BIN_DIR}/terraform version 2>/dev/null | head -n 1)"
echo "TFLint:    $(${BIN_DIR}/tflint --version 2>/dev/null | head -n 1)"
echo "Kind:      $(kind version 2>/dev/null || echo 'not found')"
echo "Kubectl:   $(kubectl version --client -o yaml 2>/dev/null | grep gitVersion || echo 'not found')"
