# ADR 0001: CPU-Only Quantized Inference via GGUF and llama.cpp

## Status
Accepted

## Context
Deploying Large Language Models in production typically incurs high GPU infrastructure costs (e.g. AWS `p3`, `g4dn`, or `g5` instances costing hundreds to thousands of dollars per month). For lightweight or cost-sensitive enterprise environments, edge deployments, and development pipelines, a GPU requirement prevents accessible horizontal scaling and local reproducibility.

## Decision
We adopt **Qwen2.5-1.5B-Instruct** in 4-bit Medium Quantization (`Q4_K_M` GGUF format) served using the optimized C++ runtime `llama-cpp-python` compiled with AVX2, FMA, and F16C instruction sets.

Key architectural choices:
1. **Model Weights**: ~1.04 GiB file size with verified SHA256 (`6a1a2eb6d156...`). Weights are decoupled from the container image and dynamically pulled into a cached volume by an init step.
2. **Quantization Precision**: `Q4_K_M` provides a sweet spot between perplexity retention (near fp16 baseline) and memory throughput, consuming only ~1.5 GiB RAM during execution.
3. **Instruction Sets**: Compiling with AVX2/FMA utilizes modern x86_64 vectorized matrix multiplication without requiring specialized tensor cores.

## Consequences
### Positive
- Fully operational on standard commodity x86_64 laptops, CI runners, and small cloud VMs (e.g. 2-4 vCPUs).
- Zero GPU hardware dependency or proprietary driver licensing.
- Predictable memory footprint (~1.8 GiB total container memory limit).

### Negative
- Lower maximum token generation speed compared to multi-gigabyte/sec GPU memory bandwidth (typically 15-30 tokens/sec on modern 4-core CPUs vs 80-120 tokens/sec on GPUs).
- Multi-user concurrency must be strictly serialized to avoid severe CPU thread contention.
