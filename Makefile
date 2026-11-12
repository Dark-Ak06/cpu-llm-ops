SHELL := /bin/bash
.DEFAULT_GOAL := help

IMAGE_NAME ?= cpu-llm-ops
IMAGE_TAG ?= latest
PORT ?= 8000
KIND_CLUSTER_NAME ?= cpu-llm-ops-cluster

.PHONY: help
help: ## Display this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: bootstrap
bootstrap: ## Setup local directories and environment file
	@bash scripts/bootstrap.sh

.PHONY: download-model
download-model: ## Download Qwen2.5-1.5B GGUF model with sha256 checksum verification
	@MODEL_DIR=models bash scripts/download_model.sh

.PHONY: build
build: ## Build the hardened inference container image
	docker build -f docker/Dockerfile -t $(IMAGE_NAME):$(IMAGE_TAG) .

.PHONY: up
up: ## Start the full production stack (app + model-init + Prometheus + Grafana) via Docker Compose
	docker compose up -d --build
	@echo "Services started. Checking health..."
	@bash -c 'for i in {1..30}; do curl -s http://localhost:$(PORT)/health >/dev/null && break || sleep 2; done'
	@echo "Service running at http://localhost:$(PORT)"
	@echo "Grafana running at http://localhost:3000 (admin / admin)"
	@echo "Prometheus running at http://localhost:9090"

.PHONY: down
down: ## Stop and remove all Docker Compose services and networks
	docker compose down --remove-orphans

.PHONY: restart
restart: down up ## Restart Docker Compose services

.PHONY: logs
logs: ## Stream logs from inference service
	docker compose logs -f app

.PHONY: smoke-test
smoke-test: ## Run smoke test suite against running service
	@bash scripts/smoke_test.sh

.PHONY: test
test: ## Run unit and API tests with coverage report
	python3 -m pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=85 tests/

.PHONY: lint
lint: ## Run code formatters, linters, and type checkers (ruff, mypy)
	ruff check app tests
	ruff format --check app tests
	mypy --config-file pyproject.toml app

.PHONY: fmt
fmt: ## Automatically format Python codebase with ruff
	ruff format app tests
	ruff check --fix app tests

.PHONY: scan
scan: ## Run Trivy vulnerability scanner on image and repository config
	trivy image --severity HIGH,CRITICAL $(IMAGE_NAME):$(IMAGE_TAG)
	trivy config .

.PHONY: k8s-up
k8s-up: build ## Create local kind cluster and install cpu-llm-ops Helm chart
	@echo "Creating kind cluster $(KIND_CLUSTER_NAME) if not exists..."
	@kind get clusters | grep -q "^$(KIND_CLUSTER_NAME)$$" || kind create cluster --name $(KIND_CLUSTER_NAME)
	@echo "Loading image $(IMAGE_NAME):$(IMAGE_TAG) into kind..."
	kind load docker-image $(IMAGE_NAME):$(IMAGE_TAG) --name $(KIND_CLUSTER_NAME)
	@echo "Installing/Upgrading Helm release..."
	helm upgrade --install cpu-llm-ops ./k8s/helm/cpu-llm-ops -f ./k8s/helm/cpu-llm-ops/values-kind.yaml
	@echo "Waiting for deployment to become ready..."
	kubectl rollout status deployment/cpu-llm-ops --timeout=180s
	@echo "Helm release ready."

.PHONY: k8s-down
k8s-down: ## Delete the local kind cluster
	kind delete cluster --name $(KIND_CLUSTER_NAME)

.PHONY: load-test
load-test: ## Execute k6 load test suite against local inference service
	k6 run loadtest/k6-script.js

.PHONY: clean
clean: ## Remove virtualenvs, cache files, and test artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov coverage.xml
