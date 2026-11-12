"""Application configuration management via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Production configuration schema with environment overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server Settings
    app_name: str = "cpu-llm-ops"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000
    environment: Literal["development", "staging", "production"] = "production"
    log_level: str = "INFO"

    # LLM Settings
    model_name: str = "Qwen2.5-1.5B-Instruct"
    model_file: str = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    model_path: str = "/models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    model_sha256: str = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
    model_url: str = (
        "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/"
        "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    )

    # Runtime Engine Parameters (CPU Tuning)
    n_threads: int = Field(default=4, ge=1, le=64)
    n_ctx: int = Field(default=2048, ge=256, le=32768)
    n_batch: int = Field(default=512, ge=32, le=2048)

    # Backpressure & Concurrency Control
    max_concurrent_requests: int = Field(default=2, ge=1, le=32)
    max_queue_depth: int = Field(default=4, ge=0, le=64)
    request_timeout_seconds: float = Field(default=60.0, gt=0.0)
    max_tokens_limit: int = Field(default=512, ge=1, le=4096)

    # Mock mode for testing and fast local CI environments
    mock_inference: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
