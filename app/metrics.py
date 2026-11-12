"""Prometheus metrics definitions and instrumentation helpers."""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Request Metrics
REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total count of HTTP requests processed by endpoint and status.",
    ["endpoint", "status"],
)

REQUEST_DURATION_SECONDS = Histogram(
    "llm_request_duration_seconds",
    "Latency distribution of HTTP requests in seconds.",
    ["endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# Token & Generation Metrics
TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total count of tokens processed by the LLM service.",
    ["type"],  # 'prompt' or 'completion'
)

TOKENS_PER_SECOND = Gauge(
    "llm_tokens_per_second",
    "Latest measured generation throughput in tokens per second.",
)

# Concurrency & Backpressure Metrics
IN_FLIGHT_REQUESTS = Gauge(
    "llm_in_flight_requests",
    "Current number of requests actively executing inference.",
)

QUEUE_DEPTH = Gauge(
    "llm_queue_depth",
    "Current number of requests waiting for inference execution.",
)

REJECTED_REQUESTS_TOTAL = Counter(
    "llm_rejected_requests_total",
    "Count of requests rejected due to backpressure or saturation.",
    ["reason"],
)

# Model Lifecycle Metrics
MODEL_LOADED = Gauge(
    "llm_model_loaded",
    "Binary indicator (1=loaded, 0=not loaded) of LLM model status in memory.",
)

MODEL_LOAD_DURATION_SECONDS = Gauge(
    "llm_model_load_duration_seconds",
    "Time taken to load the model into memory in seconds.",
)


def get_metrics_snapshot() -> bytes:
    """Export all registered Prometheus metrics in text representation."""
    return generate_latest()


def get_metrics_content_type() -> str:
    """Return standard Prometheus exposition content type."""
    return CONTENT_TYPE_LATEST
