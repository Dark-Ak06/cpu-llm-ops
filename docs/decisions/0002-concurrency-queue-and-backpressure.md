# ADR 0002: In-Flight Concurrency Limiting and Backpressure Control

## Status
Accepted

## Context
CPU-based LLM inference is fundamentally compute-bound and memory-bandwidth bound. Unlike GPU kernels that parallelize across thousands of CUDA cores, running multiple concurrent prompts against a single llama.cpp model instance on CPU causes severe thread thrashing, cache eviction, and exponential latency degradation. Without protection, a small burst of incoming HTTP requests would lead to worker exhaustion, memory starvation, and 504 Gateway Timeouts.

## Decision
We enforce strict application-level backpressure using an asynchronous semaphore paired with a bounded waiting queue:
1. **In-Flight Concurrency Semaphore**: Defaults to `MAX_CONCURRENT_REQUESTS=2` (tuned for a 4-vCPU allocation).
2. **Bounded Queue Depth**: Defaults to `MAX_QUEUE_DEPTH=4`.
3. **Early Rejection (Fast Failure)**: When the queue capacity is exceeded, incoming requests are rejected immediately with HTTP `429 Too Many Requests` (or 503) and a standard `Retry-After: 5` header, without consuming CPU inference time.
4. **Metrics Instrumentation**: Active in-flight requests, current queue depth, and rejection rates are exposed as real-time Prometheus gauges.

## Consequences
### Positive
- Latency for in-flight requests remains strictly deterministic (~1-3 seconds for 32 tokens).
- Fast feedback to clients and upstream load balancers; enables retry logic or fallback routing.
- Eliminates memory exhaustion and catastrophic cascading failures under load.

### Negative
- Bursty traffic spikes encounter 429 rejections if horizontal autoscaling has not yet provisioned additional replicas.
