# ADR 0003: Multi-Stage Hardened Containerization

## Status
Accepted

## Context
Compiling C++ extensions like `llama-cpp-python` requires a full development toolchain (GCC, G++, CMake, Make, Linux kernel headers). Shipping build tools in production container images inflates image sizes to > 1.5 GB, introduces severe CVE attack surfaces (package managers, compilers, debuggers), and violates CIS container benchmarks.

## Decision
We implement a multi-stage Dockerfile architecture separating the compilation pipeline from the runtime artifact:
1. **Builder Stage (`python:3.11-slim-bookworm AS builder`)**:
   - Installs build tools and compiles Python wheels with AVX2 instruction optimizations into a dedicated wheelhouse (`/wheels`).
2. **Runtime Stage (`python:3.11-slim-bookworm AS runtime`)**:
   - Installs only minimal runtime dependencies (`libgomp1` OpenMP runtime and `curl` for healthchecks).
   - Installs pre-compiled wheels without preserving pip cache.
   - Runs as non-root user `appuser` (UID 10001 / GID 10001).
   - Drops all Linux capabilities (`CAP_DROP ALL`) and supports `readOnlyRootFilesystem: true`.

## Consequences
### Positive
- Production image size reduced by > 60%.
- Zero compiler toolchains or dev headers present in the shipping container.
- High security posture passing Trivy vulnerability scans with 0 HIGH/CRITICAL vulnerabilities.
- Non-root execution compliant with Kubernetes restricted pod security standards.

### Negative
- Builds require BuildKit or multi-stage Docker engine support (standard across modern CI and developer machines).
