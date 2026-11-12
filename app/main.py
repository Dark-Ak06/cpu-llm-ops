"""FastAPI application providing production LLM endpoints, observability, and backpressure."""

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.llm import EngineSaturatedException, ModelEngine
from app.logging import setup_logging
from app.metrics import (
    REQUEST_DURATION_SECONDS,
    REQUESTS_TOTAL,
    get_metrics_content_type,
    get_metrics_snapshot,
)

logger = logging.getLogger("cpu_llm_ops.main")


# Request and Response Models
class GenerateRequest(BaseModel):
    """Payload schema for text generation."""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Input text prompt for inference.",
        examples=["Explain Kubernetes horizontal pod autoscaling in simple terms."],
    )
    max_tokens: int = Field(
        default=128,
        ge=1,
        le=2048,
        description="Maximum number of tokens to generate.",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for token randomness.",
    )


class GenerateResponse(BaseModel):
    """Output schema for synchronous text generation."""

    text: str
    tokens_generated: int
    latency_ms: float
    request_id: str


class HealthResponse(BaseModel):
    """Liveness probe status schema."""

    status: str
    version: str


class ReadyResponse(BaseModel):
    """Readiness probe status schema."""

    ready: bool
    model_name: str
    model_loaded: bool


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory for cpu-llm-ops service."""
    app_settings = settings or get_settings()
    setup_logging(app_settings.log_level)

    engine = ModelEngine(app_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info(
            "Starting up LLM inference service",
            extra={
                "extra_fields": {
                    "version": app_settings.app_version,
                    "env": app_settings.environment,
                }
            },
        )
        try:
            engine.load_model()
        except Exception as err:
            logger.error("Startup model load error: %s", str(err))
        yield
        logger.info("Shutting down LLM inference service")
        engine.unload_model()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description="Production CPU-Only LLM Inference Microservice",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.engine = engine

    # Request ID and Metrics Middleware
    @app.middleware("http")
    async def metrics_and_logging_middleware(request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        endpoint = request.url.path
        start_time = time.perf_counter()

        response: Response
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            logger.error(
                "Unhandled exception in request processing: %s",
                str(exc),
                exc_info=True,
                extra={"request_id": request_id},
            )
            raise
        finally:
            duration = time.perf_counter() - start_time
            REQUEST_DURATION_SECONDS.labels(endpoint=endpoint).observe(duration)
            REQUESTS_TOTAL.labels(endpoint=endpoint, status=str(status_code)).inc()

        response.headers["X-Request-ID"] = request_id
        return response

    # Exception Handlers
    @app.exception_handler(EngineSaturatedException)
    async def engine_saturated_handler(
        request: Request, exc: EngineSaturatedException
    ) -> JSONResponse:
        logger.warning(
            "Request rejected due to backpressure / saturation",
            extra={"request_id": getattr(request.state, "request_id", "unknown")},
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Inference engine saturated. Backpressure active.",
                "error_code": "SATURATION_LIMIT_EXCEEDED",
            },
            headers={"Retry-After": str(exc.retry_after)},
        )

    # API Endpoints
    @app.get("/health", response_model=HealthResponse, tags=["Observability"])
    async def health_check() -> HealthResponse:
        """Liveness probe: verifies process is alive and responsive."""
        return HealthResponse(
            status="healthy",
            version=app.state.settings.app_version,
        )

    @app.get("/ready", response_model=ReadyResponse, tags=["Observability"])
    async def ready_check() -> ReadyResponse:
        """Readiness probe: verifies model weights are loaded in memory."""
        is_ready = app.state.engine.is_loaded
        if not is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model not ready or currently loading.",
            )
        return ReadyResponse(
            ready=True,
            model_name=app.state.settings.model_name,
            model_loaded=True,
        )

    @app.get("/metrics", tags=["Observability"])
    async def metrics_endpoint() -> RawResponse:
        """Prometheus metrics scrape target."""
        return RawResponse(
            content=get_metrics_snapshot(),
            media_type=get_metrics_content_type(),
        )

    @app.post(
        "/generate",
        response_model=GenerateResponse,
        tags=["Inference"],
        responses={
            429: {"description": "Inference engine saturated with active queue"},
            504: {"description": "Request timed out during inference"},
        },
    )
    async def generate_endpoint(request: Request, payload: GenerateRequest) -> GenerateResponse:
        """Generate text synchronously using CPU LLM engine."""
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        try:
            text, tokens, latency_ms = await asyncio.wait_for(
                app.state.engine.generate(
                    prompt=payload.prompt,
                    max_tokens=payload.max_tokens,
                    temperature=payload.temperature,
                ),
                timeout=app.state.settings.request_timeout_seconds,
            )
            return GenerateResponse(
                text=text,
                tokens_generated=tokens,
                latency_ms=round(latency_ms, 2),
                request_id=request_id,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Inference request timed out",
                extra={"request_id": request_id},
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Inference execution timed out",
            ) from None

    @app.post("/generate/stream", tags=["Inference"])
    async def generate_stream_endpoint(
        request: Request, payload: GenerateRequest
    ) -> StreamingResponse:
        """Stream generated text chunks using Server-Sent Events (SSE)."""
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        async def sse_event_stream() -> AsyncGenerator[str, None]:
            try:
                async for chunk in app.state.engine.generate_stream(
                    prompt=payload.prompt,
                    max_tokens=payload.max_tokens,
                    temperature=payload.temperature,
                ):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as stream_err:
                logger.error(
                    "Error during stream generation: %s",
                    str(stream_err),
                    extra={"request_id": request_id},
                )
                yield f"data: [ERROR: {stream_err}]\n\n"

        return StreamingResponse(
            sse_event_stream(),
            media_type="text/event-stream",
            headers={"X-Request-ID": request_id},
        )

    return app


app = create_app()
