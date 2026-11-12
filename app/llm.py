"""LLM inference runtime engine with concurrency control and backpressure."""

import asyncio
import logging
import os
import time
from collections.abc import AsyncGenerator
from typing import Any

from app.config import Settings
from app.metrics import (
    IN_FLIGHT_REQUESTS,
    MODEL_LOAD_DURATION_SECONDS,
    MODEL_LOADED,
    QUEUE_DEPTH,
    REJECTED_REQUESTS_TOTAL,
    TOKENS_PER_SECOND,
    TOKENS_TOTAL,
)

logger = logging.getLogger("cpu_llm_ops.llm")


class EngineSaturatedException(Exception):
    """Raised when engine queue depth exceeds backpressure limits."""

    def __init__(self, message: str = "Inference engine saturated", retry_after: int = 5):
        super().__init__(message)
        self.retry_after = retry_after


class ModelEngine:
    """Manages LLM lifecycle, concurrency serialization, and inference execution."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: Any = None
        self._is_loaded: bool = False
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        self._active_in_flight: int = 0
        self._waiting_in_queue: int = 0

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded and ready to serve."""
        return self._is_loaded

    def load_model(self) -> None:
        """Load GGUF model into memory or initialize mock engine."""
        start_time = time.perf_counter()
        logger.info(
            "Initializing model engine",
            extra={"extra_fields": {"model_path": self.settings.model_path}},
        )

        if self.settings.mock_inference or not os.path.exists(self.settings.model_path):
            logger.warning(
                "Running in MOCK mode (model file not present or mock enabled)",
                extra={"extra_fields": {"mock": True, "path": self.settings.model_path}},
            )
            self._model = "mock-qwen-engine"
            self._is_loaded = True
        else:
            try:
                from llama_cpp import Llama

                self._model = Llama(
                    model_path=self.settings.model_path,
                    n_threads=self.settings.n_threads,
                    n_ctx=self.settings.n_ctx,
                    n_batch=self.settings.n_batch,
                    verbose=False,
                )
                self._is_loaded = True
            except Exception as e:
                logger.error("Failed to load GGUF model: %s", str(e), exc_info=True)
                MODEL_LOADED.set(0)
                self._is_loaded = False
                raise

        duration = time.perf_counter() - start_time
        MODEL_LOADED.set(1 if self._is_loaded else 0)
        MODEL_LOAD_DURATION_SECONDS.set(duration)
        logger.info(
            "Model load complete",
            extra={"extra_fields": {"duration_seconds": round(duration, 3)}},
        )

    def unload_model(self) -> None:
        """Cleanly release model memory during shutdown."""
        logger.info("Unloading model engine")
        self._model = None
        self._is_loaded = False
        MODEL_LOADED.set(0)

    async def _mock_generate(self, prompt: str, max_tokens: int) -> tuple[str, int]:
        """Simulate CPU inference for tests and fallback runs."""
        await asyncio.sleep(0.05)  # Simulate CPU compute time
        text = f"Mock response for prompt: {prompt[:30]}..."
        tokens = min(len(text.split()), max_tokens)
        return text, tokens

    async def generate(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> tuple[str, int, float]:
        """Execute synchronous text generation with backpressure control."""
        if not self._is_loaded:
            raise RuntimeError("Model is not loaded")

        # Backpressure check on queue depth
        if self._waiting_in_queue >= self.settings.max_queue_depth:
            REJECTED_REQUESTS_TOTAL.labels(reason="queue_full").inc()
            raise EngineSaturatedException()

        self._waiting_in_queue += 1
        QUEUE_DEPTH.set(self._waiting_in_queue)

        try:
            async with self._semaphore:
                self._waiting_in_queue -= 1
                QUEUE_DEPTH.set(self._waiting_in_queue)

                self._active_in_flight += 1
                IN_FLIGHT_REQUESTS.set(self._active_in_flight)

                start_time = time.perf_counter()
                try:
                    if self._model == "mock-qwen-engine":
                        text, tokens_gen = await self._mock_generate(prompt, max_tokens)
                    else:
                        loop = asyncio.get_running_loop()
                        output = await loop.run_in_executor(
                            None,
                            lambda: self._model(
                                prompt=prompt,
                                max_tokens=max_tokens,
                                temperature=temperature,
                                echo=False,
                            ),
                        )
                        text = output["choices"][0]["text"]
                        tokens_gen = output.get("usage", {}).get(
                            "completion_tokens", len(text.split())
                        )

                    latency_ms = (time.perf_counter() - start_time) * 1000.0

                    # Update throughput metrics
                    duration_sec = latency_ms / 1000.0
                    if duration_sec > 0:
                        tps = tokens_gen / duration_sec
                        TOKENS_PER_SECOND.set(tps)

                    TOKENS_TOTAL.labels(type="completion").inc(tokens_gen)
                    TOKENS_TOTAL.labels(type="prompt").inc(len(prompt.split()))

                    return text, tokens_gen, latency_ms

                finally:
                    self._active_in_flight -= 1
                    IN_FLIGHT_REQUESTS.set(self._active_in_flight)
        except EngineSaturatedException:
            raise
        except Exception:
            if self._waiting_in_queue > 0:
                self._waiting_in_queue -= 1
                QUEUE_DEPTH.set(self._waiting_in_queue)
            raise

    async def generate_stream(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> AsyncGenerator[str, None]:
        """Stream generated tokens over Server-Sent Events (SSE)."""
        if not self._is_loaded:
            raise RuntimeError("Model is not loaded")

        if self._waiting_in_queue >= self.settings.max_queue_depth:
            REJECTED_REQUESTS_TOTAL.labels(reason="queue_full").inc()
            raise EngineSaturatedException()

        self._waiting_in_queue += 1
        QUEUE_DEPTH.set(self._waiting_in_queue)

        async with self._semaphore:
            self._waiting_in_queue -= 1
            QUEUE_DEPTH.set(self._waiting_in_queue)

            self._active_in_flight += 1
            IN_FLIGHT_REQUESTS.set(self._active_in_flight)

            try:
                if self._model == "mock-qwen-engine":
                    words = f"Streamed mock completion for prompt: {prompt[:20]}".split()
                    for word in words:
                        await asyncio.sleep(0.02)
                        TOKENS_TOTAL.labels(type="completion").inc(1)
                        yield word + " "
                else:
                    loop = asyncio.get_running_loop()

                    def _stream_sync() -> list[str]:
                        chunks = []
                        for part in self._model(
                            prompt=prompt,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            stream=True,
                            echo=False,
                        ):
                            chunks.append(part["choices"][0]["text"])
                        return chunks

                    all_chunks = await loop.run_in_executor(None, _stream_sync)
                    for chunk in all_chunks:
                        yield chunk
            finally:
                self._active_in_flight -= 1
                IN_FLIGHT_REQUESTS.set(self._active_in_flight)
