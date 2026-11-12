# cpu-llm-ops Architecture Reference

## High-Level Architecture Overview

```mermaid
flowchart TD
    subgraph Clients["Consumers & Load Generators"]
        client["User Applications / Agents"]
        k6["k6 Distributed Load Testing Engine"]
    end

    subgraph Cluster["Kubernetes / Docker Compose Environment"]
        Ingress["Ingress / Reverse Proxy"]
        
        subgraph Pod["cpu-llm-ops Workload"]
            Init["Init Container (Checksum Verification & Model Download)"]
            ASGI["FastAPI / Uvicorn (HTTP + SSE Endpoints)"]
            Backpressure["Concurrency Limiter & Queue Manager"]
            CppEngine["llama-cpp-python C++ Core (AVX2/FMA Optimized)"]
            PromExporter["Prometheus Metrics Registry"]
        end

        PVC[("Persistent Storage / Cache Volume\n(Qwen2.5-1.5B-Instruct-Q4_K_M)")]
    end

    subgraph Observability["Observability Pipeline"]
        Prometheus["Prometheus Time-Series DB (:9090)"]
        Alertmanager["Prometheus Alertmanager (:9093)"]
        Grafana["Grafana Visual Dashboards (:3000)"]
    end

    client -->|POST /generate, /generate/stream| Ingress
    k6 -->|Stress Ingestion| Ingress
    Ingress --> ASGI
    Init -->|Verify / Download| PVC
    ASGI --> Backpressure
    Backpressure -->|Controlled Batch| CppEngine
    CppEngine -->|Memory Map| PVC
    ASGI --> PromExporter
    Prometheus -->|Scrape /metrics every 5s| PromExporter
    Prometheus -->|Evaluate Alert Rules| Alertmanager
    Grafana -->|Query Real-Time Metrics| Prometheus
```

---

## Inference Request Lifecycle & Backpressure Control

```mermaid
sequenceDiagram
    autonumber
    participant C as HTTP Client
    participant F as FastAPI Middleware
    participant Q as Concurrency Limiter
    participant E as llama.cpp CPU Runtime
    participant M as Prometheus Registry

    C->>F: POST /generate (prompt, max_tokens, temperature)
    F->>F: Assign X-Request-ID & record start timestamp
    F->>Q: Request Inference Execution
    alt Queue Depth > MAX_QUEUE_DEPTH
        Q-->>F: Raise EngineSaturatedException
        F-->>C: HTTP 429 Too Many Requests (Retry-After: 5)
        F->>M: Increment llm_rejected_requests_total{reason="queue_full"}
    else Queue Space Available
        Q->>Q: Enqueue (Increment llm_queue_depth)
        Q->>Q: Acquire Semaphore Slot (max_concurrent_requests)
        Q->>E: Execute C++ Inference in Thread Pool
        E->>E: Compute Token Generation via AVX2
        E-->>Q: Return Generated Tokens & Token Usage
        Q->>Q: Release Semaphore Slot
        Q->>M: Record Tokens, Latency, and Throughput
        F-->>C: HTTP 200 OK (text, tokens_generated, latency_ms, request_id)
    end
```

---

## State Diagram: Pod Lifecycle & Health Probes

```mermaid
stateDiagram-v2
    [*] --> InitContainer: Pod Scheduled
    InitContainer --> CheckingWeights: Check /models/qwen2.5.gguf
    CheckingWeights --> DownloadWeights: File missing or checksum mismatch
    CheckingWeights --> ReadyVolume: Checksum valid
    DownloadWeights --> ReadyVolume: Download complete & verified
    ReadyVolume --> AppContainerStartup: Container started

    state AppContainerStartup {
        [*] --> ProcessStarted: Uvicorn listening on :8000
        ProcessStarted --> LoadingModel: Read weights into RAM
        LoadingModel --> ModelReady: ModelEngine._is_loaded = true
    }

    ProcessStarted --> StartupProbe: GET /health returns 200
    ModelReady --> ReadinessProbe: GET /ready returns 200
    ReadinessProbe --> ServingTraffic: Ingress routing active
```

---

## Hardening & Security Boundaries

1. **Non-Root Execution**: Runs under UID `10001` (`appuser`) and GID `10001`.
2. **Read-Only Root Filesystem**: Implemented with explicit `readOnlyRootFilesystem: true`. Writable areas are isolated to ephemeral `emptyDir` mounts (`/tmp`).
3. **Capabilities**: Dropped all Linux capabilities (`CAP_DROP ALL`).
4. **Network Boundaries**: Ingress restricted to HTTP service port; egress restricted to CoreDNS (:53) and external HTTPS (:443) for initial model downloads.
