# cpu-llm-ops: Production CPU-Only LLM Inference Architecture

[![CI](https://github.com/Dark-Ak06/cpu-llm-ops/actions/workflows/ci.yml/badge.svg)](https://github.com/Dark-Ak06/cpu-llm-ops/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Multi--stage-2496ED)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Helm-326CE5)](https://kubernetes.io/)

Production-grade, CPU-only LLM inference service designed for high observability, backpressure-controlled concurrency, and cloud-native GitOps deployment.

Serving **Qwen2.5-1.5B-Instruct** (GGUF `Q4_K_M`) using an optimized C++ runtime without requiring a GPU or paid cloud infrastructure.

---

*Detailed documentation, architecture diagrams, runbooks, and benchmarks are under `docs/` and below.*
