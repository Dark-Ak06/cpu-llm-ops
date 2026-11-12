# syntax=docker/dockerfile:1.4

# Stage 1: Build & compilation environment
FROM python:3.15-slim-bookworm AS builder

ARG DEBIAN_MIRROR=deb.debian.org

WORKDIR /build

# Configure mirror and install minimal toolchain for C++ compilation
# hadolint ignore=DL3008
RUN sed -i "s|deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optimize llama.cpp for portable modern x86_64 CPU instructions without AVX512 hard requirements
ENV CMAKE_ARGS="-DLLAMA_NATIVE=OFF -DLLAMA_AVX2=ON -DLLAMA_F16C=ON -DLLAMA_FMA=ON"
ENV PIP_NO_CACHE_DIR=1

COPY app/requirements.txt .

# Build wheels for all dependencies into /wheels
RUN pip wheel --wheel-dir=/wheels -r requirements.txt


# Stage 2: Hardened runtime environment
FROM python:3.15-slim-bookworm AS runtime

ARG DEBIAN_MIRROR=deb.debian.org

LABEL org.opencontainers.image.title="cpu-llm-ops" \
      org.opencontainers.image.description="Production CPU-Only LLM Inference Service" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.vendor="Darkhan Akanov" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/Dark-Ak06/cpu-llm-ops"

WORKDIR /app

# Install only runtime OpenMP shared library and curl for healthcheck
# hadolint ignore=DL3008
RUN sed -i "s|deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged application user and non-root directories
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -M appuser && \
    mkdir -p /models /app && \
    chown -R appuser:appgroup /models /app

# Install wheels from builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && \
    rm -rf /wheels

# Copy application source code
COPY --chown=appuser:appgroup app/ /app/app/

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/health"]

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
